# PrimeData API Reference

This comprehensive API reference covers all endpoints, request/response formats, and usage examples for the PrimeData platform.

## 🔗 Base URL

```
http://localhost:8000
```

## 🔐 Authentication

All API endpoints require authentication via JWT tokens obtained through the authentication flow.

### **Authentication Flow**

1. **Frontend**: User signs in with Google OAuth
2. **Backend**: Exchange NextAuth token for JWT
3. **API Calls**: Include JWT in Authorization header

```http
Authorization: Bearer <jwt_token>
```

## 📚 API Endpoints

### **Authentication & User Management**

#### **POST /api/v1/auth/session/exchange**
Exchange NextAuth token for backend JWT.

**Request:**
```json
{
  "token": "nextauth_jwt_token"
}
```

**Response:**
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "user": {
    "id": "user_uuid",
    "email": "user@example.com",
    "name": "User Name",
    "roles": ["viewer"],
    "picture_url": "https://..."
  },
  "default_workspace_id": "workspace_uuid"
}
```

#### **GET /api/v1/users/me**
Get current user information.

**Response:**
```json
{
  "id": "user_uuid",
  "email": "user@example.com",
  "name": "User Name",
  "first_name": "User",
  "last_name": "Name",
  "timezone": "UTC",
  "roles": ["viewer"],
  "picture_url": "https://..."
}
```

#### **PUT /api/v1/user/profile**
Update user profile information.

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "timezone": "America/New_York"
}
```

**Response:**
```json
{
  "id": "user_uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "first_name": "John",
  "last_name": "Doe",
  "timezone": "America/New_York",
  "picture_url": "https://..."
}
```

#### **GET /api/v1/workspaces**
Get user's workspaces.

**Response:**
```json
[
  {
    "id": "workspace_uuid",
    "name": "My Workspace",
    "role": "owner",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### **Product Management**

#### **POST /api/v1/products**
Create a new product.

**Request:**
```json
{
  "workspace_id": "workspace_uuid",
  "name": "My Product",
  "description": "Product description"
}
```

**Response:**
```json
{
  "id": "product_uuid",
  "workspace_id": "workspace_uuid",
  "name": "My Product",
  "description": "Product description",
  "status": "draft",
  "current_version": 0,
  "promoted_version": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### **GET /api/v1/products**
List products.

**Query Parameters:**
- `workspace_id` (optional): Filter by workspace ID

**Response:**
```json
[
  {
    "id": "product_uuid",
    "workspace_id": "workspace_uuid",
    "name": "My Product",
    "status": "draft",
    "current_version": 0,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### **GET /api/v1/products/{product_id}**
Get product details.

**Response:**
```json
{
  "id": "product_uuid",
  "workspace_id": "workspace_uuid",
  "name": "My Product",
  "status": "draft",
  "current_version": 0,
  "chunking_config": {
    "mode": "auto",
    "auto_settings": {
      "content_type": "general",
      "model_optimized": true,
      "confidence_threshold": 0.7
    }
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### **PUT /api/v1/products/{product_id}**
Update product.

**Request:**
```json
{
  "name": "Updated Product Name",
  "description": "Updated description",
  "chunking_config": {
    "mode": "manual",
    "manual_settings": {
      "chunk_size": 1000,
      "chunk_overlap": 200,
      "chunking_strategy": "fixed_size"
    }
  }
}
```

#### **DELETE /api/v1/products/{product_id}**
Delete product.

**Response:**
```json
{
  "message": "Product deleted successfully"
}
```

### **Data Source Management**

#### **POST /api/v1/datasources**
Create a new data source.

**Request:**
```json
{
  "workspace_id": "workspace_uuid",
  "product_id": "product_uuid",
  "type": "web",
  "config": {
    "url": "https://example.com",
    "recursive": true,
    "max_depth": 3
  }
}
```

**Response:**
```json
{
  "id": "datasource_uuid",
  "workspace_id": "workspace_uuid",
  "product_id": "product_uuid",
  "type": "web",
  "config": {
    "url": "https://example.com",
    "recursive": true,
    "max_depth": 3
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### **GET /api/v1/datasources**
List data sources.

**Query Parameters:**
- `product_id` (optional): Filter by product ID

**Response:**
```json
[
  {
    "id": "datasource_uuid",
    "workspace_id": "workspace_uuid",
    "product_id": "product_uuid",
    "type": "web",
    "config": {
      "url": "https://example.com"
    },
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### **GET /api/v1/datasources/{datasource_id}**
Get data source details.

**Response:**
```json
{
  "id": "datasource_uuid",
  "workspace_id": "workspace_uuid",
  "product_id": "product_uuid",
  "type": "web",
  "config": {
    "url": "https://example.com",
    "recursive": true,
    "max_depth": 3
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### **PUT /api/v1/datasources/{datasource_id}**
Update data source.

**Request:**
```json
{
  "type": "folder",
  "config": {
    "path": "/path/to/folder",
    "recursive": true,
    "file_extensions": [".txt", ".pdf"]
  }
}
```

#### **DELETE /api/v1/datasources/{datasource_id}**
Delete data source.

**Response:**
```json
{
  "message": "Data source deleted successfully"
}
```

### **Pipeline Management**

#### **POST /api/v1/pipeline/run**
Trigger a pipeline run.

**Request:**
```json
{
  "product_id": "product_uuid",
  "version": 1,
  "force_run": false
}
```

**Response:**
```json
{
  "run_id": "run_uuid",
  "product_id": "product_uuid",
  "version": 1,
  "status": "queued",
  "started_at": "2024-01-01T00:00:00Z"
}
```

#### **GET /api/v1/pipeline/runs**
List pipeline runs.

**Query Parameters:**
- `product_id` (optional): Filter by product ID
- `status` (optional): Filter by status
- `limit` (optional): Limit number of results

**Response:**
```json
[
  {
    "id": "run_uuid",
    "product_id": "product_uuid",
    "version": 1,
    "status": "succeeded",
    "started_at": "2024-01-01T00:00:00Z",
    "finished_at": "2024-01-01T01:00:00Z",
    "duration_seconds": 3600
  }
]
```

#### **GET /api/v1/pipeline/runs/{run_id}**
Get pipeline run details.

**Response:**
```json
{
  "id": "run_uuid",
  "product_id": "product_uuid",
  "version": 1,
  "status": "succeeded",
  "started_at": "2024-01-01T00:00:00Z",
  "finished_at": "2024-01-01T01:00:00Z",
  "duration_seconds": 3600,
  "metrics": {
    "chunks_created": 1000,
    "embeddings_generated": 1000,
    "vectors_indexed": 1000,
    "processing_time": 3600
  }
}
```

### **Data Quality Management**

#### **GET /api/v1/data-quality/rules/{product_id}**
Get data quality rules for a product.

**Response:**
```json
{
  "product_id": "product_uuid",
  "rules": {
    "required_fields_rules": [
      {
        "field_name": "title",
        "severity": "error",
        "message": "Title is required"
      }
    ],
    "max_duplicate_rate_rules": [
      {
        "max_duplicate_rate": 0.1,
        "severity": "warning",
        "message": "Duplicate rate too high"
      }
    ],
    "bad_extensions_rules": [
      {
        "extensions": [".tmp", ".temp"],
        "severity": "error",
        "message": "Bad file extension"
      }
    ]
  }
}
```

#### **PUT /api/v1/data-quality/rules/{product_id}**
Update data quality rules.

**Request:**
```json
{
  "rules": {
    "required_fields_rules": [
      {
        "field_name": "title",
        "severity": "error",
        "message": "Title is required"
      }
    ],
    "max_duplicate_rate_rules": [
      {
        "max_duplicate_rate": 0.1,
        "severity": "warning",
        "message": "Duplicate rate too high"
      }
    ],
    "bad_extensions_rules": [
      {
        "extensions": [".tmp", ".temp"],
        "severity": "error",
        "message": "Bad file extension"
      }
    ]
  }
}
```

#### **GET /api/v1/data-quality/violations/{product_id}**
Get data quality violations.

**Response:**
```json
[
  {
    "id": "violation_uuid",
    "product_id": "product_uuid",
    "rule_type": "bad_extensions",
    "severity": "error",
    "message": "Bad file extension",
    "file_path": "/path/to/file.tmp",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### **Analytics & Metrics**

#### **GET /api/v1/analytics/metrics**
Get analytics metrics for a workspace.

**Query Parameters:**
- `workspace_id`: Workspace ID

**Response:**
```json
{
  "total_products": 10,
  "total_data_sources": 25,
  "total_pipeline_runs": 100,
  "success_rate": 95.5,
  "avg_processing_time": 30.5,
  "data_quality_score": 88.2,
  "recent_activity": [
    {
      "id": "run_uuid",
      "type": "pipeline",
      "message": "Product pipeline completed successfully",
      "timestamp": "2024-01-01T00:00:00Z",
      "status": "success"
    }
  ],
  "monthly_stats": [
    {
      "month": "Jan",
      "pipeline_runs": 25,
      "data_processed": 12.5,
      "quality_score": 88.2
    }
  ]
}
```

### **Export Management**

#### **POST /api/v1/exports/{product_id}/create**
Create an export bundle.

**Request:**
```json
{
  "version": 1
}
```

**Response:**
```json
{
  "key": "exports/workspace_uuid/product_uuid/bundle-20240101-120000.zip",
  "size": 1024000,
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### **GET /api/v1/exports**
List export bundles.

**Query Parameters:**
- `product_id`: Product ID

**Response:**
```json
[
  {
    "name": "bundle-20240101-120000.zip",
    "size": 1024000,
    "created_at": "2024-01-01T12:00:00Z",
    "presigned_url": "https://minio.example.com/..."
  }
]
```

### **Billing & Subscriptions**

#### **POST /api/v1/billing/checkout-session**
Create Stripe checkout session.

**Request:**
```json
{
  "workspace_id": "workspace_uuid",
  "plan": "pro"
}
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/..."
}
```

#### **GET /api/v1/billing/portal**
Get Stripe customer portal URL.

**Query Parameters:**
- `workspace_id`: Workspace ID

**Response:**
```json
{
  "portal_url": "https://billing.stripe.com/..."
}
```

#### **GET /api/v1/billing/limits**
Get billing limits and usage.

**Query Parameters:**
- `workspace_id`: Workspace ID

**Response:**
```json
{
  "plan": "free",
  "limits": {
    "max_products": 3,
    "max_data_sources_per_product": 5,
    "max_pipeline_runs_per_month": 10,
    "max_vectors": 10000,
    "schedule_frequency": "manual"
  },
  "usage": {
    "products": 2,
    "data_sources": 8,
    "pipeline_runs_this_month": 5,
    "vectors": 5000
  }
}
```

#### **POST /api/v1/billing/webhook**
Stripe webhook endpoint (public).

**Request:** Stripe webhook payload

**Response:**
```json
{
  "status": "success"
}
```

### **Embedding Models**

#### **GET /api/v1/embedding-models**
Get available embedding models.

**Query Parameters:**
- `model_type` (optional): Filter by model type
- `free_only` (optional): Show only free models
- `paid_only` (optional): Show only paid models

**Response:**
```json
{
  "models": [
    {
      "id": "text-embedding-ada-002",
      "name": "OpenAI Ada 002",
      "type": "openai",
      "free": false,
      "description": "OpenAI's text embedding model",
      "metadata": {
        "dimensions": 1536,
        "max_tokens": 8191
      }
    }
  ],
  "total": 1
}
```

#### **GET /api/v1/embedding-models/{model_id}**
Get specific embedding model details.

**Response:**
```json
{
  "id": "text-embedding-ada-002",
  "name": "OpenAI Ada 002",
  "type": "openai",
  "free": false,
  "description": "OpenAI's text embedding model",
  "metadata": {
    "dimensions": 1536,
    "max_tokens": 8191
  }
}
```

#### **POST /api/v1/embedding-models/{model_id}/validate**
Validate embedding model configuration.

**Request:**
```json
{
  "api_key": "your-api-key"
}
```

**Response:**
```json
{
  "valid": true,
  "message": "Model configuration is valid"
}
```

### **AI Readiness Assessment**

#### **GET /api/v1/ai-readiness/{product_id}**
Get AI readiness score for a product.

**Response:**
```json
{
  "product_id": "product_uuid",
  "ai_readiness_score": 85.5,
  "data_quality_metrics": {
    "total_chunks": 1000,
    "high_quality_chunks": 850,
    "medium_quality_chunks": 100,
    "low_quality_chunks": 50
  },
  "recommendations": [
    "Improve chunk quality by adjusting chunk size",
    "Add more data sources for better coverage"
  ]
}
```

### **Playground & Testing**

#### **POST /api/v1/playground/query**
Test queries against processed data.

**Request:**
```json
{
  "query": "What is machine learning?",
  "product_id": "product_uuid",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "content": "Machine learning is a subset of artificial intelligence...",
      "score": 0.95,
      "metadata": {
        "source": "https://example.com/ml-guide",
        "chunk_id": "chunk_uuid"
      }
    }
  ],
  "total": 1
}
```

## 🔍 Error Handling

### **HTTP Status Codes**

- **200**: Success
- **201**: Created
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **409**: Conflict
- **422**: Validation Error
- **500**: Internal Server Error

### **Error Response Format**

```json
{
  "detail": "Error message",
  "type": "error_type",
  "status_code": 400
}
```

### **Common Error Types**

- **ValidationError**: Invalid request data
- **AuthenticationError**: Invalid or expired token
- **AuthorizationError**: Insufficient permissions
- **NotFoundError**: Resource not found
- **ConflictError**: Resource already exists
- **BillingError**: Billing limit exceeded

## 📝 Usage Examples

### **Complete Workflow Example**

#### **1. Create Product**
```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "workspace_uuid",
    "name": "My AI Product",
    "description": "Product for AI training"
  }'
```

#### **2. Add Data Source**
```bash
curl -X POST http://localhost:8000/api/v1/datasources \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "workspace_uuid",
    "product_id": "product_uuid",
    "type": "web",
    "config": {
      "url": "https://example.com",
      "recursive": true
    }
  }'
```

#### **3. Set Data Quality Rules**
```bash
curl -X PUT http://localhost:8000/api/v1/data-quality/rules/product_uuid \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rules": {
      "required_fields_rules": [
        {
          "field_name": "title",
          "severity": "error",
          "message": "Title is required"
        }
      ]
    }
  }'
```

#### **4. Run Pipeline**
```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "product_uuid",
    "version": 1
  }'
```

#### **5. Check Results**
```bash
curl -X GET http://localhost:8000/api/v1/analytics/metrics?workspace_id=workspace_uuid \
  -H "Authorization: Bearer <token>"
```

## 🔧 Development

### **API Documentation**

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### **Testing**

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test authentication
curl -X POST http://localhost:8000/api/v1/auth/session/exchange \
  -H "Content-Type: application/json" \
  -d '{"token": "your_nextauth_token"}'
```

### **Rate Limiting**

- **Free Plan**: 100 requests/hour
- **Pro Plan**: 1000 requests/hour
- **Enterprise Plan**: Unlimited

### **Pagination**

For list endpoints, use:
- `limit`: Number of results (default: 50, max: 100)
- `offset`: Starting position (default: 0)

---

**Note**: This API reference covers the current implementation. For the most up-to-date information, always refer to the Swagger UI at http://localhost:8000/docs.