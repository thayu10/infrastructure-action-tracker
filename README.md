# 🛠️ Infrastructure Action Tracker
**Cloud-Native DevOps Incident Management System**

> **Tech Stack:** AWS ECS Fargate • Terraform IaC • Docker • PostgreSQL RDS • S3 • ALB • GitHub Actions CI/CD • Python Flask

Incident tracking application for cloud and DevOps teams to log operational issues, track lifecycle status, and store supporting evidence.

---

## 🚀 Cloud Architecture

### AWS Services & Infrastructure
- **Compute:** ECS Fargate with auto-scaling container orchestration
- **Networking:** Multi-AZ VPC with public/private subnets, NAT Gateway, Internet Gateway
- **Load Balancing:** Application Load Balancer with health checks and target groups
- **Database:** RDS PostgreSQL with automated backups and private subnet isolation
- **Storage:** S3 with server-side encryption (AES256) and lifecycle policies
- **Security:** IAM roles, security groups, least-privilege access policies
- **Monitoring:** CloudWatch Logs and metrics integration

### Infrastructure as Code (Terraform)
```
Modularized Terraform architecture:
├── VPC & Networking (subnets, routing, security groups)
├── ALB (load balancer, listeners, target groups)
├── ECS (Fargate cluster, task definitions, services)
├── RDS (PostgreSQL with private access)
├── IAM (execution roles, task roles, OIDC for GitHub)
├── S3 (encrypted evidence storage)
├── CloudWatch (logging and monitoring)
└── Bastion (optional admin access)
```

**State Management:** Remote backend with S3 + DynamoDB locking for team collaboration

---

## 🔄 CI/CD Pipeline (GitHub Actions → Docker Hub → AWS)

### Automated Deployment Flow
1. **Build:** GitHub Actions builds Docker image on push
2. **Push:** Immutable image tags (`sha-<commit>`) to Docker Hub
3. **Deploy:** Terraform updates ECS task definition with new image
4. **Rollout:** ECS service performs rolling deployment with zero downtime

### Infrastructure Lifecycle Management
- **Automated Provisioning:** Complete infrastructure deployment via CI/CD
- **Manual Teardown Workflows:** 
  - Full infrastructure destruction (all AWS resources)
  - Backend infrastructure cleanup (Terraform state bucket and DynamoDB table)
- **Cost Control:** On-demand environment teardown for dev/test environments

### Security Implementation
- **OIDC Authentication:** GitHub Actions assumes AWS roles (no static credentials)
- **Image Immutability:** SHA-based tagging prevents deployment confusion
- **Network Isolation:** ECS tasks in private subnets, RDS accessible only from ECS
- **Encryption:** S3 server-side encryption, RDS encryption at rest

---

## 💼 Application Features

### Purpose
Lightweight incident tracking for infrastructure incidents, cloud migrations, operational follow-ups, and audit evidence collection.

### Core Capabilities
- Full lifecycle management (Open → In Progress → Blocked → Resolved → Closed)
- Role-based access control (member/lead/admin via headers)
- S3-backed evidence file attachments
- Real-time filtering and search
- ALB-compatible health endpoints
- Audit trail with status transitions and resolution notes

### Technical Implementation
- **Backend:** Python Flask with psycopg2 (PostgreSQL) and boto3 (AWS SDK)
- **Frontend:** Vanilla JavaScript SPA with modal-based UI
- **Configuration:** Environment-variable driven, 12-factor app compliant
- **Containerization:** Docker with ECS/EC2 compatibility

---

## 📸 Application Interface

### Main Dashboard
![Action Tracker Dashboard](docs/images/dashboard.png)
*Searchable action item list with real-time filtering, priority-based sorting, and quick status updates*

### Action Management

**Creating New Actions**
![Create Action Modal](docs/images/create-action.png)
*Modal-based form for creating infrastructure actions with priority, owner, and component assignment*

**Evidence Upload Integration**
![Evidence Upload](docs/images/evidence-upload.png)
*S3-backed file attachment system for storing operational evidence and documentation*
```


## 🏗️ Architecture Overview
```
GitHub Actions (OIDC)
    ↓
Docker Hub (immutable tags)
    ↓
Terraform Apply
    ↓
┌─────────────────────────────────────────┐
│  VPC (Multi-AZ)                         │
│  ┌────────────────────────────────────┐ │
│  │ Public Subnets                     │ │
│  │   └─ ALB (HTTP/80)                 │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │ Private Subnets                    │ │
│  │   ├─ ECS Fargate (Flask app)       │ │
│  │   └─ RDS PostgreSQL                │ │
│  └────────────────────────────────────┘ │
│  NAT Gateway → Internet Gateway         │
└─────────────────────────────────────────┘
         ↓
    S3 (Evidence Storage)
    CloudWatch (Logs & Metrics)
```

---

## 📊 Technical Capabilities

✅ **Infrastructure as Code** - Modular Terraform with remote state management  
✅ **Container Orchestration** - ECS Fargate with task definitions and services  
✅ **CI/CD Automation** - End-to-end GitHub Actions pipeline  
✅ **Cloud Architecture** - Multi-tier AWS design with security best practices  
✅ **Database Management** - RDS PostgreSQL with backup and recovery  
✅ **Security Engineering** - IAM policies, OIDC, network segmentation  
✅ **Monitoring & Logging** - CloudWatch integration for observability  
✅ **Version Control** - Git-based workflow with immutable artifact tagging

---

## 🎯 Key Features

**Deployment:** Fully automated with Terraform  
**Scalability:** Horizontal scaling ready with multi-region support  
**Security:** Network isolation, encryption at rest and in transit, IAM best practices  
**Reliability:** Multi-AZ deployment, automated backups, health monitoring  
**Cost Management:** Manual workflow triggers for complete infrastructure teardown