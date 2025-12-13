# Infrastructure Action Tracker (AWS + Terraform + GitHub Actions)

A small, production-minded internal web app for tracking infrastructure actions and operational follow-ups (think: “restart stuck ECS service”, “rotate a DB parameter group”, “investigate ALB 5xx spike”) with audit-friendly metadata and evidence attachments.

The project demonstrates end-to-end delivery of a containerized web application on AWS using Terraform and GitHub Actions, with an emphasis on secure CI/CD, immutable deployments, private networking, and auditable infrastructure operations.

---

## What the app does

### Core workflow
1. An engineer creates a new **Action** with mandatory context:
   - Title (imperative and specific)
   - Description (supports markdown-style text)
   - Owner (required)
   - System/Component (required)
   - Priority (P1/P2/P3)
   - External references (optional: links, ticket IDs)

2. Actions move through a clear lifecycle:
   - **Open → In Progress → Blocked → Resolved → Closed**
   - **Resolved** requires resolution notes (“what fixed it?”)
   - **Closed** is restricted to lead/admin (auth-lite)

3. Evidence can be attached:
   - UI requests a **presigned S3 upload URL**
   - File is uploaded directly to S3
   - App stores evidence metadata in the database

### “Auth-lite” (deliberately simple)
For demo purposes, the app reads identity from request headers:
- `X-User`: required (who is acting)
- `X-Role`: optional (`member` | `lead` | `admin`)

This approach supports attribution and basic authorization while keeping the project focused on infrastructure, CI/CD, and deployment concerns.

---

## Infrastructure breakdown (AWS)

### Networking (VPC)
- **VPC** with public and private subnets across 2 AZs
- **Internet Gateway** for public routing
- **NAT Gateway** for private subnet outbound access (ECS tasks pulling images, patching, etc.)
- Security groups scoped so:
  - ALB is public on HTTP/80
  - ECS runs in private subnets and accepts traffic only from the ALB
  - RDS is private and accepts traffic only from ECS

### Compute + Delivery
- **ECS Fargate** runs the application container
- **ALB** routes traffic to ECS target group (health check path: `/health`)
- **CloudWatch Logs** collects application logs from ECS

### Data
- **RDS (Postgres)** stores:
  - tasks/actions
  - status changes and audit events
  - evidence metadata
- **S3 (private)** stores evidence files
  - public access blocked
  - encryption enabled
  - lifecycle expiration policy (keeps bucket tidy)

### IAM and security model
- GitHub Actions uses **OIDC** to assume an AWS role (no static AWS keys stored in GitHub).
- ECS uses:
  - **Execution role** (run tasks, push logs)
  - **Task role** (S3 access for evidence)

---

## CI/CD: GitHub Actions → Docker Hub → Terraform → ECS

### Container build and push
- GitHub Actions builds the Docker image and pushes to Docker Hub.
- Images are tagged immutably using the commit SHA:

`thayu10/infrastructure-action-tracker:<GIT_SHA>`

This avoids “latest tag” confusion and guarantees ECS deploys the intended version.

### Deployment mechanism (how ECS always picks up the latest build)
- CI/CD passes the immutable image reference into Terraform:
  - `-var="docker_image=thayu10/infrastructure-action-tracker:<GIT_SHA>"`
- Terraform updates the ECS task definition image
- ECS service deploys the new task definition revision automatically

---

## Remote Terraform state (mandatory for CI/CD)

Terraform state is stored remotely for team-safe locking and CI/CD runs:

- S3 bucket: `infrastructure-action-tracker-tf-state`
- DynamoDB table: `terraform-locks`
- Example state key: `infra/dev/terraform.tfstate`

---

## Repository structure

