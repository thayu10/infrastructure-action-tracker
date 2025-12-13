import os
import re
import json
import time
import uuid
import base64
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

import boto3
import psycopg2
import psycopg2.extras
from flask import (
    Flask,
    jsonify,
    request,
    render_template_string,
)

APP_PORT = int(os.getenv("APP_PORT", "8000"))

# Auth-lite identity headers
HDR_USER = "X-User"
HDR_ROLE = "X-Role"
ALLOWED_ROLES = {"member", "lead", "admin"}

# Core fields
STATUSES = ["Open", "In Progress", "Blocked", "Resolved", "Closed"]
PRIORITIES = ["P1", "P2", "P3"]

# S3 evidence config
EVIDENCE_BUCKET = os.getenv("EVIDENCE_BUCKET", "")
EVIDENCE_PREFIX = os.getenv("EVIDENCE_PREFIX", "evidence")

# DB config
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1"))

app = Flask(__name__)

# --- DB init handling (do NOT crash health checks) ---
_db_ready = False


def now_iso() -> str:
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()


def require_env() -> Tuple[bool, List[str]]:
    missing = []
    for k, v in [
        ("DB_HOST", DB_HOST),
        ("DB_NAME", DB_NAME),
        ("DB_USER", DB_USER),
        ("DB_PASSWORD", DB_PASSWORD),
        ("EVIDENCE_BUCKET", EVIDENCE_BUCKET),
    ]:
        if not v:
            missing.append(k)
    return (len(missing) == 0, missing)


def get_identity() -> Tuple[str, str]:
    user = request.headers.get(HDR_USER, "").strip()
    role = request.headers.get(HDR_ROLE, "member").strip().lower()

    if not user:
        return "", ""

    if role not in ALLOWED_ROLES:
        role = "member"

    return user, role


def require_identity() -> Tuple[Optional[Dict[str, str]], Optional[Tuple[Any, int]]]:
    user, role = get_identity()
    if not user:
        return None, (jsonify({"error": "missing identity header", "required": [HDR_USER]}), 400)
    return {"user": user, "role": role}, None


def db():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=5,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def init_db():
    schema_sql = """
    CREATE TABLE IF NOT EXISTS actions (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT NOT NULL,
      owner TEXT NOT NULL,
      component TEXT NOT NULL,
      priority TEXT NOT NULL,
      status TEXT NOT NULL,
      created_by TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL,
      resolution_notes TEXT
    );

    CREATE TABLE IF NOT EXISTS evidence (
      id TEXT PRIMARY KEY,
      action_id TEXT NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
      filename TEXT NOT NULL,
      s3_key TEXT NOT NULL,
      created_by TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL
    );
    """
    con = db()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute(schema_sql)
    finally:
        con.close()


def ensure_db_ready() -> Tuple[bool, Optional[str]]:
    """
    Initialize DB schema once. Never crash the app if DB is unavailable.
    """
    global _db_ready
    if _db_ready:
        return True, None

    try:
        init_db()
        _db_ready = True
        return True, None
    except Exception as e:
        return False, str(e)


def s3_client():
    return boto3.client("s3", region_name=AWS_REGION)


def sanitize_filename(name: str) -> str:
    name = name.strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name or "file"


def is_lead_or_admin(role: str) -> bool:
    return role in {"lead", "admin"}


def is_admin(role: str) -> bool:
    return role == "admin"


# ----------------------
# Pages
# ----------------------

@app.get("/")
def index():
    # Serve the single-page UI from /app/index.html via template string fallback.
    # If you prefer reading from file, keep it simple for now.
    try:
        # This assumes index.html is in the same folder and packaged into image.
        with open(os.path.join(os.path.dirname(__file__), "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
    except Exception:
        html = "<h1>Infrastructure Action Tracker</h1><p>index.html missing.</p>"
    return render_template_string(html)


# ----------------------
# Health
# ----------------------

@app.get("/health")
def health():
    ok, missing = require_env()
    if not ok:
        # Return 200 so ALB doesn't kill the target; show degraded state in payload.
        return jsonify({"status": "degraded", "missing_env": missing}), 200

    try:
        con = db()
        with con.cursor() as cur:
            cur.execute("SELECT 1 as ok;")
            row = cur.fetchone()
        con.close()
        return jsonify({"status": "ok", "db": row["ok"]}), 200
    except Exception as e:
        return jsonify({"status": "degraded", "db_error": str(e)}), 200


# ----------------------
# API - Actions
# ----------------------

@app.get("/api/actions")
def list_actions():
    ident, err = require_identity()
    if err:
        return err

    ready, derr = ensure_db_ready()
    if not ready:
        return jsonify({"error": "database not ready", "detail": derr}), 503

    status = request.args.get("status")
    owner = request.args.get("owner")
    priority = request.args.get("priority")
    component = request.args.get("component")

    q = "SELECT * FROM actions"
    clauses = []
    params = {}

    if status:
        clauses.append("status = %(status)s")
        params["status"] = status
    if owner:
        clauses.append("owner = %(owner)s")
        params["owner"] = owner
    if priority:
        clauses.append("priority = %(priority)s")
        params["priority"] = priority
    if component:
        clauses.append("component = %(component)s")
        params["component"] = component

    if clauses:
        q += " WHERE " + " AND ".join(clauses)

    # Default view: Status != Closed sorted by Priority then Updated
    if not status:
        q += " WHERE status <> 'Closed'"

    q += """
      ORDER BY
        CASE priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END,
        updated_at DESC
    """

    con = db()
    try:
        with con.cursor() as cur:
            cur.execute(q, params)
            rows = cur.fetchall()
        return jsonify({"items": rows, "viewer": ident})
    finally:
        con.close()


@app.post("/api/actions")
def create_action():
    ident, err = require_identity()
    if err:
        return err

    ready, derr = ensure_db_ready()
    if not ready:
        return jsonify({"error": "database not ready", "detail": derr}), 503

    body = request.get_json(force=True, silent=True) or {}

    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    owner = (body.get("owner") or "").strip()
    component = (body.get("component") or "").strip()
    priority = (body.get("priority") or "").strip()

    if not title or not description or not owner or not component or not priority:
        return jsonify({"error": "missing required fields"}), 400

    if priority not in PRIORITIES:
        return jsonify({"error": "invalid priority", "allowed": PRIORITIES}), 400

    action_id = str(uuid.uuid4())
    created_at = now_iso()

    con = db()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO actions (id, title, description, owner, component, priority, status,
                                         created_by, created_at, updated_at, resolution_notes)
                    VALUES (%(id)s, %(title)s, %(description)s, %(owner)s, %(component)s, %(priority)s, %(status)s,
                            %(created_by)s, %(created_at)s, %(updated_at)s, %(resolution_notes)s)
                    """,
                    {
                        "id": action_id,
                        "title": title,
                        "description": description,
                        "owner": owner,
                        "component": component,
                        "priority": priority,
                        "status": "Open",
                        "created_by": ident["user"],
                        "created_at": created_at,
                        "updated_at": created_at,
                        "resolution_notes": None,
                    },
                )
        return jsonify({"id": action_id})
    finally:
        con.close()


@app.patch("/api/actions/<action_id>")
def update_action(action_id: str):
    ident, err = require_identity()
    if err:
        return err

    ready, derr = ensure_db_ready()
    if not ready:
        return jsonify({"error": "database not ready", "detail": derr}), 503

    body = request.get_json(force=True, silent=True) or {}
    new_status = body.get("status")
    resolution_notes = body.get("resolution_notes")

    if new_status and new_status not in STATUSES:
        return jsonify({"error": "invalid status", "allowed": STATUSES}), 400

    # Only leads/admins can close
    if new_status == "Closed" and not is_lead_or_admin(ident["role"]):
        return jsonify({"error": "forbidden: only lead/admin can close"}), 403

    # Resolved requires notes
    if new_status == "Resolved" and not (resolution_notes or "").strip():
        return jsonify({"error": "resolution_notes required when resolving"}), 400

    updates = []
    params: Dict[str, Any] = {"id": action_id, "updated_at": now_iso()}

    if new_status:
        updates.append("status = %(status)s")
        params["status"] = new_status

    if resolution_notes is not None:
        updates.append("resolution_notes = %(resolution_notes)s")
        params["resolution_notes"] = (resolution_notes or "").strip() or None

    if not updates:
        return jsonify({"error": "no updates provided"}), 400

    updates.append("updated_at = %(updated_at)s")

    con = db()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute(
                    f"UPDATE actions SET {', '.join(updates)} WHERE id = %(id)s",
                    params,
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "not found"}), 404
        return jsonify({"ok": True})
    finally:
        con.close()


# ----------------------
# API - Evidence
# ----------------------

@app.get("/api/actions/<action_id>/evidence")
def list_evidence(action_id: str):
    ident, err = require_identity()
    if err:
        return err

    ready, derr = ensure_db_ready()
    if not ready:
        return jsonify({"error": "database not ready", "detail": derr}), 503

    con = db()
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT * FROM evidence WHERE action_id = %(aid)s ORDER BY created_at DESC",
                {"aid": action_id},
            )
            rows = cur.fetchall()
        return jsonify({"items": rows})
    finally:
        con.close()


@app.post("/api/actions/<action_id>/evidence")
def upload_evidence(action_id: str):
    ident, err = require_identity()
    if err:
        return err

    ready, derr = ensure_db_ready()
    if not ready:
        return jsonify({"error": "database not ready", "detail": derr}), 503

    if not EVIDENCE_BUCKET:
        return jsonify({"error": "EVIDENCE_BUCKET not configured"}), 500

    body = request.get_json(force=True, silent=True) or {}
    filename = sanitize_filename(body.get("filename") or "")
    content_b64 = body.get("content_base64") or ""

    if not filename or not content_b64:
        return jsonify({"error": "filename and content_base64 required"}), 400

    try:
        raw = base64.b64decode(content_b64, validate=True)
    except Exception:
        return jsonify({"error": "invalid base64"}), 400

    # Keep uploads reasonably small for demo
    if len(raw) > 5 * 1024 * 1024:
        return jsonify({"error": "file too large (max 5MB)"}), 400

    evidence_id = str(uuid.uuid4())
    created_at = now_iso()
    s3_key = f"{EVIDENCE_PREFIX}/{action_id}/{evidence_id}-{filename}"

    s3 = s3_client()
    s3.put_object(
        Bucket=EVIDENCE_BUCKET,
        Key=s3_key,
        Body=raw,
        ContentType="application/octet-stream",
        ServerSideEncryption="AES256",
    )

    con = db()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO evidence (id, action_id, filename, s3_key, created_by, created_at)
                    VALUES (%(id)s, %(action_id)s, %(filename)s, %(s3_key)s, %(created_by)s, %(created_at)s)
                    """,
                    {
                        "id": evidence_id,
                        "action_id": action_id,
                        "filename": filename,
                        "s3_key": s3_key,
                        "created_by": ident["user"],
                        "created_at": created_at,
                    },
                )
        return jsonify({"id": evidence_id, "s3_key": s3_key})
    finally:
        con.close()


# ----------------------
# Run
# ----------------------

if __name__ == "__main__":
    # Do NOT hard-init DB here; let the app come up even if DB is temporarily unavailable.
    app.run(host="0.0.0.0", port=APP_PORT)
