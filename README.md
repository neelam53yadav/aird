# AirdOps: Enterprise AI-Ready Data Platform

**Transform raw data into production-ready AI applications with enterprise-grade quality, governance, and scalability.**

AirdOps is a comprehensive data platform designed to ingest, process, vectorize, and optimize data for AI/ML applications. Built with enterprise architecture principles, it provides end-to-end data processing workflows from ingestion to vectorization, with integrated quality management, team collaboration, and advanced analytics.

---

## Table of Contents

1. [Platform Overview](#platform-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Core Capabilities](#core-capabilities)
4. [Getting Started](#getting-started)
5. [Technical Documentation](#technical-documentation)
6. [Deployment Guide](#deployment-guide)
7. [API Reference](#api-reference)
8. [Enterprise Features](#enterprise-features)

---

## Platform Overview

### What is AirdOps?

AirdOps is an enterprise-grade data processing platform that transforms unstructured and structured data sources into AI-ready formats. The platform handles the complete data lifecycle—from ingestion and preprocessing to vectorization and quality assessment—enabling organizations to build production-ready RAG (Retrieval-Augmented Generation) applications and AI systems with confidence.

### Key Value Propositions

- **AI-Ready Data Pipeline**: Automated ingestion, preprocessing, chunking, embedding, and indexing workflows
- **Quality Assurance**: 15+ dimensional quality scoring with automated optimization recommendations
- **Enterprise Architecture**: Microservices design with scalable, containerized components
- **Production-Ready**: Built-in monitoring, error handling, and compliance features
- **Team Collaboration**: Role-based access control, workspace management, and audit trails

### Production Deployment

**Live Instance**: [https://airdops.com](https://airdops.com)

**Service Endpoints**:
- Frontend UI: `https://airdops.com`
- Backend API: `https://airdops.com/api` (via reverse proxy)
- API Documentation: `https://airdops.com/docs`
- Airflow Dashboard: `https://airdops.com/airflow`

---

## Architecture & Technology Stack

### System Architecture

AirdOps follows a **microservices architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Next.js Frontend (React/TypeScript)               │    │
│  │  - Server-side rendering                           │    │
│  │  - NextAuth.js authentication                      │    │
│  │  - Real-time UI updates                            │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS/REST API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                         │
│  ┌────────────────────────────────────────────────────┐    │
│  │  FastAPI Backend (Python 3.11+)                    │    │
│  │  - RESTful API endpoints                           │    │
│  │  - JWT authentication                              │    │
│  │  - Request validation & routing                    │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Orchestration│  │  Processing  │  │   Storage    │
│              │  │              │  │              │
│ Apache       │  │ AIRD Pipeline│  │ PostgreSQL   │
│ Airflow      │  │ Stages       │  │ (Metadata)   │
│              │  │              │  │              │
│ DAG-based    │  │ Embedding    │  │ Qdrant       │
│ Workflows    │  │ Generation   │  │ (Vectors)    │
│              │  │              │  │              │
│ Task         │  │ Quality      │  │ MinIO/GCS    │
│ Scheduling   │  │ Scoring      │  │ (Objects)    │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Technology Stack

#### Frontend
- **Framework**: Next.js 13+ (App Router)
- **Language**: TypeScript
- **UI Library**: React 18+ with custom components
- **Authentication**: NextAuth.js (Google OAuth, Email/Password)
- **Styling**: Tailwind CSS
- **Build**: Docker multi-stage builds with standalone output

#### Backend
- **Framework**: FastAPI 0.104+
- **Language**: Python 3.11+ (compatible with 3.12)
- **Database ORM**: SQLAlchemy 2.0.23
- **Migrations**: Alembic 1.12.1
- **Authentication**: JWT (HS256) with Python-Jose
- **Password Hashing**: Passlib with bcrypt 3.2+

#### Data Processing
- **Orchestration**: Apache Airflow 2.x
- **Vector Database**: Qdrant 1.16.2+
- **Object Storage**: MinIO / Google Cloud Storage
- **Embedding Models**:
  - OpenAI: `text-embedding-3-small` (1536 dim), `text-embedding-3-large` (3072 dim)
  - Open Source: MiniLM, MPNet, BGE, GTE, E5, Instructor (384-1024 dim)
- **ML Libraries**: Sentence Transformers 2.7+, OpenAI SDK 1.0+

#### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Cloud Platform**: Google Cloud Platform (GCP)
  - Compute Engine VM (container hosting)
  - Cloud SQL (PostgreSQL)
  - Cloud Storage (object storage)
- **Reverse Proxy**: Nginx
- **CI/CD**: GitHub Actions with Workload Identity Federation

#### Database
- **Primary**: PostgreSQL 13+ (metadata, users, products, configurations)
- **Vector**: Qdrant (embeddings, chunk metadata, search indices)
- **Object**: MinIO/GCS (raw files, processed data, artifacts)

---

## Core Capabilities

### 1. Data Ingestion & Connectors

AirdOps supports multiple data source types with extensible connector architecture:

#### Supported Data Sources

- **Web Scraping**: URL-based content extraction with configurable depth
- **File System**: Local and remote folder synchronization
- **Cloud Storage**:
  - AWS S3 (via boto3)
  - Azure Blob Storage (via azure-storage-blob)
  - Google Cloud Storage (via google-cloud-storage)
- **Google Drive**: Direct integration with Google Drive API
- **File Uploads**: Direct browser-based file upload (PDF, TXT, DOCX, etc.)

#### Connector Features

- **Incremental Sync**: Track changes and sync only new/updated files
- **Metadata Preservation**: Maintain file metadata, timestamps, and structure
- **Error Handling**: Robust retry logic and error reporting
- **Progress Tracking**: Real-time sync status and file counts

### 2. Data Processing Pipeline

The AIRD (AI-Ready Data) pipeline consists of modular stages orchestrated by Apache Airflow:

#### Pipeline Stages

1. **Ingestion Stage**
   - Connects to data sources
   - Downloads/uploads files to object storage
   - Creates metadata records in database
   - Tracks file status and versions

2. **Preprocessing Stage**
   - Text normalization and cleaning
   - OCR error correction (optional)
   - Metadata extraction
   - Content type detection
   - Playbook-based transformations

3. **Chunking Stage**
   - Intelligent document chunking
   - Multiple strategies: fixed-size, semantic, recursive
   - Configurable overlap and size limits
   - Section-aware chunking for structured documents

4. **Scoring Stage**
   - 15+ dimensional quality metrics
   - Trust score calculation
   - Security assessment (PII detection)
   - Metadata completeness evaluation
   - Knowledge base readiness scoring

5. **Embedding Generation**
   - Model-agnostic embedding pipeline
   - Adaptive batch sizing based on model dimensions
   - Supports OpenAI and open-source models
   - Dimension validation and error handling

6. **Vector Indexing**
   - Qdrant collection management
   - Metadata-rich payload storage
   - Access control list (ACL) integration
   - Efficient bulk indexing operations

7. **Quality Validation**
   - Enterprise data quality rules (7 rule types)
   - Violation detection and reporting
   - Compliance checking
   - Policy evaluation

8. **Artifact Generation**
   - Validation summaries (CSV)
   - Trust reports (PDF)
   - Fingerprint JSON files
   - Export-ready bundles

### 3. AI Readiness Assessment

#### Quality Metrics (15+ Dimensions)

**Core Metrics**:
- **AI Trust Score**: Aggregated quality indicator (0-100)
- **Quality Score**: Content quality and structure
- **Completeness**: Data coverage and gaps
- **Security Score**: PII detection and redaction effectiveness
- **Metadata Presence**: Completeness of metadata fields
- **Knowledge Base Readiness**: Suitability for RAG applications

**Advanced Metrics**:
- Chunk coverage analysis
- Duplicate rate tracking
- Content structure validation
- Language detection and validation
- Format compliance

#### Optimization Recommendations

The platform provides actionable recommendations to improve data quality:

- **Quality Normalization**: Enhanced text cleaning (+15-25% improvement)
- **Error Correction**: OCR and typo fixes (+5-10% improvement)
- **Metadata Extraction**: Automated metadata enrichment (+5-15% improvement)
- **Chunk Overlap Optimization**: Context preservation improvements (+3-7% improvement)
- **Playbook Selection**: Content-type-specific preprocessing strategies

**Impact**: Organizations achieving >85% quality scores see **4x efficiency gains** in AI applications compared to 70-85% quality data.

### 4. Vectorization & Embeddings

#### Supported Embedding Models

**OpenAI Models** (requires API key):
- `text-embedding-3-small`: 1536 dimensions
- `text-embedding-3-large`: 3072 dimensions

**Open-Source Models** (via Sentence Transformers):
- **MiniLM**: 384 dimensions (`minilm`, `minilm-l12`)
- **MPNet**: 768 dimensions (`mpnet-base-v2`)
- **BGE Models**: 384/768/1024 dimensions (`bge-small-en`, `bge-base-en`, `bge-large-en`)
- **E5 Models**: 384/768/1024 dimensions (`e5-small`, `e5-base`, `e5-large`)
- **GTE Models**: 384/768/1024 dimensions (`gte-small`, `gte-base`, `gte-large`)
- **Instructor Models**: 768 dimensions (`instructor-base`, `instructor-large`)
- **Multilingual Models**: Various dimensions for non-English content

#### Embedding Configuration

- **Adaptive Batching**: Automatically adjusts batch sizes based on model dimensions
  - 1024+ dim: Batch size 3
  - 768+ dim: Batch size 10
  - <768 dim: Batch size 32
- **Dimension Validation**: Ensures query and index embeddings use compatible dimensions
- **Model Versioning**: Tracks embedding model versions for compatibility

### 5. Enterprise Data Quality Management

#### Data Quality Rule Types

1. **Required Fields**: Ensures critical fields are present
2. **Max Duplicate Rate**: Prevents excessive duplication
3. **Min Chunk Coverage**: Ensures adequate content coverage
4. **Bad Extensions**: Blocks problematic file types
5. **Max File Size**: Controls file size limits
6. **Content Validation**: Validates content quality and structure
7. **Custom Rules**: User-defined validation logic

#### Quality Management Features

- **Real-time Evaluation**: Rules evaluated during pipeline execution
- **Violation Tracking**: Comprehensive violation reporting with severity levels
- **Audit Trail**: Complete history of rule changes with user attribution
- **Compliance Reporting**: Regulatory compliance status tracking
- **Database-First Architecture**: ACID-compliant rule management

### 6. Policy Evaluation System

Policy evaluation serves as a quality gate to ensure data meets production standards:

#### Policy Thresholds (Configurable)

| Metric | Default Threshold | Purpose |
|--------|------------------|---------|
| **AI Trust Score** | ≥ 50% | Overall quality indicator |
| **Security Score** | ≥ 90% | PII handling compliance |
| **Metadata Presence** | ≥ 80% | Metadata completeness |
| **Knowledge Base Ready** | ≥ 50% | RAG application suitability |

#### Policy Status

- **PASSED**: All metrics meet thresholds → Product status: `READY`
- **FAILED**: One or more metrics below thresholds → Product status: `FAILED_POLICY`
- **WARNINGS**: Passes but suboptimal → Product status: `READY_WITH_WARNINGS`

### 7. Team Collaboration & Access Control

#### Workspace Management

- **Multi-workspace Support**: Users can belong to multiple workspaces
- **Role-Based Access Control (RBAC)**:
  - **Owner**: Full access, billing management
  - **Admin**: Full access, team management (no billing)
  - **Editor**: Create and manage products
  - **Viewer**: Read-only access

#### Team Features

- **User Invitations**: Email-based team member invitations
- **Permission Management**: Granular access control per workspace
- **Activity Tracking**: Audit logs for team actions
- **Profile Management**: User profiles with preferences

### 8. Billing & Usage Management

#### Subscription Plans

| Plan | Price | Products | Data Sources/Product | Pipeline Runs/Month |
|------|-------|----------|---------------------|---------------------|
| **Free** | $0 | 3 | 5 | 10 |
| **Pro** | $99/month | 25 | 50 | 1,000 |
| **Enterprise** | $999/month | Unlimited | Unlimited | Unlimited |

#### Usage Tracking

- Products, data sources, and pipeline runs
- Vector storage and embedding usage
- Real-time usage monitoring
- Plan limit enforcement
- Stripe integration for payments

---

## Getting Started

### Prerequisites

- **Python**: 3.11+ (3.12 compatible)
- **Node.js**: 18+
- **Docker**: 20.10+ and Docker Compose 2.0+
- **Git**: 2.30+
- **Make**: 4.0+ (optional, for Makefile commands - recommended for easier setup)
  - **Windows**: Install via [Chocolatey](https://chocolatey.org/) (`choco install make`), [Scoop](https://scoop.sh/) (`scoop install make`), or use WSL/Git Bash
  - **macOS**: Install via Homebrew (`brew install make`) or Xcode Command Line Tools
  - **Linux**: Usually pre-installed, or install via package manager (`apt-get install make` / `yum install make`)
- **System Resources**:
  - RAM: Minimum 8GB, Recommended 16GB+
  - Storage: Minimum 10GB free space
  - CPU: 4+ cores recommended

### Quick Start (Local Development)

#### Option 1: Using Makefile (Recommended)

The easiest way to set up and run AIRDops locally is using the provided Makefile. The Makefile handles all setup steps automatically and works cross-platform (Windows, macOS, Linux).

**Initial Setup:**

```bash
# 1. Clone repository
git clone <repository-url>
cd aird

# 2. Configure environment variables
# Create backend/.env.local (copy from backend/env.example)
# Create infra/.env.local (copy from infra/env/services.example.env)
# Create ui/.env.local (copy from infra/env/ui.example.env.local)
# See Configuration section below for required variables

# 3. One-time setup (installs dependencies, starts services, runs migrations)
make setup

# 4. Start development servers (in separate terminals)
# Terminal 1:
make backend

# Terminal 2:
make frontend
```

**Available Make Commands:**

| Command | Description | When to Use |
|---------|-------------|-------------|
| `make setup` | Complete one-time setup: installs dependencies, starts Docker services, runs migrations | First time setup or after cloning the repository |
| `make install` | Install both backend and frontend dependencies | When dependencies change (requirements.txt or package.json updated) |
| `make install-backend` | Install only backend Python dependencies | When only backend dependencies change |
| `make install-frontend` | Install only frontend npm dependencies | When only frontend dependencies change |
| `make services` | Start/restart Docker services (PostgreSQL, Qdrant, MinIO, Airflow) | When services need to be restarted or after system reboot |
| `make migrate` | Run database migrations only | When database schema changes |
| `make backend` | Start backend development server (with hot reload) | Daily development - run in separate terminal |
| `make frontend` | Start frontend development server (Next.js) | Daily development - run in separate terminal |
| `make dev` | Show instructions for running development servers | Quick reference for starting dev servers |
| `make stop` | Stop all Docker services | When you're done working |
| `make clean` | Stop services and remove all Docker volumes (⚠️ destructive) | When you want to start fresh (removes all data) |
| `make help` | Show all available commands | Quick reference |

**Daily Development Workflow:**

```bash
# Morning: Start services (if not already running)
make services

# Start development servers in separate terminals
# Terminal 1:
make backend

# Terminal 2:
make frontend

# When done for the day:
make stop
```

**Common Scenarios:**

```bash
# After pulling latest changes with new dependencies
make install
make migrate  # If there are new migrations

# After database schema changes
make migrate

# Restart services after configuration changes
make stop
make services

# Complete reset (removes all data)
make clean
make setup
```

#### Option 2: Manual Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd aird

# 2. Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install backend dependencies
cd backend
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install frontend dependencies
cd ../ui
npm install

# 5. Configure environment variables
# Backend: Create backend/.env.local (copy from backend/env.example)
# Infrastructure: Create infra/.env.local (copy from infra/env/services.example.env)
# Frontend: Create ui/.env.local (copy from infra/env/ui.example.env.local)
# Edit each .env.local file with your configuration (see Configuration section)

# 6. Start Docker services
cd ../infra
docker compose -f docker-compose.yml --env-file .env.local up -d

# 7. Wait for services to be ready (10-15 seconds)
# On Windows: python -c "import time; time.sleep(10)"
# On Unix/Mac: sleep 10

# 8. Run database migrations
cd ../backend
python -m alembic upgrade head

# 9. Start backend server (in one terminal)
cd ..
python start_backend.py

# 10. Start frontend (in separate terminal)
cd ui
npm run dev
```

### Service URLs (Local Development)

Once all services are running, you can access:

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Airflow UI**: http://localhost:8080
  - Username: Set in `infra/.env.local` (`AIRFLOW_USERNAME`)
  - Password: Set in `infra/.env.local` (`AIRFLOW_PASSWORD`)
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **MinIO Console**: http://localhost:9001
  - Username: Set in `infra/.env.local` (`MINIO_ROOT_USER`)
  - Password: Set in `infra/.env.local` (`MINIO_ROOT_PASSWORD`)

### Troubleshooting

**Makefile not working on Windows:**
- Ensure you have `make` installed (see Prerequisites)
- Use Git Bash, WSL, or install make via Chocolatey/Scoop
- The Makefile uses Python for cross-platform compatibility, so Python must be in your PATH

**Docker services not starting:**
- Check if ports are already in use: `docker ps`
- Verify `.env.local` files are configured correctly
- Check Docker logs: `docker logs primedata-postgres`, `docker logs primedata-airflow-webserver`, etc.

**Migrations failing:**
- Ensure PostgreSQL is running and healthy: `docker ps | grep postgres`
- Verify `DATABASE_URL` in `backend/.env.local` is correct
- Check database connection: `docker exec -it primedata-postgres psql -U <user> -d <db>`

**Airflow not accessible:**
- Wait 30-60 seconds after starting services for Airflow to initialize
- Check Airflow logs: `docker logs primedata-airflow-webserver`
- Verify `AIRFLOW_DB_NAME` is set in `infra/.env.local`

**Backend/Frontend not starting:**
- Ensure virtual environment is activated (for backend)
- Check that all dependencies are installed: `make install`
- Verify environment variables in `.env.local` files

### Configuration

#### Required Environment Variables

**Backend (`backend/.env.local`)**:
```env
# Database
DATABASE_URL=postgresql://primedata:password@localhost:5432/primedata

# Object Storage (MinIO)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_SECURE=false

# Vector Database (Qdrant)
QDRANT_URL=http://localhost:6333

# Authentication
JWT_SECRET_KEY=<generate-64-char-secret>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# Frontend URL
FRONTEND_URL=http://localhost:3000
```

**Frontend (`ui/.env.local`)**:
```env
# NextAuth Configuration
NEXTAUTH_SECRET=<generate-64-char-secret>
NEXTAUTH_URL=http://localhost:3000

# Google OAuth (optional)
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Infrastructure (`infra/.env.local`)**:
```env
# PostgreSQL
POSTGRES_USER=primedata
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=primedata

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<secure-password>

# Airflow
AIRFLOW_DB_NAME=airflow
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=<secure-password>
AIRFLOW_SECRET_KEY=<generate-secret>
```

**Generate Secrets**:
```bash
# JWT and NextAuth secrets
openssl rand -hex 32

# Airflow secret key
openssl rand -base64 16
```

---

## Technical Documentation

### Database Schema

AirdOps uses PostgreSQL for metadata storage with the following core tables:

- **users**: User accounts and authentication
- **workspaces**: Workspace/organization definitions
- **workspace_members**: User-workspace associations with roles
- **products**: Product definitions and configurations
- **data_sources**: Data source configurations and status
- **pipeline_runs**: Pipeline execution history and status
- **pipeline_artifacts**: Generated artifacts (reports, summaries)
- **dq_rules**: Data quality rule definitions
- **dq_violations**: Quality violation records
- **raw_files**: Raw file metadata catalog
- **billing_profiles**: Subscription and billing information

**Schema Migrations**: Managed via Alembic. Run `alembic upgrade head` to apply migrations.

### API Architecture

#### Authentication Flow

1. **User Authentication**: NextAuth.js handles OAuth (Google) or email/password authentication
2. **Token Exchange**: Frontend exchanges NextAuth JWT for backend JWT via `/api/v1/auth/session/exchange`
3. **API Requests**: All API requests include `Authorization: Bearer <jwt_token>` header
4. **Token Validation**: Backend middleware validates JWT and extracts user context

#### API Design Principles

- **RESTful**: Standard HTTP methods and status codes
- **Versioned**: All endpoints under `/api/v1/` prefix
- **Documented**: OpenAPI/Swagger documentation at `/docs`
- **Validated**: Request/response validation via Pydantic models
- **Error Handling**: Consistent error response format

### Pipeline Architecture

#### Airflow DAG Structure

The platform uses a modular Airflow architecture:

- **DAG Files**: Minimal orchestration logic (~100 lines)
- **Task Functions**: Business logic in `dag_tasks.py` module
- **AIRD Stages**: Reusable pipeline components

**Benefits**:
- Maintainability: Business logic changes don't require DAG file changes
- Testability: Task functions can be unit tested independently
- Reusability: Task functions can be used in multiple DAGs

#### Pipeline Execution Flow

```
Ingestion → Preprocessing → Chunking → Scoring → 
Embedding → Indexing → Quality Validation → Artifact Generation → Finalization
```

Each stage:
- Reads input from previous stage
- Processes data according to configuration
- Writes output to storage
- Updates pipeline run status
- Handles errors and retries

### Storage Architecture

#### Three-Tier Storage Strategy

1. **PostgreSQL**: Metadata, configurations, user data (fast queries, ACID compliance)
2. **Qdrant**: Vector embeddings, chunk metadata, search indices (high-performance similarity search)
3. **MinIO/GCS**: Raw files, processed data, artifacts (scalable object storage)

#### Data Flow

```
Data Source → MinIO (raw bucket) → 
Processing Pipeline → MinIO (clean bucket) → 
Embedding Generation → Qdrant (vectors) + 
Metadata → PostgreSQL
```

### Security Architecture

#### Authentication & Authorization

- **Frontend**: NextAuth.js with Google OAuth and email/password
- **Backend**: JWT (HS256) with configurable expiration
- **API**: Bearer token authentication
- **Workspace-Level ACL**: Role-based access control per workspace

#### Data Security

- **Encryption at Rest**: Object storage encryption (MinIO/GCS)
- **Encryption in Transit**: HTTPS/TLS for all API communications
- **PII Handling**: Automated PII detection and redaction
- **Secret Management**: Environment variables (production: secrets manager)

---

## Deployment Guide

### Production Deployment (GCP)

AirdOps is designed for deployment on Google Cloud Platform using Infrastructure as Code (Terraform) and CI/CD (GitHub Actions).

#### Architecture Components

- **Compute Engine VM**: Hosts Docker containers (backend, frontend, Airflow, Qdrant)
- **Cloud SQL**: Managed PostgreSQL database
- **Cloud Storage**: Object storage (alternative to MinIO)
- **Load Balancer**: Nginx reverse proxy (optional)

#### Deployment Steps

1. **Infrastructure Provisioning** (Terraform)
   ```bash
   cd infra/terraform
   terraform init
   terraform plan
   terraform apply
   ```

2. **VM Configuration**
   - SSH to VM and create environment file
   - Configure database connection
   - Set up service accounts and credentials

3. **Application Deployment** (GitHub Actions)
   - Push code to repository
   - GitHub Actions workflow automatically deploys
   - Conditional builds based on file changes

For detailed deployment instructions, see the [COMPREHENSIVE_GUIDE.md](COMPREHENSIVE_GUIDE.md) in the repository.

### Docker Compose Deployment

For production-like local deployment:

```bash
docker-compose -f infra/docker-compose.prod.yml --env-file infra/.env up -d
```

This starts all services in production mode:
- Backend API
- Frontend (Next.js standalone)
- Airflow (scheduler + webserver)
- Qdrant
- PostgreSQL
- MinIO

---

## API Reference

### Base URL

- **Production**: `https://airdops.com/api`
- **Local Development**: `http://localhost:8000/api`

### Authentication

All endpoints (except public endpoints) require JWT authentication:

```http
Authorization: Bearer <jwt_token>
```

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/session/exchange` - Exchange NextAuth token for backend JWT
- `POST /api/v1/auth/signup` - User registration
- `POST /api/v1/auth/login` - User login

#### Products
- `GET /api/v1/products` - List products
- `POST /api/v1/products` - Create product
- `GET /api/v1/products/{id}` - Get product details
- `PUT /api/v1/products/{id}` - Update product
- `DELETE /api/v1/products/{id}` - Delete product

#### Data Sources
- `GET /api/v1/datasources` - List data sources
- `POST /api/v1/datasources` - Create data source
- `POST /api/v1/datasources/{id}/sync-full` - Trigger data sync

#### Pipeline
- `POST /api/v1/pipeline/run` - Trigger pipeline execution
- `GET /api/v1/pipeline/runs` - List pipeline runs
- `GET /api/v1/pipeline/runs/{id}` - Get pipeline run details

#### Data Quality
- `GET /api/v1/data-quality/rules/{product_id}` - Get quality rules
- `PUT /api/v1/data-quality/rules/{product_id}` - Update quality rules
- `GET /api/v1/data-quality/violations/{product_id}` - Get violations

#### AI Readiness
- `GET /api/v1/ai-readiness/{product_id}` - Get AI readiness score
- `POST /api/v1/products/{id}/apply-recommendation` - Apply optimization recommendations

**Full API Documentation**: Available at `/docs` (Swagger UI) or `/redoc` (ReDoc)

---

## Enterprise Features

### Scalability

- **Horizontal Scaling**: Stateless API design enables multiple backend instances
- **Database Connection Pooling**: Efficient database resource management
- **Vector Database Scaling**: Qdrant supports clustering and horizontal scaling
- **Object Storage**: MinIO/GCS provide virtually unlimited storage

### Reliability

- **Error Handling**: Comprehensive error handling and retry logic
- **Pipeline Monitoring**: Airflow provides task-level monitoring and alerting
- **Health Checks**: Built-in health check endpoints for all services
- **Graceful Degradation**: Fallback mechanisms for service failures

### Compliance & Governance

- **Audit Logging**: Complete audit trail of user actions and system changes
- **Data Retention Policies**: Configurable retention policies for data and artifacts
- **Access Control**: Fine-grained permissions and workspace isolation
- **Data Lineage**: Complete tracking of data transformations and processing

### Monitoring & Observability

- **Pipeline Metrics**: Execution time, success rates, resource usage
- **Quality Metrics**: Real-time quality scores and trend analysis
- **Usage Analytics**: Product usage, data volume, embedding generation tracking
- **System Health**: Service status, database connectivity, storage availability

---

## Support & Resources

- **Documentation**: This README and [COMPREHENSIVE_GUIDE.md](COMPREHENSIVE_GUIDE.md)
- **API Documentation**: Interactive Swagger UI at `/docs`
- **GitHub Repository**: Source code and issue tracking
- **Production Instance**: https://airdops.com

---

**AirdOps** - Enterprise AI-Ready Data Platform  
*Transform data into production-ready AI applications with confidence.*
