# PrimeData

**AI-ready data from any source. Ingest, clean, chunk, embed & index. Test and export with confidence.**

PrimeData is a comprehensive enterprise data platform designed for AI workflows. It provides end-to-end data processing, from ingestion to vectorization, with enterprise-grade data quality management, billing & gating, team collaboration, and advanced analytics.

## 🚀 Features

### **🏢 Enterprise Data Quality Management**
- **7 Rule Types**: Required fields, duplicate detection, chunk coverage, bad extensions, file size limits, content validation, and custom rules
- **Real-time Monitoring**: Continuous quality assessment with violation tracking
- **Audit Trail**: Complete history of rule changes and violations
- **Compliance Reporting**: Enterprise-grade governance and compliance features
- **Database-First Architecture**: ACID-compliant rule storage with concurrent access support

### **💰 Billing & Gating with Stripe**
- **Subscription Plans**: Free, Pro, and Enterprise tiers with usage limits
- **Usage Tracking**: Monitor products, data sources, pipeline runs, and vector storage
- **Stripe Integration**: Secure payment processing with customer portal
- **Plan Limits**: Enforced limits on products, data sources, and pipeline runs
- **Webhook Support**: Real-time subscription updates

### **👥 Team Management**
- **Role-Based Access**: Owner, Admin, Editor, and Viewer roles
- **Team Invitations**: Invite members with specific roles
- **Workspace Management**: Multi-workspace support with proper access control
- **User Profiles**: Comprehensive user profile management with Google OAuth

### **📊 Analytics & Monitoring**
- **Real-time Metrics**: Pipeline performance, success rates, processing times
- **Data Quality Scores**: Continuous quality assessment and reporting
- **Monthly Trends**: Historical performance analysis
- **Activity Tracking**: Recent pipeline runs and system events

### **🔧 Advanced Chunking Configuration**
- **Hybrid Mode**: Auto and manual chunking with AI-powered optimization
- **Content Analysis**: Detects content types (legal, code, documentation) and suggests optimal settings
- **Smart Defaults**: Intelligent recommendations based on content characteristics
- **Model Optimization**: AI-optimized chunking parameters

### **🧪 MLflow Integration**
- **Experiment Tracking**: Complete pipeline run tracking with parameters, metrics, and artifacts
- **Performance Monitoring**: Track chunking, embedding, and indexing performance over time
- **Artifact Management**: Store sample chunks, provenance data, and model artifacts
- **UI Integration**: Pipeline metrics dashboard with direct MLflow access

### **📤 Export & Data Management**
- **Export Bundles**: Create downloadable ZIP archives of processed data
- **Data Provenance**: Complete lineage tracking from source to vector
- **Version Management**: Track different versions of processed data
- **Presigned URLs**: Secure, time-limited download links

### **🔌 Data Connectors**
- **Web Scraping**: Extract data from websites and online sources
- **Folder Monitoring**: Process files from local and remote directories
- **Database Connectors**: Connect to various database systems
- **API Integrations**: RESTful API data ingestion

### **🏗️ Enterprise Architecture**
- **Microservices**: FastAPI backend with Next.js frontend
- **Vector Storage**: Qdrant for embeddings and similarity search
- **Object Storage**: MinIO for scalable file storage
- **Orchestration**: Airflow-powered data pipelines
- **Database**: PostgreSQL with ACID compliance
- **Authentication**: JWT-based security with Google OAuth

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker & Docker Compose**
- **Git**

### Setup

#### **Option 1: Automated Setup (Recommended)**

1. **Clone and navigate to the project:**
   ```cmd
   git clone <repository-url>
   cd PrimeData
   ```

2. **Run the complete setup script:**
   ```cmd
   setup_mlflow.bat
   ```
   This will:
   - Activate the virtual environment
   - Install MLflow and all dependencies
   - Test the MLflow integration
   - Provide next steps

#### **Option 2: Manual Setup**

1. **Create virtual environment and install dependencies:**
   ```cmd
   cd PrimeData
   activate_venv.bat
   pip install -r backend\requirements.txt
   install_mlflow.bat
   ```

2. **Start all services:**
   ```cmd
   docker-compose -f infra\docker-compose.yml up -d
   ```

3. **Start MLflow server:**
   ```cmd
   start_mlflow_server.bat
   ```

4. **Start the backend API:**
   ```cmd
   start_backend.bat
   ```

5. **Start the UI:**
   ```cmd
   cd ui
   npm install
   npm run dev
   ```

### **Database Setup**

1. **Run database migrations:**
   ```cmd
   cd backend
   activate_venv.bat
   alembic upgrade head
   ```

### **Service URLs**

- **PrimeData UI**: http://localhost:3000
- **PrimeData API**: http://localhost:8000/health
- **MLflow UI**: http://localhost:5000
- **Airflow UI**: http://localhost:8080
- **MinIO Console**: http://localhost:9001
- **Qdrant Dashboard**: http://localhost:6333

### **Default Credentials**

- **Airflow**: admin / admin
- **MinIO**: minioadmin / minioadmin123
- **PostgreSQL**: primedata / primedata123

## 📁 Project Structure

```
PrimeData/
├── backend/                    # FastAPI backend
│   ├── src/primedata/         # Python package
│   │   ├── api/               # API endpoints
│   │   │   ├── auth.py        # Authentication & user management
│   │   │   ├── products.py    # Product management
│   │   │   ├── datasources.py # Data source connectors
│   │   │   ├── pipeline.py    # Pipeline orchestration
│   │   │   ├── data_quality.py # Data quality rules
│   │   │   ├── billing.py     # Stripe billing integration
│   │   │   ├── analytics.py   # Analytics & metrics
│   │   │   ├── exports.py     # Export bundle management
│   │   │   └── ai_readiness.py # AI readiness assessment
│   │   ├── core/              # Core functionality
│   │   ├── db/                # Database models and connection
│   │   ├── indexing/          # Embedding and vector operations
│   │   ├── connectors/        # Data source connectors
│   │   └── analysis/          # Content analysis and chunking
│   ├── alembic/               # Database migrations
│   └── requirements.txt       # Python dependencies
├── ui/                        # Next.js frontend
│   ├── app/                   # App Router pages
│   │   ├── app/products/      # Product management
│   │   ├── app/datasources/   # Data source management
│   │   ├── app/analytics/     # Analytics dashboard
│   │   ├── app/billing/       # Billing & subscription management
│   │   ├── app/team/          # Team management
│   │   ├── app/settings/      # User settings
│   │   └── api/               # API routes
│   ├── components/            # React components
│   └── lib/                   # Utilities and API client
├── infra/                     # Infrastructure
│   ├── docker-compose.yml     # Service definitions
│   ├── airflow/               # Airflow DAGs and configuration
│   ├── env/                   # Environment templates
│   └── init/                  # Initialization scripts
├── docs/                      # Documentation
│   ├── architecture.md        # System architecture
│   ├── data-quality.md        # Data quality management
│   ├── pipeline-guide.md      # Pipeline setup and usage
│   ├── api-reference.md       # API documentation
│   └── troubleshooting/       # Troubleshooting guides
├── *.bat                      # Windows batch scripts for setup
└── MLFLOW_TROUBLESHOOTING.md  # MLflow troubleshooting guide
```

## 🎯 Usage Guide

### **Getting Started**

1. **Access the UI**: Go to http://localhost:3000
2. **Sign in with Google**: Use your Google account for authentication
3. **Create a Product**: Click "New Product" and fill in details
4. **Configure Chunking**: Choose between Auto or Manual mode
5. **Add Data Sources**: Connect web URLs, folders, or other data sources
6. **Set Data Quality Rules**: Configure validation rules for your data
7. **Run Pipeline**: Execute the data processing pipeline
8. **Monitor Results**: Check analytics dashboard and MLflow UI

### **Core Workflows**

#### **1. Product Management**
- Create and manage data products
- Configure chunking strategies (auto/manual)
- Set up data quality rules
- Monitor pipeline performance

#### **2. Data Source Management**
- Connect web sources, folders, databases
- Configure data extraction settings
- Monitor data freshness and quality
- Manage data source permissions

#### **3. Data Quality Management**
- Define validation rules (7 rule types)
- Monitor quality violations in real-time
- Generate compliance reports
- Track quality trends over time

#### **4. Team Collaboration**
- Invite team members with specific roles
- Manage workspace permissions
- Track team activity and usage
- Configure team-wide settings

#### **5. Billing & Usage**
- Monitor usage against plan limits
- Upgrade/downgrade subscription plans
- Manage payment methods
- Track usage analytics

### **Advanced Features**

#### **Chunking Configuration**
- **Auto Mode**: AI analyzes content and optimizes parameters
- **Manual Mode**: Full control over chunk size, overlap, and strategy
- **Content Analysis**: Detects content types and suggests optimal settings
- **Model Optimization**: AI-powered parameter tuning

#### **MLflow Integration**
- **Experiment Tracking**: Complete pipeline run history
- **Performance Metrics**: Processing time, quality scores, success rates
- **Artifact Management**: Sample chunks, provenance data, model artifacts
- **A/B Testing**: Compare different configurations

#### **Export & Data Management**
- **Export Bundles**: Download processed data as ZIP archives
- **Data Provenance**: Complete lineage from source to vector
- **Version Control**: Track different versions of processed data
- **Secure Downloads**: Presigned URLs for data access

## 🛠️ Development

### **Batch Scripts Available**

- `setup_mlflow.bat` - Complete MLflow setup
- `activate_venv.bat` - Activate virtual environment
- `install_mlflow.bat` - Install MLflow dependencies
- `test_mlflow.bat` - Test MLflow integration
- `start_backend.bat` - Start FastAPI server
- `start_mlflow_server.bat` - Start MLflow tracking server
- `rebuild_airflow_with_mlflow.bat` - Rebuild Airflow with MLflow

### **API Documentation**

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### **Database Migrations**
```cmd
cd backend
activate_venv.bat
alembic upgrade head
```

## 📊 Monitoring & Observability

### **Pipeline Metrics**
- Chunking performance and quality
- Embedding generation speed
- Vector indexing efficiency
- Overall pipeline health and processing time
- Real-time metrics aggregation

### **Analytics Dashboard**
- Product performance overview
- Data quality trends
- Team activity monitoring
- Usage analytics and billing insights

### **MLflow Experiments**
- Historical performance trends
- Configuration impact analysis
- A/B testing capabilities
- Model performance tracking

## 🔧 Configuration

### **Environment Variables**

#### **Backend (.env)**
```env
# Database
DATABASE_URL=postgresql://primedata:primedata123@localhost:5432/primedata

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_BACKEND_STORE_URI=postgresql://primedata:primedata123@localhost:5432/primedata
MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://mlflow-artifacts

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123

# Qdrant
QDRANT_URL=http://localhost:6333

# Stripe (for billing)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...

# Frontend
FRONTEND_URL=http://localhost:3000
```

#### **Frontend (.env.local)**
```env
# NextAuth Configuration
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=http://localhost:3000

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Stripe
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...

# API
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📚 Documentation

### **Core Documentation**
- **[Architecture Guide](docs/architecture.md)** - System architecture and component overview
- **[Setup Guide](docs/setup-guide.md)** - Complete installation and configuration guide
- **[User Guide](docs/user-guide.md)** - Comprehensive user manual and best practices
- **[Features Overview](docs/features-overview.md)** - Complete feature overview and capabilities
- **[API Reference](docs/api-reference.md)** - Complete API documentation and examples
- **[Data Quality Management](docs/data-quality.md)** - Enterprise data quality rules and management
- **[Pipeline Guide](docs/pipeline-guide.md)** - Complete pipeline setup and usage
- **[AI Readiness](docs/ai-readiness.md)** - Data quality assessment and improvement

### **Troubleshooting & Support**
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Comprehensive troubleshooting for all issues
- **[FAQ](docs/faq.md)** - Frequently asked questions and answers
- **[MLflow Troubleshooting](MLFLOW_TROUBLESHOOTING.md)** - MLflow setup and common issues
- **[Pipeline Troubleshooting](docs/pipeline-troubleshooting.md)** - Airflow and pipeline issues
- **[Data Quality Troubleshooting](docs/data-quality-troubleshooting.md)** - Data quality rule problems

### **When to Use Which Documentation**

#### **Getting Started**
1. **First Time Setup**: Start with this README → Setup Guide → User Guide
2. **Understanding the System**: Architecture → Data Quality → AI Readiness
3. **Setting Up Pipelines**: Pipeline Guide → API Reference

#### **Development & Configuration**
1. **API Development**: API Reference → Architecture
2. **Data Quality Rules**: Data Quality → API Reference
3. **Pipeline Customization**: Pipeline Guide → Architecture
4. **Billing Integration**: API Reference → Architecture

#### **Troubleshooting**
1. **General Issues**: Troubleshooting Guide
2. **MLflow Issues**: MLflow Troubleshooting
3. **Pipeline Failures**: Pipeline Troubleshooting
4. **Data Quality Problems**: Data Quality Troubleshooting

#### **Enterprise Features**
1. **Data Quality Management**: Data Quality → API Reference
2. **Billing & Subscriptions**: API Reference → Architecture
3. **Team Management**: User Guide → API Reference
4. **Compliance & Governance**: Data Quality → Architecture

#### **User Experience**
1. **New Users**: User Guide → Setup Guide
2. **Advanced Users**: API Reference → Architecture
3. **Administrators**: User Guide → Troubleshooting Guide
4. **Developers**: API Reference → Pipeline Guide

## 🚀 What's New

### **Latest Features**
- ✅ **Enterprise Data Quality Management** - 7 rule types with real-time monitoring
- ✅ **Billing & Gating with Stripe** - Subscription plans with usage limits
- ✅ **Team Management** - Role-based access control and collaboration
- ✅ **Analytics Dashboard** - Real-time metrics and performance monitoring
- ✅ **Export Bundles** - Secure data export with provenance tracking
- ✅ **User Profile Management** - Comprehensive user settings and preferences
- ✅ **Database-First Architecture** - ACID-compliant data quality rules
- ✅ **Hybrid Chunking Configuration** - Auto and manual modes with AI optimization
- ✅ **MLflow Integration** - Complete experiment tracking with accurate metrics
- ✅ **Content Analysis** - AI-powered chunking optimization
- ✅ **Pipeline Metrics Dashboard** - Real-time performance monitoring

### **Upcoming Features**
- 🔄 Advanced content type detection
- 🔄 Custom embedding models
- 🔄 Pipeline scheduling and automation
- 🔄 Advanced analytics and reporting
- 🔄 Multi-workspace data sharing
- 🔄 Custom data quality rules

## 🆘 Support & Troubleshooting

### **Common Issues**

#### **Setup Issues**
- **Virtual Environment**: Ensure Python 3.11+ is installed
- **Docker Services**: Check all services are running with `docker-compose ps`
- **Database Connection**: Verify PostgreSQL is accessible
- **Port Conflicts**: Ensure ports 3000, 8000, 5000, 8080, 9000, 6333 are available

#### **Authentication Issues**
- **Google OAuth**: Verify client ID and secret are correct
- **JWT Tokens**: Check token expiration and refresh
- **Session Management**: Clear browser cache and cookies

#### **Pipeline Issues**
- **Airflow Connection**: Check Airflow UI at http://localhost:8080
- **MLflow Tracking**: Verify MLflow server is running
- **Data Quality Rules**: Check rule configuration and validation

### **Getting Help**

1. **Check Documentation**: Start with relevant troubleshooting guide
2. **Review Logs**: Check backend logs for error details
3. **Health Check**: Use http://localhost:8000/health for system status
4. **Service Status**: Verify all services are running and accessible

## 📄 License

Enterprise License - All Rights Reserved

---

**PrimeData** - Transforming data into AI-ready insights with enterprise-grade quality and governance.