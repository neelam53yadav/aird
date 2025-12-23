# PrimeData Troubleshooting Guide

This comprehensive troubleshooting guide covers common issues, solutions, and debugging steps for the PrimeData platform.

## 🚨 Quick Diagnostics

### **System Health Check**
```bash
# Check all services
curl http://localhost:8000/health

# Expected response:
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

### **Service Status Check**
```bash
# Check Docker services
docker-compose -f infra/docker-compose.yml ps

# Check individual services
curl http://localhost:3000  # Frontend
curl http://localhost:8000/health  # Backend API
curl http://localhost:5000  # MLflow
curl http://localhost:8080/health  # Airflow
curl http://localhost:9000/minio/health  # MinIO
curl http://localhost:6333/health  # Qdrant
```

## 🔧 Setup & Installation Issues

### **Virtual Environment Issues**

#### **Problem**: `No module named 'alembic'` or similar import errors
```bash
# Solution: Activate virtual environment properly
cd backend
.\venv\Scripts\Activate.ps1
# or
venv\Scripts\activate
```

#### **Problem**: `python: command not found`
```bash
# Solution: Install Python 3.11+ and ensure it's in PATH
python --version  # Should show 3.11+
# If not, install from python.org or use pyenv
```

#### **Problem**: `pip install` fails with permission errors
```bash
# Solution: Use virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### **Docker & Docker Compose Issues**

#### **Problem**: `docker-compose: command not found`
```bash
# Solution: Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop
# Ensure Docker Desktop is running
```

#### **Problem**: Port conflicts (ports already in use)
```bash
# Solution: Check what's using the ports
netstat -ano | findstr :3000
netstat -ano | findstr :8000
netstat -ano | findstr :5000
netstat -ano | findstr :8080
netstat -ano | findstr :9000
netstat -ano | findstr :6333

# Kill processes if needed
taskkill /PID <process_id> /F
```

#### **Problem**: Docker containers won't start
```bash
# Solution: Check Docker logs
docker-compose -f infra/docker-compose.yml logs

# Restart services
docker-compose -f infra/docker-compose.yml down
docker-compose -f infra/docker-compose.yml up -d
```

### **Database Issues**

#### **Problem**: `psycopg2.OperationalError: connection refused`
```bash
# Solution: Check PostgreSQL is running
docker-compose -f infra/docker-compose.yml ps postgres

# If not running, start it
docker-compose -f infra/docker-compose.yml up -d postgres

# Wait for it to be ready, then run migrations
cd backend
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

#### **Problem**: `alembic: command not found`
```bash
# Solution: Activate virtual environment first
cd backend
.\venv\Scripts\Activate.ps1
python -m alembic upgrade head
```

#### **Problem**: Migration conflicts
```bash
# Solution: Check current migration state
alembic current

# If needed, reset migrations (WARNING: This will lose data)
alembic downgrade base
alembic upgrade head
```

## 🌐 Frontend Issues

### **Next.js & React Issues**

#### **Problem**: `Module not found: Can't resolve 'class-variance-authority'`
```bash
# Solution: Install missing dependencies
cd ui
npm install class-variance-authority
# or
npm install
```

#### **Problem**: `next-auth` errors
```bash
# Solution: Check environment variables
# Ensure .env.local has:
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

#### **Problem**: `Cannot read properties of undefined`
```bash
# Solution: Check API responses and add null checks
# Common in analytics page - check if data is loaded
if (analytics?.monthlyStats) {
  // Safe to access monthlyStats
}
```

### **Authentication Issues**

#### **Problem**: `[next-auth][error][NO_SECRET]`
```bash
# Solution: Add NEXTAUTH_SECRET to .env.local
NEXTAUTH_SECRET=your-32-character-secret-key
```

#### **Problem**: Google OAuth not working
```bash
# Solution: Check Google OAuth configuration
# 1. Go to Google Cloud Console
# 2. Create OAuth 2.0 credentials
# 3. Add authorized redirect URIs:
#    - http://localhost:3000/api/auth/callback/google
# 4. Update .env.local with correct credentials
```

#### **Problem**: `Failed to update profile` errors
```bash
# Solution: Check backend API is running
curl http://localhost:8000/health

# Check API endpoint exists
curl http://localhost:8000/api/v1/users/me
```

## 🔌 Backend API Issues

### **FastAPI Issues**

#### **Problem**: `ModuleNotFoundError: No module named 'primedata'`
```bash
# Solution: Install package in development mode
cd backend
.\venv\Scripts\Activate.ps1
pip install -e .
```

#### **Problem**: `ImportError: cannot import name 'Optional'`
```bash
# Solution: Check imports in Python files
# Ensure: from typing import Optional
# Fix any missing imports
```

#### **Problem**: `ValidationError: Input should be a valid string`
```bash
# Solution: Check Pydantic models
# Ensure Optional fields are properly typed:
# picture_url: Optional[str] = None  # Correct
# picture_url: str = None  # Incorrect
```

### **Database Connection Issues**

#### **Problem**: `sqlalchemy.exc.OperationalError: connection refused`
```bash
# Solution: Check database connection
# 1. Verify PostgreSQL is running
# 2. Check DATABASE_URL in .env
# 3. Test connection:
python -c "from primedata.db.database import engine; print(engine.url)"
```

#### **Problem**: `alembic.util.exc.CommandError: Can't locate revision`
```bash
# Solution: Check migration history
alembic history
alembic current

# If corrupted, reset:
alembic downgrade base
alembic upgrade head
```

### **API Endpoint Issues**

#### **Problem**: `404 Not Found` for API endpoints
```bash
# Solution: Check router registration in app.py
# Ensure all routers are included:
app.include_router(auth_router)
app.include_router(products_router)
# etc.
```

#### **Problem**: `500 Internal Server Error`
```bash
# Solution: Check backend logs
# Look for specific error messages
# Common issues:
# - Missing environment variables
# - Database connection issues
# - Import errors
```

## 🗄️ Database Issues

### **PostgreSQL Issues**

#### **Problem**: Database connection timeout
```bash
# Solution: Check PostgreSQL status
docker-compose -f infra/docker-compose.yml ps postgres

# Check logs
docker-compose -f infra/docker-compose.yml logs postgres

# Restart if needed
docker-compose -f infra/docker-compose.yml restart postgres
```

#### **Problem**: `relation does not exist`
```bash
# Solution: Run migrations
cd backend
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

#### **Problem**: Migration conflicts
```bash
# Solution: Check migration files
# Look for duplicate revision IDs
# Check alembic/versions/ directory
# Remove duplicate or conflicting migrations
```

### **Data Quality Rules Issues**

#### **Problem**: `Data quality validation failed`
```bash
# Solution: Check rule configuration
# 1. Verify rule format in database
# 2. Check rule validation logic
# 3. Test rules individually
```

#### **Problem**: Rules not persisting
```bash
# Solution: Check database connection
# Verify rules are being saved to database
# Check for transaction rollbacks
```

## 🔄 Pipeline Issues

### **Airflow Issues**

#### **Problem**: DAG not appearing in Airflow UI
```bash
# Solution: Check DAG files
# 1. Verify DAG files are in correct location
# 2. Check for syntax errors in DAG files
# 3. Restart Airflow scheduler
```

#### **Problem**: `Task failed` in Airflow
```bash
# Solution: Check task logs
# 1. Go to Airflow UI → DAG → Task → Logs
# 2. Look for specific error messages
# 3. Check dependencies and imports
```

#### **Problem**: `No module named 'primedata'` in Airflow
```bash
# Solution: Install package in Airflow container
# Add to Dockerfile or requirements.txt
# Rebuild Airflow image
```

### **MLflow Issues**

#### **Problem**: `MLflow tracking failed`
```bash
# Solution: Check MLflow server
curl http://localhost:5000/health

# Check environment variables
echo $MLFLOW_TRACKING_URI
echo $MLFLOW_BACKEND_STORE_URI
```

#### **Problem**: `Experiment not found`
```bash
# Solution: Check experiment creation
# Verify experiment is created before logging
# Check experiment name and ID
```

## 💰 Billing & Stripe Issues

### **Stripe Integration Issues**

#### **Problem**: `Stripe error: Invalid API key`
```bash
# Solution: Check Stripe configuration
# 1. Verify STRIPE_SECRET_KEY in .env
# 2. Use test keys for development
# 3. Check key format (starts with sk_test_)
```

#### **Problem**: `Webhook signature verification failed`
```bash
# Solution: Check webhook configuration
# 1. Verify STRIPE_WEBHOOK_SECRET
# 2. Check webhook endpoint URL
# 3. Test webhook with Stripe CLI
```

#### **Problem**: `Price ID not found`
```bash
# Solution: Check price configuration
# 1. Create products and prices in Stripe Dashboard
# 2. Update price IDs in .env
# 3. Use test price IDs for development
```

## 📊 Analytics & Monitoring Issues

### **Analytics Dashboard Issues**

#### **Problem**: `Failed to get analytics metrics`
```bash
# Solution: Check analytics API
# 1. Verify analytics endpoint is working
# 2. Check database queries
# 3. Verify data exists in database
```

#### **Problem**: `Cannot read properties of undefined` in analytics
```bash
# Solution: Add null checks in frontend
# Check if data is loaded before accessing properties
# Add loading states and error handling
```

## 🔐 Security Issues

### **Authentication & Authorization**

#### **Problem**: `JWT token expired`
```bash
# Solution: Check token expiration
# 1. Verify JWT secret is set
# 2. Check token expiration time
# 3. Implement token refresh if needed
```

#### **Problem**: `Access denied` errors
```bash
# Solution: Check user permissions
# 1. Verify user has access to workspace
# 2. Check role-based permissions
# 3. Verify workspace membership
```

## 🐛 Debugging Tips

### **General Debugging**

1. **Check Logs**: Always check application logs first
2. **Health Checks**: Use `/health` endpoint to verify services
3. **Environment Variables**: Verify all required env vars are set
4. **Service Dependencies**: Ensure all services are running
5. **Database State**: Check database migrations and data integrity

### **Frontend Debugging**

1. **Browser Console**: Check for JavaScript errors
2. **Network Tab**: Check API requests and responses
3. **React DevTools**: Use React DevTools for component debugging
4. **Next.js Debug**: Use `NODE_ENV=development` for detailed errors

### **Backend Debugging**

1. **FastAPI Docs**: Use `/docs` endpoint for API testing
2. **Database Queries**: Check SQL queries in logs
3. **Import Errors**: Verify all imports are correct
4. **Environment**: Check all environment variables

### **Database Debugging**

1. **Connection**: Test database connection
2. **Migrations**: Check migration status
3. **Data Integrity**: Verify data consistency
4. **Queries**: Check SQL query performance

## 📞 Getting Help

### **When to Check What**

1. **Setup Issues**: Check this troubleshooting guide
2. **API Issues**: Check API documentation and logs
3. **Database Issues**: Check database logs and migrations
4. **Frontend Issues**: Check browser console and network tab
5. **Pipeline Issues**: Check Airflow and MLflow logs

### **Useful Commands**

```bash
# Check all services
docker-compose -f infra/docker-compose.yml ps

# View logs
docker-compose -f infra/docker-compose.yml logs [service_name]

# Restart services
docker-compose -f infra/docker-compose.yml restart [service_name]

# Check database
psql -h localhost -U primedata -d primedata

# Check migrations
alembic current
alembic history

# Test API
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

### **Common Solutions**

1. **Restart Services**: Often fixes temporary issues
2. **Check Logs**: Provides specific error information
3. **Verify Configuration**: Ensure all settings are correct
4. **Update Dependencies**: Keep packages up to date
5. **Clear Cache**: Clear browser cache and application cache

---

**Remember**: Most issues are configuration-related. Double-check your environment variables, service status, and dependencies before diving into complex debugging.
