# 🛠️ Infrastructure Action Tracker
## Engineering Runbook

A lightweight internal infrastructure action and incident tracking application designed for cloud and DevOps teams.

This system enables teams to:
- Log operational issues
- Track lifecycle status
- Capture resolution context
- Store supporting evidence securely in Amazon S3

The application is intentionally lightweight and is not intended to replace full ITSM platforms.

Built with Flask on the backend and a single-page HTML + JavaScript UI on the frontend.

---

## 1. System Overview

### Purpose
Infrastructure Action Tracker is designed for operational visibility and accountability during:
- Infrastructure incidents
- Cloud migration work
- Operational follow-ups
- Audit and compliance evidence collection
- DevOps task coordination

The tool focuses on **clarity, traceability, and low operational overhead**.

---

## 2. Feature Set

### Core Capabilities
- 📋 Create, edit, resolve, close, and delete infrastructure actions
- 🏷️ Track actions by priority, status, owner, and component
- 🔄 Full lifecycle management  
  Open → In Progress → Blocked → Resolved → Closed
- 🧠 Mandatory resolution notes when resolving actions
- 🧾 Attach operational evidence files stored securely in Amazon S3
- 🔍 Real-time filtering and full-text search across actions and resolutions
- ⚡ One-click quick status updates directly from the action list
- 🔐 Role-based behavior enforced via headers (member, lead, admin)
- 🗑️ Hard delete functionality (admin only)
- 📊 Priority-based sorting with latest updates surfaced first
- 🩺 Health endpoint compatible with ALB target groups

---

## 3. Technology Stack

### Frontend
- Vanilla HTML
- Custom CSS dark UI theme
- JavaScript (no framework)
- Single-page, modal-based UI

### Backend
- Python
- Flask
- psycopg2
- boto3 (AWS SDK)

### Data and Storage
- PostgreSQL  
  Stores:
  - Actions
  - Status transitions
  - Resolution notes
  - Evidence metadata
- Amazon S3  
  Stores:
  - Evidence files only
  - Server-side encryption enabled (AES256)

### Cloud and DevOps
- Container-ready (ECS / EC2 compatible)
- ALB-friendly health checks
- Environment-variable driven configuration

---

## 4. Application Lifecycle

### Supported Action Statuses
- Open
- In Progress
- Blocked
- Resolved
- Closed

### Backend-Enforced Rules
- Resolving an action requires resolution notes
- Closing an action requires role lead or admin
- Deleting an action requires role admin
- Closed actions are hidden by default unless explicitly filtered

---

## 5. Identity and Access Control

### Identity Model
Authentication is header-based and designed to sit behind:
- ALB
- API Gateway
- Internal reverse proxy
- Auth middleware (future)

### Required Headers
X-User: <username>
X-Role: member | lead | admin

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


## Module Overview

```
modules/
  vpc        → Networking, subnets, routing, and security boundaries
  alb        → Application Load Balancer and target groups
  ecs        → ECS Fargate cluster, task definitions, and services
  rds        → PostgreSQL database with private access
  iam        → IAM roles and policies for ECS and CI/CD
  s3         → Evidence storage bucket with restricted access
  cloudwatch → Log groups and basic monitoring
  bastion    → Optional administrative access host
```

## Directory Structure

```
infra/
├── main.tf
├── provider.tf
├── versions.tf
├── variables.tf
├── outputs.tf
├── dev.tfvars
├── prod.tfvars
│
├── modules/
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── alb/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── ecs/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── rds/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── iam/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── s3/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── cloudwatch/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   └── bastion/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
└── README.md
```


