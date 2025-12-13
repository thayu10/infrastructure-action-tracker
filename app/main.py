import os
import re
import json
import uuid
import time
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory
import psycopg2
import psycopg2.extras
import boto3

APP_PORT = int(os.getenv("APP_PORT", "8000"))

DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

EVIDENCE_BUCKET = os.getenv("EVIDENCE_BUCKET", "")
OWNERS = [x.strip() for x in os.getenv("OWNERS", "thayu10").split(",") if x.strip()]
COMPONENTS = [x.strip() for x in os.getenv("COMPONENTS", "CI-Pipeline,ECS-Service,RDS-Postgres,ALB,VPC").split(",") if x.strip()]

ALLOWED_PRIORITIES = {"P1", "P2", "P3"}
ALLOWED_STATUSES = ["Open", "In Progress", "Blocked", "Resolved", "Closed"]  # linear-ish
CLOSE_ROLES = {"lead", "admin"}

# AWS region is auto-detected by boto3 from env/metadata in ECS.
s3 = boto3.client("s3")

app = Flask(__name__, static_folder=".", static_url_path="")

_conn = None


def utc_now():
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_identity(required_for_write: bool = False):
    user = request.headers.get("X-User", "").strip()
    role = request.headers.get("X-Role", "member").strip().lower()

    if required_for_write and not user:
        return None, None, (jsonify({"error": "Missing X-User header"}), 401)

    # For read-only calls, allow missing user (use "anonymous" for attribution-less reads)
    if not user:
        user = "anonymous"

    if role not in {"member", "lead", "admin"}:
        role = "member"

    return user, role, None


def db():
    global _conn
    if _conn is None or _conn.closed != 0:
        _conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        _conn.autocommit = True
    return _conn


def init_db():
    con = db()
    with con.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS actions (
              id UUID PRIMARY KEY,
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              owner TEXT NOT NULL,
              component TEXT NOT NULL,
              priority TEXT NOT NULL,
              status TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL,
              updated_at TIMESTAMPTZ NOT NULL,
              resolution_notes TEXT,
              resolved_at TIMESTAMPTZ,
              closed_at TIMESTAMPTZ
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence (
              id UUID PRIMARY KEY,
              action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
              filename TEXT NOT NULL,
              s3_key TEXT NOT NULL,
              content_type TEXT NOT NULL,
              size_bytes BIGINT,
              uploaded_by TEXT NOT NULL,
              uploaded_at TIMESTAMPTZ NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
              id UUID PRIMARY KEY,
              action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
              event_type TEXT NOT NULL,
              from_status TEXT,
              to_status TEXT,
              actor TEXT NOT NULL,
              notes TEXT,
              created_at TIMESTAMPTZ NOT NULL
            );
            """
        )


def add_audit(action_id: uuid.UUID, event_type: str, actor: str, notes: str = None, from_status: str = None, to_status: str = None):
    con = db()
    with con.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_events (id, action_id, event_type, from_status, to_status, actor, notes, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (uuid.uuid4(), action_id, event_type, from_status, to_status, actor, notes, utc_now()),
        )


def normalize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w.\- ]+", "_", name)
    name = re.sub(r"\s+", "_", name)
    return name[:160] if name else "file"


def require_env():
    missing = []
    for k in ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD", "EVIDENCE_BUCKET"]:
        if not os.getenv(k):
            missing.append(k)
    if missing:
        return False, missing
    return True, []


@app.get("/health")
def health():
    ok, missing = require_env()
    if not ok:
        return jsonify({"status": "degraded", "missing_env": missing}), 200
    # Quick DB check
    try:
        con = db()
        with con.cursor() as cur:
            cur.execute("SELECT 1 as ok;")
            row = cur.fetchone()
        return jsonify({"status": "ok", "db": row["ok"]}), 200
    except Exception as e:
        return jsonify({"status": "degraded", "db_error": str(e)}), 200


@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@app.get("/api/config")
def api_config():
    # Read-only; no identity needed
    return jsonify(
        {
            "owners": OWNERS,
            "components": COMPONENTS,
            "priorities": sorted(list(ALLOWED_PRIORITIES)),
            "statuses": ALLOWED_STATUSES,
        }
    )


@app.get("/api/actions")
def list_actions():
    user, role, err = get_identity(required_for_write=False)
    if err:
        return err

    status = request.args.get("status")
    owner = request.args.get("owner")
    priority = request.args.get("priority")
    component = request.args.get("component")
    q = request.args.get("q")

    filters = []
    params = {}

    if status:
        filters.append("status = %(status)s")
        params["status"] = status
    if owner:
        filters.append("owner = %(owner)s")
        params["owner"] = owner
    if priority:
        filters.append("priority = %(priority)s")
        params["priority"] = priority
    if component:
        filters.append("component = %(component)s")
        params["component"] = component
    if q:
        filters.append("(title ILIKE %(q)s OR description ILIKE %(q)s)")
        params["q"] = f"%{q}%"

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sql = f"""
        SELECT *
        FROM actions
        {where}
        ORDER BY
          CASE priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END,
          updated_at DESC;
    """

    con = db()
    with con.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    # ISO format timestamps for frontend
    def convert(r):
        r = dict(r)
        for k in ["created_at", "updated_at", "resolved_at", "closed_at"]:
            if r.get(k):
                r[k] = iso(r[k])
        return r

    return jsonify({"items": [convert(r) for r in rows]})


@app.post("/api/actions")
def create_action():
    actor, role, err = get_identity(required_for_write=True)
    if err:
        return err

    body = request.get_json(force=True, silent=True) or {}
    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    owner = (body.get("owner") or "").strip()
    component = (body.get("component") or "").strip()
    priority = (body.get("priority") or "").strip().upper()

    if not title or not description or not owner or not component or not priority:
        return jsonify({"error": "title, description, owner, component, priority are required"}), 400
    if owner not in OWNERS:
        return jsonify({"error": f"owner must be one of: {OWNERS}"}), 400
    if component not in COMPONENTS:
        return jsonify({"error": f"component must be one of: {COMPONENTS}"}), 400
    if priority not in ALLOWED_PRIORITIES:
        return jsonify({"error": "priority must be P1, P2, or P3"}), 400

    action_id = uuid.uuid4()
    now = utc_now()

    con = db()
    with con.cursor() as cur:
        cur.execute(
            """
            INSERT INTO actions (id, title, description, owner, component, priority, status, created_by, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (action_id, title, description, owner, component, priority, "Open", actor, now, now),
        )
    add_audit(action_id, "created", actor, notes="Action created", to_status="Open")

    return jsonify({"id": str(action_id)}), 201


@app.patch("/api/actions/<action_id>")
def update_action(action_id):
    actor, role, err = get_identity(required_for_write=True)
    if err:
        return err

    try:
        aid = uuid.UUID(action_id)
    except ValueError:
        return jsonify({"error": "invalid action id"}), 400

    body = request.get_json(force=True, silent=True) or {}
    fields = {}
    allowed = {"title", "description", "owner", "component", "priority"}
    for k in allowed:
        if k in body and body[k] is not None:
            fields[k] = (str(body[k]).strip() if k in {"title", "description", "owner", "component"} else str(body[k]).strip().upper())

    if not fields:
        return jsonify({"error": "no updatable fields provided"}), 400

    if "owner" in fields and fields["owner"] not in OWNERS:
        return jsonify({"error": f"owner must be one of: {OWNERS}"}), 400
    if "component" in fields and fields["component"] not in COMPONENTS:
        return jsonify({"error": f"component must be one of: {COMPONENTS}"}), 400
    if "priority" in fields and fields["priority"] not in ALLOWED_PRIORITIES:
        return jsonify({"error": "priority must be P1, P2, or P3"}), 400

    con = db()
    with con.cursor() as cur:
        cur.execute("SELECT * FROM actions WHERE id = %s", (aid,))
        existing = cur.fetchone()
        if not existing:
            return jsonify({"error": "not found"}), 404

        sets = []
        params = {"id": aid}
        for i, (k, v) in enumerate(fields.items()):
            sets.append(f"{k} = %({k})s")
            params[k] = v

        sets.append("updated_at = %(updated_at)s")
        params["updated_at"] = utc_now()

        cur.execute(f"UPDATE actions SET {', '.join(sets)} WHERE id = %(id)s", params)

    add_audit(aid, "updated", actor, notes=f"Fields updated: {', '.join(fields.keys())}")
    return jsonify({"status": "ok"}), 200


@app.post("/api/actions/<action_id>/status")
def update_status(action_id):
    actor, role, err = get_identity(required_for_write=True)
    if err:
        return err

    try:
        aid = uuid.UUID(action_id)
    except ValueError:
        return jsonify({"error": "invalid action id"}), 400

    body = request.get_json(force=True, silent=True) or {}
    to_status = (body.get("to_status") or "").strip()
    resolution_notes = (body.get("resolution_notes") or "").strip()

    if to_status not in ALLOWED_STATUSES:
        return jsonify({"error": f"to_status must be one of: {ALLOWED_STATUSES}"}), 400

    con = db()
    with con.cursor() as cur:
        cur.execute("SELECT * FROM actions WHERE id = %s", (aid,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404

        from_status = row["status"]

        # Basic workflow checks
        if from_status == "Closed":
            return jsonify({"error": "Closed actions cannot be changed"}), 409

        if to_status == "Resolved" and not resolution_notes:
            return jsonify({"error": "resolution_notes is required when setting status to Resolved"}), 400

        if to_status == "Closed":
            if role not in CLOSE_ROLES:
                return jsonify({"error": "Only lead/admin can close actions"}), 403
            # Closing is only allowed from Resolved
            if from_status != "Resolved":
                return jsonify({"error": "Action must be Resolved before it can be Closed"}), 409

        now = utc_now()
        resolved_at = row["resolved_at"]
        closed_at = row["closed_at"]

        updates = {"status": to_status, "updated_at": now}
        if to_status == "Resolved":
            updates["resolution_notes"] = resolution_notes
            updates["resolved_at"] = now
        if to_status == "Closed":
            updates["closed_at"] = now

        set_parts = []
        params = {"id": aid}
        for k, v in updates.items():
            set_parts.append(f"{k} = %({k})s")
            params[k] = v

        cur.execute(f"UPDATE actions SET {', '.join(set_parts)} WHERE id = %(id)s", params)

    add_audit(aid, "status_changed", actor, notes=resolution_notes if to_status == "Resolved" else None, from_status=from_status, to_status=to_status)
    return jsonify({"status": "ok"}), 200


@app.get("/api/actions/<action_id>/evidence")
def list_evidence(action_id):
    actor, role, err = get_identity(required_for_write=False)
    if err:
        return err

    try:
        aid = uuid.UUID(action_id)
    except ValueError:
        return jsonify({"error": "invalid action id"}), 400

    con = db()
    with con.cursor() as cur:
        cur.execute("SELECT id, filename, s3_key, content_type, size_bytes, uploaded_by, uploaded_at FROM evidence WHERE action_id = %s ORDER BY uploaded_at DESC", (aid,))
        rows = cur.fetchall()

    items = []
    for r in rows:
        rr = dict(r)
        rr["id"] = str(rr["id"])
        rr["uploaded_at"] = iso(rr["uploaded_at"])
        items.append(rr)

    return jsonify({"items": items}), 200


@app.post("/api/actions/<action_id>/evidence/presign")
def presign_evidence(action_id):
    actor, role, err = get_identity(required_for_write=True)
    if err:
        return err

    try:
        aid = uuid.UUID(action_id)
    except ValueError:
        return jsonify({"error": "invalid action id"}), 400

    if not EVIDENCE_BUCKET:
        return jsonify({"error": "EVIDENCE_BUCKET not configured"}), 500

    body = request.get_json(force=True, silent=True) or {}
    filename = normalize_filename(body.get("filename") or "")
    content_type = (body.get("content_type") or "application/octet-stream").strip()

    # Key: actions/<action_id>/<uuid>_<filename>
    obj_id = uuid.uuid4()
    key = f"actions/{aid}/{obj_id}_{filename}"

    try:
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": EVIDENCE_BUCKET, "Key": key, "ContentType": content_type},
            ExpiresIn=900,
        )
    except Exception as e:
        return jsonify({"error": f"presign failed: {str(e)}"}), 500

    # Client should PUT directly to S3, then call /confirm to record metadata in DB
    return jsonify(
        {
            "upload_url": url,
            "s3_key": key,
            "expires_in_seconds": 900,
        }
    ), 200


@app.post("/api/actions/<action_id>/evidence/confirm")
def confirm_evidence(action_id):
    actor, role, err = get_identity(required_for_write=True)
    if err:
        return err

    try:
        aid = uuid.UUID(action_id)
    except ValueError:
        return jsonify({"error": "invalid action id"}), 400

    body = request.get_json(force=True, silent=True) or {}
    filename = normalize_filename(body.get("filename") or "")
    s3_key = (body.get("s3_key") or "").strip()
    content_type = (body.get("content_type") or "application/octet-stream").strip()
    size_bytes = body.get("size_bytes")

    if not filename or not s3_key:
        return jsonify({"error": "filename and s3_key are required"}), 400

    evid = uuid.uuid4()
    now = utc_now()

    con = db()
    with con.cursor() as cur:
        # Ensure action exists
        cur.execute("SELECT id FROM actions WHERE id = %s", (aid,))
        if not cur.fetchone():
            return jsonify({"error": "action not found"}), 404

        cur.execute(
            """
            INSERT INTO evidence (id, action_id, filename, s3_key, content_type, size_bytes, uploaded_by, uploaded_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (evid, aid, filename, s3_key, content_type, size_bytes, actor, now),
        )

        # Touch action updated_at
        cur.execute("UPDATE actions SET updated_at = %s WHERE id = %s", (now, aid))

    add_audit(aid, "evidence_attached", actor, notes=f"{filename} -> {s3_key}")
    return jsonify({"id": str(evid)}), 201


@app.get("/api/actions/<action_id>/audit")
def list_audit(action_id):
    actor, role, err = get_identity(required_for_write=False)
    if err:
        return err

    try:
        aid = uuid.UUID(action_id)
    except ValueError:
        return jsonify({"error": "invalid action id"}), 400

    con = db()
    with con.cursor() as cur:
        cur.execute(
            """
            SELECT id, event_type, from_status, to_status, actor, notes, created_at
            FROM audit_events
            WHERE action_id = %s
            ORDER BY created_at DESC
            """,
            (aid,),
        )
        rows = cur.fetchall()

    items = []
    for r in rows:
        rr = dict(r)
        rr["id"] = str(rr["id"])
        rr["created_at"] = iso(rr["created_at"])
        items.append(rr)

    return jsonify({"items": items}), 200


@app.before_first_request
def _startup():
    # Initialize DB schema lazily on first request
    # (works well in ECS where container can restart; idempotent DDL)
    init_db()


if __name__ == "__main__":
    # Local dev
    init_db()
    app.run(host="0.0.0.0", port=APP_PORT)
