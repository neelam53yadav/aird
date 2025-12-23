# Qdrant Cloud Setup Guide

## Step 1: Create Qdrant Cloud Account
1. Go to https://cloud.qdrant.io/
2. Sign up for a free account
3. Create a new cluster (free tier: 1GB storage, 1M vectors)
4. Note down your cluster details:
   - Cluster URL: `https://your-cluster-id.qdrant.tech`
   - API Key: `your-api-key-here`

## Step 2: Update Environment Variables
Add these to your `.env` file:

```bash
# Qdrant Cloud Configuration
QDRANT_HOST=your-cluster-id.qdrant.tech
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_API_KEY=your-api-key-here
QDRANT_USE_SSL=true
```

## Step 3: Update Backend Configuration
The backend will automatically use these environment variables.

## Step 4: Test Connection
```powershell
# Test the connection
Invoke-WebRequest -Uri "https://your-cluster-id.qdrant.tech/health" -Method GET -Headers @{"api-key"="your-api-key-here"}
```

## Benefits of Qdrant Cloud
- ✅ No Docker issues
- ✅ Always available
- ✅ Managed service
- ✅ Free tier available
- ✅ Automatic scaling
- ✅ Built-in monitoring

