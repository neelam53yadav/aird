"""
FastAPI application for PrimeData API.
"""

import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from primedata.core.settings import get_settings
from primedata.core.jwt_keys import get_public_jwks
from primedata.core.auth_middleware import AuthMiddleware
from primedata.db.database import engine, get_db
from primedata.api.auth import router as auth_router
from primedata.api.products import router as products_router
from primedata.api.datasources import router as datasources_router
from primedata.api.artifacts import router as artifacts_router
from primedata.api.pipeline import router as pipeline_router
from primedata.api.playground import router as playground_router
from primedata.api.ai_readiness import router as ai_readiness_router
from primedata.api.embedding_models import router as embedding_models_router
from primedata.api.data_quality import router as data_quality_router
from primedata.api.exports import router as exports_router
from primedata.api.billing import router as billing_router
from primedata.api.analytics import router as analytics_router
from primedata.api.playbooks import router as playbooks_router  # M1
from primedata.api.acl import router as acl_router  # M5
from primedata.api.settings import router as settings_router

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="PrimeData API",
    description="AI-ready data from any source",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(datasources_router)
app.include_router(artifacts_router)
app.include_router(pipeline_router)
app.include_router(playground_router)
app.include_router(ai_readiness_router)
app.include_router(embedding_models_router)
app.include_router(data_quality_router)
app.include_router(exports_router, prefix="/api/v1/exports", tags=["exports"])
app.include_router(billing_router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(playbooks_router)  # M1
app.include_router(acl_router)  # M5
app.include_router(settings_router)


async def check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return {"status": "healthy", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Database connection failed: {str(e)}"}


async def check_qdrant() -> Dict[str, Any]:
    """Check Qdrant connectivity."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:6333/", timeout=5.0)
            if response.status_code == 200:
                return {"status": "healthy", "message": "Qdrant is accessible"}
            else:
                return {"status": "unhealthy", "message": f"Qdrant returned status {response.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Qdrant connection failed: {str(e)}"}


async def check_minio() -> Dict[str, Any]:
    """Check MinIO connectivity."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:9000/minio/health/live", timeout=5.0)
            if response.status_code == 200:
                return {"status": "healthy", "message": "MinIO is accessible"}
            else:
                return {"status": "unhealthy", "message": f"MinIO returned status {response.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"MinIO connection failed: {str(e)}"}


# MLflow check disabled - MLflow integration removed
# async def check_mlflow() -> Dict[str, Any]:
#     """Check MLflow connectivity."""
#     ...


async def check_airflow() -> Dict[str, Any]:
    """Check Airflow connectivity."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/health", timeout=5.0)
            if response.status_code == 200:
                return {"status": "healthy", "message": "Airflow is accessible"}
            else:
                return {"status": "unhealthy", "message": f"Airflow returned status {response.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Airflow connection failed: {str(e)}"}


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    # Check all services concurrently (MLflow removed)
    services = await asyncio.gather(check_database(), check_qdrant(), check_minio(), check_airflow(), return_exceptions=True)

    # Process results
    service_results = {
        "database": (
            services[0] if not isinstance(services[0], Exception) else {"status": "unhealthy", "message": str(services[0])}
        ),
        "qdrant": (
            services[1] if not isinstance(services[1], Exception) else {"status": "unhealthy", "message": str(services[1])}
        ),
        "minio": (
            services[2] if not isinstance(services[2], Exception) else {"status": "unhealthy", "message": str(services[2])}
        ),
        "airflow": (
            services[3] if not isinstance(services[3], Exception) else {"status": "unhealthy", "message": str(services[3])}
        ),
    }

    # Determine overall status
    all_healthy = all(service["status"] == "healthy" for service in service_results.values())
    overall_status = "healthy" if all_healthy else "degraded"

    return {
        "status": overall_status,
        "service": "PrimeData",
        "version": "0.1.0",
        "services": service_results,
        "timestamp": asyncio.get_event_loop().time(),
    }


@app.get("/health/simple")
async def simple_health_check():
    """Simple health check endpoint (app only)."""
    return {"status": "ok", "service": "PrimeData", "version": "0.1.0"}


@app.get("/.well-known/jwks.json")
async def get_jwks():
    """JWKS endpoint for JWT key discovery."""
    return get_public_jwks()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
