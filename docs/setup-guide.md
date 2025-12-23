# PrimeData Setup Guide

This comprehensive setup guide will walk you through installing and configuring PrimeData on your local machine.

## 📋 Prerequisites

### **System Requirements**

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **RAM**: Minimum 8GB, Recommended 16GB+
- **Storage**: Minimum 10GB free space
- **Network**: Internet connection for downloading dependencies

### **Required Software**

#### **1. Python 3.11+**
```bash
# Check Python version
python --version
# Should show Python 3.11.x or higher

# If not installed, download from:
# https://www.python.org/downloads/
```

#### **2. Node.js 18+**
```bash
# Check Node.js version
node --version
# Should show v18.x.x or higher

# If not installed, download from:
# https://nodejs.org/
```

#### **3. Docker Desktop**
```bash
# Check Docker version
docker --version
docker-compose --version

# If not installed, download from:
# https://www.docker.com/products/docker-desktop
```

#### **4. Git**
```bash
# Check Git version
git --version

# If not installed, download from:
# https://git-scm.com/downloads
```

## 🚀 Installation Methods

### **Method 1: Automated Setup (Recommended for Windows)**

This method uses the provided batch scripts for easy setup.

#### **Step 1: Clone Repository**
```cmd
git clone <repository-url>
cd PrimeData
```

#### **Step 2: Run Automated Setup**
```cmd
# This will set up everything automatically
setup_mlflow.bat
```

The script will:
- Create and activate virtual environment
- Install all Python dependencies
- Install MLflow and test integration
- Provide next steps

#### **Step 3: Start Services**
```cmd
# Start all Docker services
docker-compose -f infra\docker-compose.yml up -d

# Start MLflow server
start_mlflow_server.bat

# Start backend API
start_backend.bat

# Start frontend (in new terminal)
cd ui
npm install
npm run dev
```

### **Method 2: Manual Setup**

This method gives you more control over the installation process.

#### **Step 1: Clone Repository**
```bash
git clone <repository-url>
cd PrimeData
```

#### **Step 2: Backend Setup**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Install MLflow
pip install mlflow

# Test MLflow installation
python -c "import mlflow; print('MLflow installed successfully')"
```

#### **Step 3: Frontend Setup**
```bash
# Navigate to UI directory
cd ui

# Install dependencies
npm install

# Verify installation
npm run build
```

#### **Step 4: Database Setup**
```bash
# Start PostgreSQL
docker-compose -f infra/docker-compose.yml up -d postgres

# Wait for PostgreSQL to be ready (30 seconds)
sleep 30

# Run database migrations
cd backend
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate  # macOS/Linux
alembic upgrade head
```

#### **Step 5: Start All Services**
```bash
# Start all services
docker-compose -f infra/docker-compose.yml up -d

# Start MLflow server
cd backend
.\venv\Scripts\Activate.ps1
mlflow server --backend-store-uri postgresql://primedata:primedata123@localhost:5432/primedata --default-artifact-root s3://mlflow-artifacts --host 0.0.0.0 --port 5000

# Start backend API (in new terminal)
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn src.primedata.api.app:app --reload --host 0.0.0.0 --port 8000

# Start frontend (in new terminal)
cd ui
npm run dev
```

## ⚙️ Configuration

### **Environment Variables**

#### **Backend Configuration (.env)**
Create `backend/.env` with the following content:

```env
# Database Configuration
DATABASE_URL=postgresql://primedata:primedata123@localhost:5432/primedata

# MLflow Configuration
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_BACKEND_STORE_URI=postgresql://primedata:primedata123@localhost:5432/primedata
MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://mlflow-artifacts

# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_SECURE=false

# Qdrant Configuration
QDRANT_URL=http://localhost:6333

# Stripe Configuration (for billing features)
STRIPE_SECRET_KEY=sk_test_51234567890abcdefghijklmnopqrstuvwxyz
STRIPE_WEBHOOK_SECRET=whsec_1234567890abcdefghijklmnopqrstuvwxyz
STRIPE_PRO_PRICE_ID=price_1234567890
STRIPE_ENTERPRISE_PRICE_ID=price_0987654321

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

#### **Frontend Configuration (.env.local)**
Create `ui/.env.local` with the following content:

```env
# NextAuth Configuration
NEXTAUTH_SECRET=zAFv6-Z8iJJ1wla4U0-tS8UsV_v2f5u0QvTNXJwJIJZhR6yRpAH0DRGBiG5Jn6yY
NEXTAUTH_URL=http://localhost:3000

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here

# Stripe Configuration
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_51234567890abcdefghijklmnopqrstuvwxyz

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Email Auth (optional)
NEXT_PUBLIC_ENABLE_EMAIL_AUTH=false
```

### **Google OAuth Setup**

#### **Step 1: Create Google Cloud Project**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API

#### **Step 2: Create OAuth 2.0 Credentials**
1. Go to "Credentials" in the API & Services section
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Choose "Web application"
4. Add authorized redirect URIs:
   - `http://localhost:3000/api/auth/callback/google`
5. Copy Client ID and Client Secret

#### **Step 3: Update Environment Variables**
Update your `ui/.env.local` with the Google OAuth credentials:
```env
GOOGLE_CLIENT_ID=your-actual-google-client-id
GOOGLE_CLIENT_SECRET=your-actual-google-client-secret
```

### **Stripe Setup (Optional)**

#### **Step 1: Create Stripe Account**
1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Create account or sign in
3. Get your API keys from the dashboard

#### **Step 2: Create Products and Prices**
1. Go to Products in Stripe Dashboard
2. Create products for Pro and Enterprise plans
3. Create prices for each product
4. Copy the price IDs

#### **Step 3: Update Environment Variables**
Update your `backend/.env` with Stripe credentials:
```env
STRIPE_SECRET_KEY=sk_test_your_actual_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_actual_webhook_secret
STRIPE_PRO_PRICE_ID=price_your_actual_pro_price_id
STRIPE_ENTERPRISE_PRICE_ID=price_your_actual_enterprise_price_id
```

## 🔧 Service Configuration

### **Docker Services**

The system uses the following Docker services:

#### **PostgreSQL Database**
- **Port**: 5432
- **Database**: primedata
- **Username**: primedata
- **Password**: primedata123

#### **MinIO Object Storage**
- **Port**: 9000 (API), 9001 (Console)
- **Access Key**: minioadmin
- **Secret Key**: minioadmin123

#### **Qdrant Vector Database**
- **Port**: 6333 (API), 6334 (Dashboard)
- **No authentication required for local setup**

#### **Airflow Orchestration**
- **Port**: 8080
- **Username**: admin
- **Password**: admin

### **Service URLs**

After setup, the following services will be available:

- **PrimeData UI**: http://localhost:3000
- **PrimeData API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MLflow UI**: http://localhost:5000
- **Airflow UI**: http://localhost:8080
- **MinIO Console**: http://localhost:9001
- **Qdrant Dashboard**: http://localhost:6333

## 🧪 Verification

### **Health Check**

#### **Step 1: Check All Services**
```bash
# Check Docker services
docker-compose -f infra/docker-compose.yml ps

# Check API health
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "PrimeData",
  "database": {"status": "healthy"},
  "qdrant": {"status": "healthy"},
  "minio": {"status": "healthy"},
  "mlflow": {"status": "healthy"},
  "airflow": {"status": "healthy"}
}
```

#### **Step 2: Test Frontend**
1. Open http://localhost:3000
2. You should see the PrimeData landing page
3. Click "Sign in with Google" to test authentication

#### **Step 3: Test Backend API**
1. Open http://localhost:8000/docs
2. You should see the Swagger UI
3. Test the `/health` endpoint

#### **Step 4: Test MLflow**
1. Open http://localhost:5000
2. You should see the MLflow UI
3. Check that experiments can be created

## 🐛 Troubleshooting

### **Common Issues**

#### **Port Conflicts**
```bash
# Check what's using the ports
netstat -ano | findstr :3000
netstat -ano | findstr :8000
netstat -ano | findstr :5000

# Kill processes if needed
taskkill /PID <process_id> /F
```

#### **Docker Issues**
```bash
# Check Docker status
docker --version
docker-compose --version

# Restart Docker Desktop if needed
# Check Docker Desktop is running
```

#### **Database Connection Issues**
```bash
# Check PostgreSQL is running
docker-compose -f infra/docker-compose.yml ps postgres

# Check database logs
docker-compose -f infra/docker-compose.yml logs postgres
```

#### **Python Environment Issues**
```bash
# Check Python version
python --version

# Check virtual environment
.\venv\Scripts\Activate.ps1
python --version

# Reinstall dependencies if needed
pip install -r backend/requirements.txt
```

### **Reset Everything**

If you encounter persistent issues, you can reset everything:

```bash
# Stop all services
docker-compose -f infra/docker-compose.yml down

# Remove all containers and volumes
docker-compose -f infra/docker-compose.yml down -v

# Remove virtual environment
rmdir /s venv

# Start fresh
setup_mlflow.bat
```

## 📚 Next Steps

### **After Successful Setup**

1. **Read the Documentation**:
   - [Architecture Guide](architecture.md)
   - [Data Quality Management](data-quality.md)
   - [Pipeline Guide](pipeline-guide.md)
   - [API Reference](api-reference.md)

2. **Create Your First Product**:
   - Go to http://localhost:3000
   - Sign in with Google
   - Create a new product
   - Add data sources
   - Configure data quality rules
   - Run the pipeline

3. **Explore Features**:
   - Analytics dashboard
   - Team management
   - Billing & subscriptions
   - Export functionality

### **Development Workflow**

1. **Backend Development**:
   - Make changes to Python code
   - Test with FastAPI docs
   - Run database migrations if needed

2. **Frontend Development**:
   - Make changes to React components
   - Test in browser
   - Check for TypeScript errors

3. **Database Changes**:
   - Create new migration: `alembic revision --autogenerate -m "description"`
   - Apply migration: `alembic upgrade head`

## 🆘 Getting Help

### **If You're Stuck**

1. **Check the Troubleshooting Guide**: [troubleshooting.md](troubleshooting.md)
2. **Verify Prerequisites**: Ensure all required software is installed
3. **Check Logs**: Look at Docker logs and application logs
4. **Health Check**: Use the `/health` endpoint to verify services
5. **Reset and Retry**: Sometimes a clean start helps

### **Useful Commands**

```bash
# Check service status
docker-compose -f infra/docker-compose.yml ps

# View logs
docker-compose -f infra/docker-compose.yml logs [service_name]

# Restart services
docker-compose -f infra/docker-compose.yml restart [service_name]

# Check database
psql -h localhost -U primedata -d primedata

# Run migrations
cd backend
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

---

**Congratulations!** You should now have PrimeData running locally. Start exploring the features and building your AI-ready data pipelines!
