@echo off
echo Setting up PrimeData backend environment file...
echo.

cd backend

if exist .env (
    echo .env file already exists. Backing up to .env.backup
    copy .env .env.backup
)

echo Creating .env file with MLflow configuration...
(
echo # Environment
echo ENV=development
echo.
echo # Database
echo DATABASE_URL=postgresql+psycopg2://primedata:primedata123@localhost:5433/primedata
echo.
echo # CORS
echo CORS_ORIGINS=["http://localhost:3000"]
echo.
echo # Authentication
echo NEXTAUTH_SECRET=REPLACE_WITH_64_CHAR_RANDOM_STRING_FOR_PRODUCTION_USE_ONLY
echo JWT_ISSUER=https://api.local/auth
echo JWT_AUDIENCE=primedata-api
echo API_SESSION_EXCHANGE_ALLOWED_ISS=https://nextauth.local
echo.
echo # MLflow Configuration
echo MLFLOW_TRACKING_URI=http://localhost:5000
echo MLFLOW_BACKEND_STORE_URI=postgresql://primedata:primedata123@localhost:5433/primedata
echo MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://mlflow-artifacts
echo.
echo # Testing Configuration (for development)
echo DISABLE_AUTH=true
echo TESTING_MODE=true
echo.
echo # MinIO Configuration
echo MINIO_HOST=localhost:9000
echo MINIO_ACCESS_KEY=minioadmin
echo MINIO_SECRET_KEY=minioadmin123
echo MINIO_SECURE=false
echo.
echo # Qdrant Configuration
echo QDRANT_HOST=localhost
echo QDRANT_PORT=6333
echo QDRANT_GRPC_PORT=6334
) > .env

echo.
echo ✅ .env file created successfully!
echo.
echo The backend will now load these environment variables automatically.
echo You can modify the .env file to change any settings.
echo.
pause
