# PrimeData Architecture

## Overview

PrimeData is a modern data platform designed for enterprise AI workflows. It provides a comprehensive solution for data ingestion, processing, vectorization, and ML operations.

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js UI    │    │   FastAPI API   │    │   PostgreSQL    │
│   (Port 3000)   │◄──►│   (Port 8000)   │◄──►│   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Qdrant      │    │     MinIO       │    │     MLflow      │
│   (Port 6333)   │    │  (Port 9000)    │    │   (Port 5000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │    Airflow      │
                       │   (Port 8080)   │
                       └─────────────────┘
```

## Components

### Frontend (UI)
- **Technology**: Next.js 14+ with App Router
- **Styling**: Tailwind CSS + shadcn/ui components
- **Authentication**: NextAuth.js ready
- **Features**: Enterprise-grade design with neutral grays/blues palette

### Backend (API)
- **Technology**: FastAPI with Python 3.11
- **Database**: SQLAlchemy + Alembic for migrations
- **Authentication**: JWT with RS256 keys
- **Validation**: Pydantic v1 for data validation
- **Server**: Uvicorn ASGI server

### Data Storage

#### PostgreSQL
- Primary relational database
- Stores user data, configurations, and metadata
- **Enterprise Data Quality Rules**: ACID-compliant rule storage with audit trails
- **Quality Violations**: Comprehensive violation tracking and management
- **Rule Versioning**: Complete rule lifecycle management
- Connection pooling and health checks

#### Qdrant
- Vector database for embeddings
- Similarity search and retrieval
- Persistent storage with health checks

#### MinIO
- S3-compatible object storage
- Buckets: primedata-raw, primedata-clean, primedata-chunk, primedata-embed, primedata-export, primedata-config
- Development environment (S3 in production)

### ML Operations

#### MLflow
- Experiment tracking and model management
- PostgreSQL backend store
- MinIO artifact store
- Model versioning and deployment

#### Airflow
- Data pipeline orchestration
- LocalExecutor for development
- DAG management and scheduling
- Integration with all services

## Data Flow

1. **Ingestion**: Data connectors feed into MinIO raw bucket
2. **Quality Validation**: Enterprise data quality rules validate data integrity
3. **Processing**: Airflow orchestrates cleaning and chunking
4. **Embedding**: Vectorization and storage in Qdrant
5. **ML Operations**: MLflow tracks experiments and models
6. **Quality Monitoring**: Continuous quality assessment and violation tracking
7. **Export**: Processed data available for AI applications

## Enterprise Data Quality Management

### **Rule Engine Architecture**
- **7 Rule Types**: Required fields, duplicate rate, chunk coverage, file extensions, freshness, file size, content length
- **Database-First**: ACID-compliant rule storage in PostgreSQL
- **Audit Trail**: Complete change history with user attribution
- **Version Control**: Rule versioning and lifecycle management
- **Real-time Monitoring**: Continuous quality assessment

### **Quality Violations System**
- **Violation Detection**: Automated rule evaluation and violation identification
- **Severity Levels**: Error, warning, and info classifications
- **Status Tracking**: Pending, acknowledged, resolved, ignored states
- **Impact Analysis**: Business impact assessment and prioritization
- **Reporting**: Comprehensive violation reporting and analytics

### **Compliance & Governance**
- **Rule Ownership**: Clear ownership and responsibility assignment
- **Change Management**: Formal rule change processes
- **Audit Logging**: Complete audit trail for compliance
- **Role-Based Access**: Secure rule management and access control

## Security

- JWT-based authentication with RS256 keys
- CORS configuration for frontend access
- Environment-based configuration
- Health checks for all services

## Development

- Docker Compose for local development
- Environment templates for configuration
- Structured logging with loguru
- Health endpoints for monitoring

## Deployment

- Containerized services
- Environment-specific configurations
- Health checks and monitoring
- Scalable architecture for production
