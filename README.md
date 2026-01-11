# AIRDops Comprehensive Guide

**AI-ready data from any source. Ingest, clean, chunk, embed & index. Test and export with confidence.**

This comprehensive guide covers everything you need to know about AIRDops - from getting started to advanced configuration, optimization, troubleshooting, and enterprise deployment.

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Core Features & Capabilities](#core-features--capabilities)
4. [Configuration Guide](#configuration-guide)
5. [AI Readiness & Optimization](#ai-readiness--optimization)
6. [Policy Evaluation](#policy-evaluation)
7. [User Guide](#user-guide)
8. [API Reference](#api-reference)
9. [Architecture & Development](#architecture--development)
10. [Troubleshooting](#troubleshooting)
11. [Enterprise Features](#enterprise-features)
12. [Deployment & Operations](#deployment--operations)
    - [Local Development](#local-development)
    - [GCP Cloud Deployment](#gcp-cloud-deployment)
    - [GitHub Actions CI/CD](#github-actions-cicd)
    - [Conditional Builds](#conditional-builds)
    - [Idempotency](#idempotency)
    - [Production Considerations](#production-considerations)

---

## Overview

AIRDops is a comprehensive enterprise data platform designed for AI workflows. It provides end-to-end data processing, from ingestion to vectorization, with enterprise-grade data quality management, billing & gating, team collaboration, and advanced analytics.

### Key Capabilities

- **Data Ingestion**: Connect web sources, folders, databases, and APIs
- **Intelligent Chunking**: Auto and manual modes with AI-powered optimization
- **Vector Embeddings**: Support for OpenAI, MiniLM, BGE, GTE, Instructor, and other embedding models
- **Quality Management**: 7 rule types for comprehensive data validation
- **AI Readiness Assessment**: Quality scoring and actionable recommendations
- **Team Collaboration**: Role-based access control and workspace management
- **Billing & Usage**: Stripe integration with subscription plans and usage tracking
- **Export & Provenance**: Secure data export with complete lineage tracking
- **Enterprise Architecture**: Microservices design with scalable components

### Service URLs (Default)

- **AIRDops UI**: http://localhost:3000
- **AIRDops API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Airflow UI**: http://localhost:8080
- **MinIO Console**: http://localhost:9001
- **Qdrant Dashboard**: http://localhost:6333

### Environment Configuration

⚠️ **IMPORTANT**: All credentials must be set via environment variables! No defaults are provided for security.

**Required Environment Variables for Docker Compose:**

1. **Database Configuration** (choose one):
   - Option A: `DATABASE_URL` - Full connection string (simplest)
   - Option B: Individual components (allows database name from secrets):
     - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`
     - Optional: `AIRFLOW_DB_NAME` for separate Airflow database

2. **MinIO Configuration:**
   - `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`

3. **Airflow Configuration:**
   - `AIRFLOW_USERNAME`, `AIRFLOW_PASSWORD`, `AIRFLOW_SECRET_KEY`
   - `AIRFLOW_DB_NAME` (if using separate database)

4. **Security:**
   - `JWT_SECRET_KEY`, `NEXTAUTH_SECRET`

**Setup Instructions:**

1. For local development: Create `.env` file in `infra/` directory based on `infra/env/services.example.env`
2. For production: Set all variables via secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
3. Copy `backend/env.example` to `backend/.env` and fill in values
4. Copy `env.production.example` to `.env.production` for production

See configuration templates in `backend/env.example`, `infra/env/services.example.env`, and `env.production.example`.

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker & Docker Compose**
- **Git**
- **RAM**: Minimum 8GB, Recommended 16GB+
- **Storage**: Minimum 10GB free space

### Quick Setup

#### **Option 1: Quick Setup**

```bash
# Clone repository
git clone <repository-url>
cd AIRDops

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

This will:
- Create and activate virtual environment
- Install all dependencies
- Set up the database

#### **Option 2: Manual Setup**

```bash
# 1. Clone repository
git clone <repository-url>
cd AIRDops

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install backend dependencies
cd backend
pip install -r requirements.txt

# 4. Install frontend dependencies
cd ../ui
npm install

# 5. Configure environment variables (REQUIRED!)
# ⚠️ IMPORTANT: Create .env files before starting services - all credentials must be set!
cd ../infra
# Copy example file and fill in your values
cp env/services.example.env .env
# Edit .env and set all required values (POSTGRES_*, MINIO_ROOT_*, AIRFLOW_*, etc.)

cd ../backend
# Copy example file and fill in your values  
cp env.example .env
# Edit .env and set DATABASE_URL or individual POSTGRES_* components

# 6. Start Docker services (will use .env file automatically)
cd ..
docker-compose -f infra/docker-compose.yml --env-file infra/.env up -d

# 7. Run database migrations
cd backend
alembic upgrade head

# 7. Start services
# Terminal 1: Backend (Platform-agnostic)
python start_backend.py
# Or manually:
# cd backend
# python -m uvicorn primedata.api.app:app --reload --port 8000

# Terminal 2: Frontend
cd ui
npm run dev
```

### Database Setup

1. **Run database migrations:**
   ```bash
   # Platform-agnostic (works on Windows, macOS, Linux)
   cd backend
   # Activate virtual environment (if using one)
   # Windows: venv\Scripts\activate
   # macOS/Linux: source venv/bin/activate
   alembic upgrade head
   ```

### First Steps

1. **Access the UI**: Go to http://localhost:3000
2. **Sign in with Google**: Use your Google account for authentication
3. **Create a Product**: Click "New Product" and fill in details
4. **Configure Chunking**: Choose between Auto or Manual mode
5. **Add Data Sources**: Connect web URLs, folders, or other data sources
6. **Run Pipeline**: Execute the data processing pipeline
7. **Monitor Results**: Check analytics dashboard and insights

---

## Core Features & Capabilities

### Enterprise Data Quality Management

#### **7 Rule Types**

1. **Required Fields**: Ensure critical fields are present
2. **Max Duplicate Rate**: Prevent excessive duplication
3. **Min Chunk Coverage**: Ensure adequate content coverage
4. **Bad Extensions**: Block problematic file types
5. **Max File Size**: Control file size limits
6. **Content Validation**: Validate content quality and structure
7. **Custom Rules**: Define your own validation logic

#### **Real-time Monitoring**

- Continuous quality assessment
- Violation tracking and reporting
- Trend analysis over time
- Alert system for quality issues

#### **Audit Trail & Compliance**

- Complete history of rule changes
- User attribution and timestamps
- Compliance reporting capabilities
- Database-first architecture with ACID compliance

### Billing & Gating with Stripe

#### **Subscription Plans**

- **Free**: 3 products, 5 data sources/product, 10 pipeline runs/month
- **Pro ($99/month)**: 25 products, 50 data sources/product, 1,000 runs/month
- **Enterprise ($999/month)**: Unlimited everything

#### **Usage Tracking**

- Products, data sources, pipeline runs
- Vector storage and embedding usage
- Real-time usage monitoring
- Plan limit enforcement

### Team Management

- **Role-Based Access**: Owner, Admin, Editor, Viewer
- **Workspace Management**: Multi-workspace support
- **Team Invitations**: Invite members with specific roles
- **User Profiles**: Comprehensive profile management

### Advanced Chunking Configuration

#### **Auto Mode (Recommended)**

- AI analyzes content and optimizes settings
- Automatically detects content type (legal, code, documentation)
- Provides confidence scores and recommendations
- Best for most use cases

#### **Manual Mode**

- Full control over chunk size, overlap, and strategy
- Advanced configuration options
- Best for specific requirements

#### **Available Strategies**

1. **Fixed Size** (`fixed_size`): Splits by character count exactly
2. **Semantic** (`semantic`): Paragraph-based chunking for structured documents
3. **Recursive** (`recursive`): Hierarchical splitting for code/technical docs

**Note**: When you select "Semantic" in the UI, the backend uses paragraph-based chunking, which is ideal for structured documents like annual reports.

### Export & Data Management

- Export bundles (ZIP archives)
- Complete data provenance tracking
- Version control for processed data
- Secure downloads with presigned URLs
- Metadata inclusion

### Data Connectors

- **Web**: Scrape websites and online content
- **Folder**: Process files from local or remote directories
- **Database**: Connect to database systems
- **API**: RESTful API data ingestion

---

## Configuration Guide

### Chunking Configuration

#### **Optimal Settings for Different Content Types**

**Technical Documentation (Annual Reports, Technical Docs)**
```json
{
  "chunking_mode": "manual",
  "manual_settings": {
    "chunking_strategy": "semantic",
    "chunk_size": 800,
    "chunk_overlap": 300,
    "min_chunk_size": 200,
    "max_chunk_size": 1500
  }
}
```

**Code/Technical Documentation**
```json
{
  "chunk_size": 600,
  "chunk_overlap": 200,
  "strategy": "semantic"
}
```

**General Knowledge Base**
```json
{
  "chunk_size": 1000,
  "chunk_overlap": 250,
  "strategy": "semantic"
}
```

**Legal/Regulatory Documents**
```json
{
  "chunk_size": 1200,
  "chunk_overlap": 400,
  "strategy": "semantic"
}
```

#### **Key Principles**

1. **Chunk Size Trade-off**
   - **Smaller chunks (600-800 tokens)**: Better precision, higher relevance scores
   - **Larger chunks (1200-1500 tokens)**: More context, better for complex questions
   - **Recommendation**: Start with 800-1000 tokens for documentation

2. **Overlap Matters**
   - **17% overlap**: Current default (200 tokens on 1200 token chunks)
   - **30-40% overlap**: Recommended for better context preservation
   - **Why**: Prevents losing context at chunk boundaries

3. **Strategy Selection**
   - **Semantic**: Paragraph-based (best for structured documents)
   - **Fixed Size**: Uniform splitting (simple documents)
   - **Recursive**: Hierarchical (code, technical docs)

### Embedding Configuration

#### **Available Models**

**OpenAI Models**:
- `openai-3-small` (1536 dim)
- `openai-3-large` (3072 dim)

**Open-Source Models** (Sentence Transformers):
- **MiniLM**: `minilm` (384 dim), `minilm-l12` (384 dim)
- **MPNet**: `mpnet` (768 dim)
- **BGE Models**: `bge-small-en` (384 dim), `bge-base-en` (768 dim), `bge-large-en` (1024 dim)
- **E5 Models**: `e5-small` (384 dim), `e5-base` (768 dim), `e5-large` (1024 dim)
- **GTE Models**: `gte-small` (384 dim), `gte-base` (768 dim), `gte-large` (1024 dim)
- **Instructor Models**: `instructor-base` (768 dim), `instructor-large` (768 dim)
- **Multilingual Models**: Various multilingual variants with 768 and 1024 dimensions

#### **Configuration**

```json
{
  "embedding_config": {
    "embedder_name": "bge-large-en",
    "embedding_dimension": 1024
  }
}
```

**Note**: OpenAI models require an API key configured in workspace settings or environment variables.

**Adaptive Batching**: The system automatically adjusts batch sizes based on model dimensions:
- **1024+ dimensions**: Batch size 3 (e.g., BGE Large)
- **768+ dimensions**: Batch size 10
- **Smaller models**: Batch size 32

### Playbook Selection

Playbooks define preprocessing strategies:
- **TECH**: Technical documentation with structured chunking
- **HEALTHCARE**: Healthcare/regulatory content
- **REGULATORY**: Legal/regulatory documents
- **SCANNED**: OCR-heavy content cleanup

You can also create custom playbooks using the UI.

### Environment Variables

#### **Backend (.env)**

```env
# Database
# ⚠️ WARNING: Replace with secure passwords in production!
DATABASE_URL=postgresql://primedata:YOUR_PASSWORD@localhost:5432/primedata

# MinIO
# ⚠️ WARNING: Replace with secure credentials in production!
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=YOUR_MINIO_PASSWORD
MINIO_SECURE=false

# Qdrant
QDRANT_URL=http://localhost:6333
# For Qdrant Cloud:
# QDRANT_HOST=your-cluster-id.qdrant.tech
# QDRANT_API_KEY=your-api-key-here
# QDRANT_USE_SSL=true

# Stripe (for billing features)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...

# Frontend URL
FRONTEND_URL=http://localhost:3000

# Security
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]

# Development Settings
DEBUG=true
TESTING_MODE=false
DISABLE_AUTH=false
```

#### **Frontend (.env.local)**

```env
# NextAuth Configuration
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=http://localhost:3000

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Stripe Configuration
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## AI Readiness & Optimization

### Overview

The AIRDops optimizer actively improves data quality and pushes scores from "good" to "excellent" (>85%) to maximize AI application efficiency. Rather than just reporting metrics, it provides actionable recommendations.

### The 4x Efficiency Goal

**Why Excellence Matters (>85% scores):**

1. **Better RAG Performance**: High-quality data delivers more accurate search results
2. **Reduced AI Errors**: Clean, normalized data reduces hallucinations
3. **Faster Processing**: Well-structured data processes faster
4. **Better Embeddings**: Quality text produces better vector embeddings
5. **Higher Confidence**: Excellent scores mean trusted AI outputs

**Result**: Companies using excellent-quality data (>85%) see **4x efficiency gains** in AI initiatives compared to "good" quality data (70-85%).

### How Optimizations Work

**Important**: You must re-run the pipeline after applying optimizations. When you click "Apply" on recommendations, it only saves the configuration flags. The actual optimizations are applied during the preprocessing stage of the next pipeline run.

**Does it use LLMs? NO!**

The optimizations are **pattern-based text processing functions**, NOT LLM-based. They use:
- **Regular expressions (regex)** for pattern matching and replacement
- **Text analysis algorithms** for correction
- **Rule-based processing** (not AI/ML models)

This makes them:
- ✅ **Fast**: No API calls, no latency
- ✅ **Predictable**: Consistent results
- ✅ **Cost-effective**: No API costs
- ✅ **Reliable**: Works offline

### Recommendation Types

#### 1. Quality Normalization
- **Action**: `enhance_normalization`
- **What it does**: Enhances text normalization (fixes OCR errors, normalizes whitespace)
- **Expected Impact**: +15-25% Quality score improvement
- **When to use**: Quality score < 85%

**Specific Fixes**:
- Removes control characters (except newlines/tabs)
- Normalizes whitespace (multiple spaces → single space)
- Fixes punctuation spacing
- Normalizes quotes and dashes
- Fixes ellipsis
- Removes excessive line breaks

#### 2. Error Correction
- **Action**: `error_correction`
- **What it does**: Fixes common OCR mistakes and typos
- **Expected Impact**: +5-10% Quality score improvement
- **When to use**: Quality score < 85%

**Specific Fixes**:
- Common OCR word errors (teh → the, adn → and)
- Fixes excessive repeated letters
- Adds missing space after sentences

#### 3. Metadata Extraction
- **Action**: `extract_metadata`
- **What it does**: Extracts additional metadata (dates, authors, versions)
- **Expected Impact**: +5-15% Metadata Presence improvement
- **When to use**: Metadata Presence < 90%

**Specific Extractions**:
- Date extraction (various formats)
- Author extraction (By:, Author:, Written by:)
- Version extraction (v1.0, Version 1.0, ver 2.3.4)

#### 4. Increase Chunk Overlap
- **Action**: `increase_chunk_overlap`
- **What it does**: Increases chunk overlap to reduce context loss
- **Expected Impact**: +3-7% Completeness, +5-10% AI Trust Score
- **When to use**: Completeness < 90%

#### 5. Switch Playbook
- **Action**: `switch_playbook`
- **What it does**: Changes to a playbook optimized for your content type
- **When to use**: When current playbook is not optimal

#### 6. Apply All Quality Improvements
- **Action**: `apply_all_quality_improvements`
- **What it does**: Applies all quality enhancements at once
- **Expected Impact**: Maximum improvement - pushes scores to excellent (>85%)
- **When to use**: When you want to maximize AI readiness

### Example Workflow

**Starting Point:**
```
AI Trust Score: 74.9% (good)
Quality Score: 56.9% (below optimal)
Completeness: 75.0% (good)
Policy: Passed
```

**Recommendations:**
1. Quality Normalization (High Priority) - Expected: +15-25% Quality improvement
2. Error Correction (High Priority) - Expected: +5-10% Quality improvement
3. Apply All Quality Improvements (High Priority) - Expected: +10.1% Trust Score improvement

**After Applying and Re-running Pipeline:**
```
AI Trust Score: 85.0%+ (excellent) ✅
Quality Score: 75.0%+ (excellent) ✅
Completeness: 80.0%+ (improved) ✅
```

### How to Use Recommendations

**Via UI:**
1. Navigate to Product Insights page
2. Review actionable recommendations with expected impact
3. Click "Apply" button on any recommendation
4. Re-run the pipeline to see improvements
5. Monitor progress after pipeline completes

**Via API:**
```bash
POST /api/v1/products/{product_id}/apply-recommendation
{
  "action": "apply_all_quality_improvements",
  "config": {
    "enhance_normalization": true,
    "error_correction": true,
    "extract_metadata": true,
    "increase_overlap": true
  }
}
```

### Score Thresholds

| Score Range | Status | Recommendation |
|-------------|--------|----------------|
| < 50% | Poor | Apply all quality improvements (high priority) |
| 50-70% | Acceptable | Apply targeted improvements |
| 70-85% | Good | Push to excellent (>85%) |
| > 85% | Excellent | ✅ Maximizes AI efficiency (4x gains) |

### Best Practices

1. Apply high-priority recommendations first
2. Use "Apply All Quality Improvements" for maximum impact
3. Re-run pipeline after each set of changes
4. Target excellence (>85%) for maximum efficiency
5. Monitor iteratively: apply, re-run, check, repeat

---

## Policy Evaluation

### What is Policy Evaluation?

Policy Evaluation is a quality gate system that checks whether your processed data meets predefined quality and compliance thresholds. It ensures your data is ready for production use in AI/ML applications.

### Purpose

The Policy Evaluation serves as a compliance check to ensure:
1. Data meets minimum quality standards
2. Security requirements are satisfied (PII properly handled)
3. Metadata is sufficiently complete
4. Data is ready for knowledge base/RAG applications

### Policy Thresholds (Default Values)

| Metric | Default Threshold | What It Checks |
|--------|------------------|----------------|
| **AI Trust Score** | ≥ 50% | Overall data quality and completeness |
| **Secure** | ≥ 90% | PII detection and redaction effectiveness |
| **Metadata Presence** | ≥ 80% | Completeness of metadata |
| **KnowledgeBase Ready** | ≥ 50% | Suitability for RAG/search applications |

### Evaluation Results

#### ✅ Passed
- **Meaning**: All metrics meet or exceed thresholds
- **Implication**: Data is compliant and ready for production
- **What Happens**: Product status set to "READY"

#### ❌ Failed
- **Meaning**: One or more metrics below thresholds
- **Implication**: Data needs improvement
- **What Happens**: Product status set to "FAILED_POLICY"

#### ⚠️ Warnings
- **Meaning**: Data passes but some metrics below optimal
- **Implication**: Data is usable but could be improved
- **What Happens**: Product status may be "READY_WITH_WARNINGS"

### Configuration

Policy thresholds can be customized via environment variables:

```bash
AIRD_POLICY_MIN_TRUST_SCORE=50.0
AIRD_POLICY_MIN_SECURE=90.0
AIRD_POLICY_MIN_METADATA_PRESENCE=80.0
AIRD_POLICY_MIN_KB_READY=50.0
```

### Improving Policy Results

Use the Optimization Suggestions in the UI to:
- Improve chunking configuration
- Enhance text normalization
- Enable error correction
- Improve metadata extraction
- Switch to better playbooks

Then re-run the pipeline to re-evaluate.

---

## User Guide

### Product Management

#### Creating a Product

1. Go to **Products** → **New Product**
2. Fill in product details (name, description, workspace)
3. Configure chunking (Auto or Manual mode)
4. Add data sources
5. Set data quality rules
6. Run pipeline

#### Product Actions

- **Edit**: Modify product settings
- **Run Pipeline**: Execute data processing
- **View Results**: See processed data and metrics
- **Export**: Download processed data
- **Delete**: Remove the product

### Data Source Management

#### Supported Types

- **Web**: Scrape websites and online content
- **Folder**: Process files from local or remote directories
- **Database**: Connect to database systems
- **API**: RESTful API data ingestion

#### Configuration Steps

1. Go to **Data Sources** → **Add Data Source**
2. Choose data source type
3. Configure settings
4. Test connection
5. Save and sync

**Important**: For folder data sources, use Docker container paths (`/opt/airflow/data`) not Windows paths (`D:\projects\data`).

### Pipeline Execution

#### Running a Pipeline

1. Go to **Products** → Select your product
2. Click **Run Pipeline**
3. Monitor progress in real-time
4. View results and metrics

#### Pipeline Stages

1. **Preprocessing**: Normalization, chunking, sectioning
2. **Validation**: Data quality checks
3. **Fingerprinting**: Quality metrics calculation
4. **Policy Evaluation**: Compliance checking
5. **Indexing**: Embedding generation and vector storage

#### Version Management

The system uses smart version resolution:
- **Auto-Detection**: When no version is specified, automatically uses the latest ingested version
- **Explicit Version**: You can specify a version to process
- **Validation**: System validates that raw files exist for the specified version

### Analytics & Monitoring

#### Metrics Dashboard

- Product performance overview
- Data quality trends
- Team activity monitoring
- Usage analytics and billing insights

#### Pipeline Metrics

- Chunking performance and quality
- Embedding generation speed
- Vector indexing efficiency
- Overall pipeline health

### Team Management

#### Team Roles

- **Owner**: Full access, can manage team and billing
- **Admin**: Full access, can manage team (no billing)
- **Editor**: Can create and manage products
- **Viewer**: Read-only access

#### Managing Team Members

1. Go to **Team** → **Invite Member**
2. Enter email address
3. Select role
4. Send invitation

### Billing & Subscriptions

#### Subscription Plans

- **Free**: 3 products, 5 data sources/product, 10 runs/month
- **Pro ($99/month)**: 25 products, 50 data sources/product, 1,000 runs/month
- **Enterprise ($999/month)**: Unlimited everything

#### Managing Billing

- Monitor usage against plan limits
- Upgrade/downgrade subscription plans
- Manage payment methods
- Track usage analytics

---

## API Reference

### Base URL

```
http://localhost:8000
```

### Authentication

All API endpoints require authentication via JWT tokens obtained through the authentication flow.

```http
Authorization: Bearer <jwt_token>
```

### Key Endpoints

#### **Authentication & User Management**

- `POST /api/v1/auth/session/exchange` - Exchange NextAuth token for backend JWT
- `GET /api/v1/users/me` - Get current user information
- `PUT /api/v1/user/profile` - Update user profile
- `GET /api/v1/workspaces/` - Get user's workspaces

#### **Product Management**

- `POST /api/v1/products` - Create a new product
- `GET /api/v1/products` - List products
- `GET /api/v1/products/{product_id}` - Get product details
- `PUT /api/v1/products/{product_id}` - Update product
- `DELETE /api/v1/products/{product_id}` - Delete product

#### **Data Source Management**

- `POST /api/v1/datasources` - Create a new data source
- `GET /api/v1/datasources` - List data sources
- `GET /api/v1/datasources/{datasource_id}` - Get data source details
- `PUT /api/v1/datasources/{datasource_id}` - Update data source
- `DELETE /api/v1/datasources/{datasource_id}` - Delete data source

#### **Pipeline Management**

- `POST /api/v1/pipeline/run` - Trigger a pipeline run
- `GET /api/v1/pipeline/runs` - List pipeline runs
- `GET /api/v1/pipeline/runs/{run_id}` - Get pipeline run details

#### **Data Quality Management**

- `GET /api/v1/data-quality/rules/{product_id}` - Get data quality rules
- `PUT /api/v1/data-quality/rules/{product_id}` - Update data quality rules
- `GET /api/v1/data-quality/violations/{product_id}` - Get data quality violations

#### **Analytics & Metrics**

- `GET /api/v1/analytics/metrics` - Get analytics metrics

#### **Embedding Models**

- `GET /api/v1/embedding-models` - Get available embedding models
- `GET /api/v1/embedding-models/{model_id}` - Get specific model details

#### **AI Readiness Assessment**

- `GET /api/v1/ai-readiness/{product_id}` - Get AI readiness score

#### **Playground & Testing**

- `POST /api/v1/playground/query` - Test queries against processed data

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Architecture & Development

### System Architecture

#### **Microservices Design**

- **Backend API**: FastAPI (Python) - http://localhost:8000
- **Frontend UI**: Next.js (React/TypeScript) - http://localhost:3000
- **Vector Database**: Qdrant - http://localhost:6333
- **Object Storage**: MinIO - http://localhost:9000
- **Orchestration**: Airflow - http://localhost:8080
- **Database**: PostgreSQL - localhost:5432

#### **Data Flow**

1. **Ingestion**: Data sources → MinIO (raw bucket)
2. **Preprocessing**: Raw files → Normalized/Chunked → MinIO (clean bucket)
3. **Embedding**: Chunks → OpenAI/MiniLM/BGE/etc. → Vectors
4. **Indexing**: Vectors → Qdrant (vector database)
5. **Query**: User query → Embedding → Qdrant search → Results

### Project Structure

```
AIRDops/
├── backend/                    # FastAPI backend
│   ├── src/primedata/         # Python package
│   │   ├── api/               # API endpoints
│   │   ├── core/              # Core functionality
│   │   ├── db/                # Database models
│   │   ├── indexing/          # Embedding and vector operations
│   │   ├── connectors/        # Data source connectors
│   │   ├── ingestion_pipeline/ # Pipeline stages
│   │   │   ├── dag_tasks.py  # Task functions
│   │   │   └── aird_stages/  # AIRD pipeline stages
│   │   └── services/          # Business logic services
│   ├── alembic/               # Database migrations
│   └── requirements.txt
├── ui/                        # Next.js frontend
│   ├── app/                   # App Router pages
│   ├── components/            # React components
│   └── lib/                   # Utilities
├── infra/                     # Infrastructure
│   ├── docker-compose.yml
│   └── airflow/               # Airflow configuration
│       └── dags/              # DAG files
└── docs/                      # Documentation
```

### Airflow Modular Architecture

The system uses a modular architecture for Airflow DAGs:

- **DAG Files**: Minimal orchestration logic only (~100 lines)
- **Task Functions**: Business logic in `dag_tasks.py` module
- **AIRD Stages**: Reusable pipeline components

**Benefits**:
- ✅ Maintainability: Business logic changes don't require DAG file changes
- ✅ Testability: Task functions can be unit tested independently
- ✅ Reusability: Task functions can be used in multiple DAGs
- ✅ Version Control: Clear separation in git history

### Database Migrations

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

### Qdrant as Single Source of Truth

The system uses Qdrant as the single source of truth for all chunk metadata:

- **Metadata Storage**: All chunk metadata stored in Qdrant payload
- **ACL Filtering**: Uses Qdrant scroll API for access control
- **Analytics Queries**: Uses Qdrant for analytics instead of PostgreSQL
- **No Duplication**: Eliminates data duplication between PostgreSQL and Qdrant

**Qdrant Payload Fields**:
- `created_at`, `collection_id`, `version`
- `source_file`, `page_number`, `document_id`
- `field_name`, `tags`, `score`
- `text`, `text_length`, `source`, `audience`
- `timestamp`, `product_id`, `index_scope`
- `doc_scope`, `field_scope`, `token_est`

### Database Optimization

The system implements enterprise best practices for database optimization:

**Hybrid Storage Pattern**:
- Small JSON fields stored inline in PostgreSQL
- Large JSON fields (>1MB) stored in S3
- Lazy loading: Fields loaded from S3 when needed

**Archiving**:
- Old pipeline run metrics archived to S3 after 90 days
- DQ violations can be archived to S3
- Reduces database storage costs

**Indexing**:
- Indexes on frequently queried columns
- Composite indexes for common query patterns
- Performance optimization for large datasets

**NOT NULL Constraints**:
- Required fields marked as NOT NULL
- Default values for existing data
- Data integrity enforcement

---

## Troubleshooting

### Quick Diagnostics

```bash
# System health check
curl http://localhost:8000/health

# Expected response shows status of all services
{
  "status": "healthy",
  "database": {"status": "healthy"},
  "qdrant": {"status": "healthy"},
  "minio": {"status": "healthy"},
  "airflow": {"status": "healthy"}
}
```

### Common Issues

#### Setup Issues

**Virtual Environment Problems**
```bash
# Activate virtual environment
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**Docker Services Not Running**
```bash
# Check service status
docker-compose -f infra/docker-compose.yml ps

# Restart services
docker-compose -f infra/docker-compose.yml restart
```

**Port Conflicts**
```bash
# Check what's using the ports
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Linux/Mac
```

#### Authentication Issues

- Verify Google OAuth client ID and secret
- Check JWT token expiration
- Clear browser cache and cookies
- Ensure NEXTAUTH_SECRET is configured

#### Pipeline Issues

**"No raw data found for preprocessing"**
- Check data source configuration (use Docker container paths)
- Verify file paths (use `/opt/airflow/data` not Windows paths)
- Check file permissions
- Review ingest task logs in Airflow UI

**Database Connection Errors**
- Verify PostgreSQL is running: `docker-compose ps postgres`
- Check database credentials
- Verify network connectivity
- Review database logs

**Import Errors in Airflow**
- Check PYTHONPATH environment variable
- Verify module imports in DAG
- Check file permissions
- Review Airflow logs

**DAG Import Timeout**
- Move heavy imports inside task functions (lazy imports)
- Reduce module-level code execution
- Check for circular imports

**Indexing Task Timeout**
- Use adaptive batch sizing for large models
- Increase execution timeout in DAG
- Use smaller embedding models for testing

#### Configuration Not Saving

1. Check browser console for errors
2. Verify backend logs for save requests
3. Ensure database connection is working
4. Check for validation errors in response

#### Embedding Issues

**Hash-based Fallback Warnings**
- Install `openai` package in backend: `pip install openai>=1.0.0`
- Install `openai` package in Airflow (add to Dockerfile)
- Verify OpenAI API key is configured
- Check `/api/v1/products/{id}/embedding-diagnostics` endpoint

**Dimension Mismatch**
- Ensure query and stored embeddings use same model
- Check embedding configuration matches
- Verify model dimension settings

#### Search Results Issues

**Poor Search Results**
- Verify OpenAI embeddings are being used (not hash-based)
- Check chunking configuration (size, overlap, strategy)
- Ensure document content is relevant to queries
- Try optimizing chunk size and overlap

**Document Links Not Working**
- Verify MinIO is accessible
- Check presigned URL generation
- Ensure file paths are correct (v/{version}/clean/)


#### Data Quality Issues

**Rules not saving**
- Check database connection
- Validate rule configuration format
- Review API response for errors

**Violations not detected**
- Verify rule evaluation is running
- Check rule configuration
- Test rules with sample data

### Getting Help

1. **Check Documentation**: Review relevant sections
2. **Review Logs**: Check backend/Airflow logs
3. **Health Check**: Use http://localhost:8000/health
4. **Service Status**: Verify all services are running

---

## Enterprise Features

### Enterprise Data Quality Management

#### **Database-First Architecture**

- **ACID Compliance**: Transactional rule updates
- **Audit Trail**: Complete change history with user attribution
- **Concurrent Access**: Multi-user rule management with conflict resolution
- **Security**: Role-based access control and data encryption

#### **Rule Lifecycle Management**

- **Rule Creation**: Template selection, configuration, testing, review, activation
- **Rule Updates**: Change request, impact analysis, testing, approval, deployment
- **Rule Retirement**: Deprecation notice, impact assessment, migration planning, deactivation, archive

#### **Quality Monitoring**

- **Real-time Monitoring**: Continuous rule evaluation with violation alerts
- **Performance Metrics**: Rule execution performance and system resource usage
- **Quality Dashboards**: Real-time quality scores and violation trend analysis
- **Compliance Reports**: Regulatory compliance status and audit trail summaries

### Version Management

#### **Smart Version Resolution**

The system implements Option C (Hybrid Approach) for version management:

- **Auto-Detection**: When no version is specified, automatically uses latest ingested version
- **Explicit Control**: You can specify a version to process
- **Validation**: System validates that raw files exist for the specified version
- **Helpful Errors**: Guides users to correct action when version not found

**Benefits**:
- ✅ User-friendly: No manual version coordination needed
- ✅ Automatic: Always processes latest available data
- ✅ Flexible: Still allows explicit version control
- ✅ Enterprise-grade: Follows industry best practices

### Raw File Tracking

#### **Metadata Catalog Pattern**

- **Database**: Fast queries for file metadata
- **MinIO**: Scalable object storage for files
- **Separation**: Clear boundaries between systems

#### **Enterprise Enhancements**

- **Status Tracking**: Track file lifecycle (ingesting, ingested, processing, processed, failed, deleted)
- **File Validation**: Validate files exist in MinIO before processing
- **Checksum/Integrity**: Store file checksum/ETag for integrity checking
- **Reconciliation**: Periodic job to reconcile DB and MinIO
- **Soft Delete**: Audit trail of deletions with retention policies
- **Audit Logging**: Complete change history for compliance

### Database Optimization

#### **Hybrid Storage Pattern**

- **Small JSON**: Stored inline in PostgreSQL
- **Large JSON**: Stored in S3 (MinIO) when >1MB
- **Lazy Loading**: Fields loaded from S3 when accessed
- **Transparent**: API responses maintain compatibility

#### **Archiving**

- **Pipeline Runs**: Metrics archived to S3 after 90 days
- **DQ Violations**: Can be archived to S3 for long-term storage
- **Cost Optimization**: Reduces database storage costs

#### **Performance Optimization**

- **Indexes**: Added on frequently queried columns
- **Composite Indexes**: For common query patterns
- **NOT NULL Constraints**: Data integrity enforcement

---

## Deployment & Operations

### Local Development

#### **Platform-Agnostic Scripts**

AIRDops uses Python scripts that work on Windows, macOS, and Linux:

**Start Backend Server:**
```bash
# Works on all platforms (Windows, macOS, Linux)
python start_backend.py
```

The script automatically:
- Detects your operating system
- Finds and activates virtual environment (`.venv` or `venv`)
- Sets PYTHONPATH correctly
- Starts the FastAPI server with hot reload

**Benefits:**
- ✅ Single script for all platforms
- ✅ No need for separate `.bat` and `.sh` files
- ✅ Automatic virtual environment detection
- ✅ Cross-platform compatibility

#### **Docker Compose Setup**

```bash
# Start all services
docker-compose -f infra/docker-compose.yml up -d

# Check service status
docker-compose -f infra/docker-compose.yml ps

# View logs
docker-compose -f infra/docker-compose.yml logs [service_name]

# Restart services
docker-compose -f infra/docker-compose.yml restart [service_name]
```

### GCP Cloud Deployment

AIRDops can be deployed to Google Cloud Platform (GCP) using Terraform for Infrastructure as Code (IaC) and GitHub Actions for CI/CD.

#### **Architecture**

```
┌─────────────────────────────────────────┐
│         GCP Cloud Platform              │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Cloud SQL (PostgreSQL)         │  │
│  │   - primedata-postgres           │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Compute Engine VM              │  │
│  │   ┌──────────────────────────┐   │  │
│  │   │  Docker Containers       │   │  │
│  │   │  - Qdrant (6333)         │   │  │
│  │   │  - Airflow (8080)        │   │  │
│  │   │  - Backend API (8000)    │   │  │
│  │   │  - Frontend (3000)        │   │  │
│  │   └──────────────────────────┘   │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Cloud Storage (GCS)            │  │
│  │   - primedata-raw                │  │
│  │   - primedata-processed         │  │
│  │   - primedata-exports            │  │
│  └──────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

#### **Prerequisites**

1. GCP account with billing enabled
2. GitHub repository with Actions enabled
3. Terraform >= 1.0 (for manual deployment)
4. GCP Cloud SDK installed

#### **Quick Start**

**1. Deploy Infrastructure (Terraform)**

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply (creates VM, firewall rules, service accounts)
terraform apply
```

**Outputs:**
- VM External IP
- Service Account Email
- Database Connection Name

**2. Configure GitHub Secrets**

Go to GitHub → Settings → Secrets and variables → Actions

Add these secrets:
- `VM_USERNAME` - Your VM username (e.g., `neelamvivaan23`)
- `VM_SSH_KEY` - Private SSH key for VM access

**3. Setup VM Environment**

SSH to the VM and create `.env.production`:

```bash
# SSH to VM
gcloud compute ssh primedata-beta --zone=us-central1-c

# Create environment file
sudo mkdir -p /opt/primedata
sudo chown $USER:$USER /opt/primedata
cd /opt/primedata

# Create .env.production (see template below)
nano .env.production
```

**Environment File Template:**

```bash
# Database Configuration
# ⚠️ WARNING: Replace YOUR_PASSWORD and YOUR_DB_IP with your actual values!
DATABASE_URL=postgresql://primedata:YOUR_PASSWORD@YOUR_DB_IP:5432/primedata
AIRFLOW_DB_URL=postgresql://primedata:YOUR_PASSWORD@YOUR_DB_IP:5432/airflow

# Cloud Storage (GCS) Configuration
MINIO_HOST=storage.googleapis.com
MINIO_ACCESS_KEY=<YOUR_GCS_SERVICE_ACCOUNT_KEY>
MINIO_SECRET_KEY=<YOUR_GCS_SERVICE_ACCOUNT_SECRET>
MINIO_SECURE=true
GOOGLE_APPLICATION_CREDENTIALS=/opt/primedata/gcp-sa-key.json

# Qdrant Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334

# Application URLs (replace <VM_IP> with actual IP)
FRONTEND_URL=http://<VM_IP>:3000
NEXT_PUBLIC_API_URL=http://<VM_IP>:8000
NEXTAUTH_URL=http://<VM_IP>:3000
CORS_ORIGINS=["http://<VM_IP>:3000"]

# Security (generate these)
JWT_SECRET_KEY=<generate-64-char-secret>
NEXTAUTH_SECRET=<generate-64-char-secret>
AIRFLOW_PASSWORD=<generate-password>
AIRFLOW_SECRET_KEY=<generate-secret>

# Airflow Configuration
AIRFLOW_USERNAME=admin
AIRFLOW_SECRET_KEY=<generate-secret>

# Disable Auth for Beta (optional)
DISABLE_AUTH=false
```

**Generate Secrets:**
```bash
openssl rand -hex 32  # For JWT_SECRET_KEY and NEXTAUTH_SECRET
openssl rand -base64 16  # For AIRFLOW_PASSWORD
openssl rand -hex 32  # For AIRFLOW_SECRET_KEY
```

**4. Deploy Application**

**Option A: Via GitHub Actions (Recommended)**
- Push code to `db-fixes` branch
- GitHub Actions will automatically deploy
- Monitor in Actions tab

**Option B: Manual Deployment**
```bash
# Use deployment script
./infra/scripts/deploy.sh

# Or manually
gcloud compute ssh primedata-beta --zone=us-central1-c
cd /opt/primedata
docker-compose -f infra/docker-compose.prod.yml up -d --build
```

#### **Accessing Services**

After deployment, services will be available at:

- **Frontend**: http://VM_IP:3000
- **Backend API**: http://VM_IP:8000
- **API Docs**: http://VM_IP:8000/docs
- **Airflow**: http://VM_IP:8080
- **Qdrant Dashboard**: http://VM_IP:6333/dashboard

#### **Database Migrations**

Migrations run automatically on deployment. To run manually:

```bash
docker-compose -f infra/docker-compose.prod.yml exec backend alembic upgrade head
```

#### **Monitoring**

**Check Service Status:**
```bash
# SSH to VM
gcloud compute ssh primedata-beta --zone=us-central1-c

# Check containers
docker ps

# Check logs
docker-compose -f infra/docker-compose.prod.yml logs -f
```

**Health Checks:**
```bash
# Backend
curl http://VM_IP:8000/health

# Airflow
curl http://VM_IP:8080/health
```

#### **Updating Application**

**Via GitHub Actions:**
1. Make changes
2. Commit and push to `db-fixes` branch
3. GitHub Actions will automatically deploy

**Manual Update:**
```bash
# SSH to VM
gcloud compute ssh primedata-beta --zone=us-central1-c

# Pull latest code
cd /opt/primedata
git pull origin db-fixes

# Rebuild and restart
docker-compose -f infra/docker-compose.prod.yml up -d --build
```

#### **Scaling**

**Increase VM Size:**
```bash
# Stop VM
gcloud compute instances stop primedata-beta --zone=us-central1-c

# Change machine type
gcloud compute instances set-machine-type primedata-beta \
  --zone=us-central1-c \
  --machine-type=e2-standard-4

# Start VM
gcloud compute instances start primedata-beta --zone=us-central1-c
```

#### **Cleanup**

To destroy all infrastructure:

```bash
cd infra/terraform
terraform destroy
```

**Warning**: This will delete everything!

#### **Qdrant Cloud Setup (Alternative)**

1. Create Qdrant Cloud account at https://cloud.qdrant.io/
2. Create a new cluster (free tier: 1GB storage, 1M vectors)
3. Update environment variables:
   ```env
   QDRANT_HOST=your-cluster-id.qdrant.tech
   QDRANT_API_KEY=your-api-key-here
   QDRANT_USE_SSL=true
   ```

### GitHub Actions CI/CD

AIRDops uses GitHub Actions for Continuous Integration (CI) and Continuous Deployment (CD) with Workload Identity Federation for secure GCP authentication.

#### **Workflows Overview**

1. **CI Pipeline (`ci.yml`)**:
   - Triggers on `pull_request` and `push` to `main` or `db-fixes` branches
   - Performs backend linting (flake8, black, isort)
   - Runs backend unit/integration tests (pytest)
   - Performs frontend linting (ESLint) and type checking (TypeScript)
   - Builds Docker images for testing

2. **Deploy Infrastructure (`deploy-infra.yml`)**:
   - Triggers on push to `main` or `db-fixes` when changes detected in `infra/terraform/**`
   - Supports `workflow_dispatch` for manual triggers with `plan`, `apply`, or `destroy` options
   - Uses Terraform to provision and manage GCP infrastructure
   - Authenticates to GCP using Workload Identity Federation

3. **Deploy Application (`deploy-app.yml`)**:
   - Triggers on push to `main` or `db-fixes` when changes detected in `backend/**`, `ui/**`, `infra/docker-compose.prod.yml`, or `infra/airflow/**`
   - Authenticates to GCP using Workload Identity Federation
   - Connects to the provisioned Compute Engine VM via SSH
   - Copies application code and Docker Compose files to the VM
   - Builds and starts Docker containers using conditional builds
   - Runs database migrations
   - Performs basic health checks

#### **GCP Authentication with Workload Identity Federation**

This setup uses [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation) for secure authentication from GitHub Actions to GCP, eliminating the need for long-lived service account keys.

**Configuration Details:**
- **Project ID**: `project-f3c8a334-a3f2-4f66-a06`
- **Project Number**: `890841479962`
- **Workload Identity Pool**: `github-pool`
- **OIDC Provider**: `github-provider`
- **Service Account**: `github-actions@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com`
- **Workload Identity Provider Path**: `projects/890841479962/locations/global/workloadIdentityPools/github-pool/providers/github-provider`

**Setup Steps (Run in GCP Cloud Shell):**

1. **Set your GCP Project ID:**
   ```bash
   gcloud config set project project-f3c8a334-a3f2-4f66-a06
   ```

2. **Create a Service Account for GitHub Actions:**
   ```bash
   gcloud iam service-accounts create github-actions \
     --display-name="GitHub Actions Service Account" \
     --description="Service account for GitHub Actions CI/CD"
   ```

3. **Grant Permissions to the Service Account:**
   ```bash
   PROJECT_ID="project-f3c8a334-a3f2-4f66-a06"
   GITHUB_SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

   gcloud projects add-iam-policy-binding ${PROJECT_ID} \
     --member="serviceAccount:${GITHUB_SA_EMAIL}" \
     --role="roles/owner" # Or more specific roles
   ```

4. **Create Workload Identity Pool:**
   ```bash
   gcloud iam workload-identity-pools create github-pool \
     --project=${PROJECT_ID} \
     --location="global" \
     --display-name="GitHub Actions Pool"
   ```

5. **Create Workload Identity Provider:**
   ```bash
   PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")

   gcloud iam workload-identity-pools providers create-oidc github-provider \
     --project=${PROJECT_ID} \
     --location="global" \
     --workload-identity-pool=github-pool \
     --display-name="GitHub Provider" \
     --attribute-mapping="google.subject=assertion.sub" \
     --attribute-condition="assertion.repository == 'neelam53yadav/aird'" \
     --issuer-uri="https://token.actions.githubusercontent.com"
   ```

6. **Allow GitHub Actions to Impersonate the Service Account:**
   ```bash
   PROVIDER_NAME="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"

   gcloud iam service-accounts add-iam-policy-binding ${GITHUB_SA_EMAIL} \
     --project=${PROJECT_ID} \
     --role="roles/iam.workloadIdentityUser" \
     --member="principalSet://iam.googleapis.com/${PROVIDER_NAME}/attribute.repository/neelam53yadav/aird"
   ```

**Fixing OIDC Provider (If Needed):**

If the OIDC provider wasn't created correctly, run this script:

```bash
# In Cloud Shell
chmod +x infra/scripts/fix-oidc-provider.sh
./infra/scripts/fix-oidc-provider.sh
```

**GitHub Repository Secrets:**

Configure the following secrets in your GitHub repository (Settings → Secrets and variables → Actions):

1. **VM_USERNAME**: Your username on the Compute Engine VM
   - Example: `neelamvivaan23`
   - How to get it: `echo $USER` in Cloud Shell

2. **VM_SSH_KEY**: The **private SSH key** that GitHub Actions will use to connect to the VM
   - Generate an SSH key pair:
     ```bash
     ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ~/.ssh/github_actions_deploy
     ```
   - Add public key to VM (after VM is created):
     ```bash
     gcloud compute instances add-metadata primedata-beta \
       --zone=us-central1-c \
       --metadata-from-file ssh-keys=~/.ssh/github_actions_deploy.pub
     ```
   - Copy private key content to GitHub secret:
     ```bash
     cat ~/.ssh/github_actions_deploy
     ```

**How It Works:**

1. **GitHub Actions** requests an OIDC token from GitHub
2. **Workload Identity Federation** validates the token
3. **GCP** grants temporary access to the service account
4. **No service account keys** are stored or needed!

**Benefits:**

✅ **More Secure**: No long-lived service account keys
✅ **Automatic**: No manual key rotation needed
✅ **Auditable**: Better tracking of who accessed what
✅ **Policy Compliant**: Works with organization policies that block key creation

**Verification:**

After setup, verify the configuration:

```bash
# Verify Workload Identity Pool
gcloud iam workload-identity-pools describe github-pool \
  --project=project-f3c8a334-a3f2-4f66-a06 \
  --location="global"

# Verify OIDC Provider
gcloud iam workload-identity-pools providers describe github-provider \
  --project=project-f3c8a334-a3f2-4f66-a06 \
  --location="global" \
  --workload-identity-pool=github-pool

# Check service account binding
gcloud iam service-accounts get-iam-policy \
  github-actions@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com
```

**Important: Fix Authentication Permission Error**

If you see the error `Permission 'iam.serviceAccounts.getAccessToken' denied`, grant the service account token creator role:

```bash
PROJECT_ID="project-f3c8a334-a3f2-4f66-a06"
GITHUB_SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant the service account token creator role
gcloud iam service-accounts add-iam-policy-binding ${GITHUB_SA_EMAIL} \
  --project=${PROJECT_ID} \
  --role="roles/iam.serviceAccountTokenCreator" \
  --member="serviceAccount:${GITHUB_SA_EMAIL}"
```

This allows the service account to create tokens for itself, which is required for Workload Identity Federation.

**If authentication still fails after adding the role:**

1. **Wait 5-10 minutes** - IAM changes can take time to propagate
2. **Verify the binding**:
   ```bash
   gcloud iam service-accounts get-iam-policy ${GITHUB_SA_EMAIL} \
     --project=${PROJECT_ID}
   ```
3. **Remove and re-add** the binding if needed:
   ```bash
   # Remove
   gcloud iam service-accounts remove-iam-policy-binding ${GITHUB_SA_EMAIL} \
     --project=${PROJECT_ID} \
     --role="roles/iam.serviceAccountTokenCreator" \
     --member="serviceAccount:${GITHUB_SA_EMAIL}"
   
   # Re-add
   gcloud iam service-accounts add-iam-policy-binding ${GITHUB_SA_EMAIL} \
     --project=${PROJECT_ID} \
     --role="roles/iam.serviceAccountTokenCreator" \
     --member="serviceAccount:${GITHUB_SA_EMAIL}"
   ```

#### **CI Workflow Optimizations**

**Lightweight CI Requirements:**

The CI workflow uses `backend/requirements-ci.txt` which excludes heavy ML dependencies:
- Excludes: `sentence-transformers` (requires PyTorch + CUDA ~3GB)
- Includes: Only what's needed for linting and basic testing
- Reduces installation size from ~3GB to ~200MB

**Frontend Build Fixes:**

- Removed conflicting `next.config.js` file (kept only `next.config.ts`)
- Dockerfile uses `COPY . .` to ensure all files are included
- Fixed module resolution for `@/lib/*` imports

### Conditional Builds

The deploy workflow intelligently detects which files changed and only rebuilds the Docker images for services that were actually modified. This significantly speeds up deployments when only unrelated files (like documentation) are changed.

#### **How It Works**

**1. File Change Detection**

The workflow detects changed files by comparing:
- For `push` events: Previous commit vs current commit
- For `workflow_dispatch`: Current HEAD vs `main` branch

**2. Service-Specific Change Detection**

**Backend** (`rebuild_backend=true` if):
- `backend/src/**` - Source code changes
- `backend/Dockerfile` - Dockerfile changes
- `backend/requirements*.txt` - Dependency changes
- `backend/alembic/**` - Migration changes

**Frontend** (`rebuild_frontend=true` if):
- `ui/app/**` - App directory changes
- `ui/lib/**` - Library changes
- `ui/components/**` - Component changes
- `ui/Dockerfile` - Dockerfile changes
- `ui/package.json` - Dependency changes
- `ui/next.config.ts` - Next.js config changes
- `ui/tsconfig.json` - TypeScript config changes

**Airflow** (`rebuild_airflow=true` if):
- `infra/airflow/**` - Any Airflow-related changes

**All Services** (if `docker-compose.prod.yml` changed):
- If `infra/docker-compose.prod.yml` changes, all services are rebuilt

**3. Build Skipping**

The workflow skips building entirely (`skip_build=true`) if:
- Only unrelated files changed (not in `backend/`, `ui/`, or `infra/`)
- Examples: `README.md`, `.gitignore`, documentation files

**4. Selective Building**

On the VM, the workflow:
1. Builds only services that changed
2. Starts all services (using newly built images for changed services)
3. Skips build entirely if `skip_build=true`

#### **Examples**

**Example 1: Backend Code Change**
```
Changed: backend/src/primedata/api/products.py
Result:
  ✅ rebuild_backend=true
  ❌ rebuild_frontend=false
  ❌ rebuild_airflow=false
  ❌ skip_build=false
Action: Only backend image is rebuilt
```

**Example 2: Only Documentation Changed**
```
Changed: README.md, docs/guide.md
Result:
  ❌ rebuild_backend=false
  ❌ rebuild_frontend=false
  ❌ rebuild_airflow=false
  ✅ skip_build=true
Action: No images rebuilt, just restart containers
```

**Example 3: Docker Compose Config Changed**
```
Changed: infra/docker-compose.prod.yml
Result:
  ✅ rebuild_backend=true
  ✅ rebuild_frontend=true
  ✅ rebuild_airflow=true
  ❌ skip_build=false
Action: All services rebuilt (config might affect all)
```

**Example 4: Frontend and Backend Changed**
```
Changed: ui/app/page.tsx, backend/src/api.py
Result:
  ✅ rebuild_backend=true
  ✅ rebuild_frontend=true
  ❌ rebuild_airflow=false
  ❌ skip_build=false
Action: Backend and frontend rebuilt, Airflow skipped
```

#### **Benefits**

1. **Faster Deployments**: Only rebuilds what changed
2. **Resource Efficient**: Saves CPU/memory on VM
3. **Time Savings**: Can skip build entirely for docs-only changes
4. **Still Uses Docker Caching**: Unchanged layers are reused

#### **Docker Build Behavior**

**CI Workflow (`build-images` job)**:
- Builds Docker images using Docker Buildx
- Uses GitHub Actions cache (`cache-from: type=gha`, `cache-to: type=gha,mode=max`)
- Does NOT push images - only builds for testing
- Uses Docker layer caching - reuses layers if Dockerfile/source files unchanged

**Deploy Workflow**:
- Uses conditional builds based on file changes
- Only rebuilds affected services
- Uses Docker layer caching for unchanged layers
- Skips build entirely if only unrelated files changed

### Idempotency

All infrastructure components are designed to be **idempotent**, meaning running the same operation multiple times produces the same result without creating duplicates or errors.

#### **Terraform Idempotency**

Terraform is **inherently idempotent**:
1. **State Management**: Terraform tracks all resources in state
2. **Comparison**: Compares desired state (code) with actual state
3. **Skip Creation**: If resource exists and matches, no action taken
4. **Update Only**: Only updates resources that differ
5. **No Duplicates**: Resources identified by unique names/IDs

**Resource Naming Strategy:**
- VM: `primedata-beta`
- Service Account: `primedata-compute-sa-beta`
- Firewall Rules: `primedata-allow-http-beta`

**Handling Existing Resources:**

**Scenario 1: Resource Already in State**
- ✅ Terraform detects it exists
- ✅ Skips creation
- ✅ Updates if configuration changed

**Scenario 2: Resource Exists but Not in State**
- ⚠️ Terraform will try to create
- ⚠️ GCP will return "already exists" error
- ✅ **Solution**: Import resource into state

```bash
# Import existing VM
terraform import google_compute_instance.primedata_vm \
  projects/project-f3c8a334-a3f2-4f66-a06/zones/us-central1-c/instances/primedata-beta
```

**Lifecycle Rules:**
```hcl
lifecycle {
  create_before_destroy = true  # Prevents downtime
  ignore_changes = [metadata_startup_script]  # Ignores changes after creation
  prevent_destroy = false  # Allows deletion if needed
}
```

#### **Docker Compose Idempotency**

Docker Compose commands are idempotent:

- **`up -d`**: Starts stopped containers, no-op if containers already running, creates containers if they don't exist
- **`pull`**: Updates images if newer version available, no-op if images are current
- **`build`**: Rebuilds images if Dockerfile changed, uses cache if unchanged
- **`exec`**: Runs command in existing container, fails gracefully if container doesn't exist

**Network Management:**
```bash
docker network create primedata-network 2>/dev/null || echo "Network already exists"
```

This command:
- ✅ Creates network if it doesn't exist
- ✅ Skips silently if it exists
- ✅ No errors or duplicates

#### **Database Migrations**

Alembic migrations are idempotent:
1. **Migration Tracking**: Tracks applied migrations in database
2. **Skip Applied**: Automatically skips already applied migrations
3. **Safe to Re-run**: Can run `alembic upgrade head` multiple times safely

```bash
# Safe to run multiple times
alembic upgrade head
# First run: Applies pending migrations
# Second run: "No migrations to apply"
```

#### **Testing Idempotency**

**Test Terraform:**
```bash
cd infra/terraform
terraform apply  # First run - creates resources
terraform apply  # Second run - should show "No changes"
```

**Test Docker Compose:**
```bash
docker-compose -f infra/docker-compose.prod.yml up -d
docker-compose -f infra/docker-compose.prod.yml up -d  # Second run - no changes
```

**Test Migrations:**
```bash
alembic upgrade head  # First run - applies migrations
alembic upgrade head  # Second run - "No migrations to apply"
```

#### **Benefits**

✅ **No Duplicates**: Resources won't be created twice
✅ **Safe Re-runs**: Can run deployments multiple times
✅ **Error Prevention**: Handles existing resources gracefully
✅ **State Management**: Terraform tracks everything
✅ **Rollback Safe**: Can destroy and recreate safely

### Production Considerations

#### **Security**

- Use strong JWT secrets
- Enable HTTPS/TLS
- Configure proper CORS settings
- Implement rate limiting
- Use environment-specific secrets

#### **Performance**

- Configure connection pooling
- Use CDN for static assets
- Implement caching strategies
- Monitor resource usage
- Scale services horizontally

#### **Monitoring**

- Set up health checks
- Configure logging aggregation
- Implement alerting
- Monitor performance metrics
- Track error rates

#### **Backup & Recovery**

- Regular database backups
- S3/MinIO backup strategy
- Disaster recovery plan
- Test recovery procedures

#### **GitHub Actions Next Steps**

**Step 1: Commit and Push All Changes**

```bash
# Check what files have changed
git status

# Add all changes
git add .

# Commit with descriptive message
git commit -m "Fix GitHub Actions: CI optimizations, conditional builds, and frontend fixes"

# Push to trigger workflows
git push origin db-fixes
```

**Step 2: Verify GitHub Secrets Are Configured**

Go to: https://github.com/neelam53yadav/aird/settings/secrets/actions

**Required Secrets:**
- ✅ `VM_USERNAME` - Your VM username (e.g., `neelamvivaan23`)
- ✅ `VM_SSH_KEY` - Private SSH key for VM access

**Step 3: Monitor CI Workflow (First Run)**

After pushing, check: https://github.com/neelam53yadav/aird/actions

**Expected Results:**
- ✅ `lint-backend` - Should pass (using lightweight requirements)
- ✅ `test-backend` - Should pass or skip if no tests
- ✅ `lint-frontend` - Should pass
- ✅ `build-images` - Should successfully build all Docker images

**Step 4: Deploy Infrastructure (If Not Done Yet)**

**Option A: Automatic (if `infra/terraform/**` changed)**
- Workflow will trigger automatically
- Monitor: https://github.com/neelam53yadav/aird/actions/workflows/deploy-infra.yml

**Option B: Manual Trigger**
1. Go to: https://github.com/neelam53yadav/aird/actions/workflows/deploy-infra.yml
2. Click "Run workflow"
3. Choose branch: `db-fixes`
4. Choose action: `apply`
5. Click "Run workflow"

**Step 5: Setup VM (After Infrastructure Deployment)**

**5.1 Get VM IP:**
```bash
gcloud compute instances describe primedata-beta \
  --zone=us-central1-c \
  --format="value(networkInterfaces[0].accessConfig[0].natIP)"
```

**5.2 Add SSH Key to VM:**
```bash
# Generate key if you haven't already
ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github_actions -N ""

# Add public key to VM
gcloud compute instances add-metadata primedata-beta \
  --zone=us-central1-c \
  --metadata-from-file ssh-keys=~/.ssh/github_actions.pub

# Verify the private key matches what's in GitHub secrets
cat ~/.ssh/github_actions  # This should match VM_SSH_KEY secret
```

**5.3 Create Environment File on VM:**
- SSH to VM: `gcloud compute ssh primedata-beta --zone=us-central1-c`
- Create `/opt/primedata/.env.production` (see template in GCP Cloud Deployment section)

**Step 6: Trigger Application Deployment**

**Option A: Automatic (if app files changed)**
- Push any change to `backend/**`, `ui/**`, or `infra/docker-compose.prod.yml`
- Workflow will trigger automatically

**Option B: Manual Trigger**
1. Go to: https://github.com/neelam53yadav/aird/actions/workflows/deploy-app.yml
2. Click "Run workflow"
3. Choose branch: `db-fixes`
4. Click "Run workflow"

**Step 7: Verify Deployment**

**Check Services:**
```bash
# SSH to VM
gcloud compute ssh primedata-beta --zone=us-central1-c

# Check container status
docker ps

# Check logs if needed
docker-compose -f infra/docker-compose.prod.yml logs backend
docker-compose -f infra/docker-compose.prod.yml logs frontend
```

**Test Endpoints:**
```bash
# Get VM IP
VM_IP=$(gcloud compute instances describe primedata-beta \
  --zone=us-central1-c \
  --format="value(networkInterfaces[0].accessConfig[0].natIP)")

# Test health endpoints
curl http://$VM_IP:8000/health  # Backend
curl http://$VM_IP:8080/health  # Airflow
curl http://$VM_IP:6333/health  # Qdrant
```

#### **Troubleshooting GitHub Actions**

**CI Workflow Fails:**

**Issue: Disk space error**
- ✅ Fixed with `requirements-ci.txt`
- If still fails, check if PyTorch is being installed

**Issue: Frontend build fails**
- ✅ Fixed by removing `next.config.js`
- If still fails, check for TypeScript errors

**Issue: Module not found**
- Check if `ui/lib/` files exist
- Verify `tsconfig.json` paths configuration

**Deploy Workflow Fails:**

**Issue: Cannot connect to VM**
- Verify `VM_SSH_KEY` secret is correct
- Check if SSH key is added to VM metadata
- Test SSH connection manually

**Issue: File change detection fails**
- Check git history (might be first commit)
- Verify `git fetch` works in workflow

**Issue: Docker build fails on VM**
- Check if Docker is installed on VM
- Verify docker-compose is available
- Check VM disk space

**Issue: Services don't start**
- Check `.env.production` file exists
- Verify environment variables are correct
- Check Docker logs: `docker-compose logs`

**Infrastructure Deployment Fails:**

**Issue: Authentication error**
- Verify Workload Identity Federation is set up
- Check service account permissions
- Verify project ID is correct

**Issue: Terraform state error**
- Check if GCS bucket `primedata-terraform-state` exists
- Verify bucket permissions

#### **Success Indicators**

You'll know everything is working when:

1. ✅ CI workflow completes successfully (green checkmarks)
2. ✅ Infrastructure deployment shows "No changes" or creates resources
3. ✅ Application deployment shows conditional build plan
4. ✅ Services are running on VM (`docker ps` shows all containers)
5. ✅ Health checks return 200 OK
6. ✅ You can access frontend/backend/Airflow in browser

---

## Conclusion

AIRDops provides a comprehensive platform for preparing data for AI applications. By following this guide, you can:

- Set up and configure the system
- Optimize data quality for maximum AI efficiency
- Understand and use all core features
- Troubleshoot common issues
- Achieve excellent data quality (>85%) for 4x efficiency gains
- Deploy to production environments

For additional support, check the API documentation at http://localhost:8000/docs or review the troubleshooting section.

---

**AIRDops** - Transforming data into AI-ready insights with enterprise-grade quality and governance.
