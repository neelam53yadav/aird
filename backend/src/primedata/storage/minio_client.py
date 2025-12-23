"""
MinIO client wrapper for PrimeData storage operations.
"""

import os
import json
from typing import List, Dict, Any, Optional
from minio import Minio
from minio.error import S3Error
import logging

logger = logging.getLogger(__name__)


class MinIOClient:
    """MinIO client wrapper with PrimeData-specific operations."""
    
    def __init__(self):
        """Initialize MinIO client from environment variables."""
        self.host = os.getenv('MINIO_HOST', 'localhost:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin123')  # Fixed default to match Docker setup
        self.secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
        
        self.client = Minio(
            self.host,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # Don't ensure buckets during initialization - do it lazily
        self._buckets_ensured = False
    
    def _ensure_buckets(self):
        """Ensure all required buckets exist."""
        if self._buckets_ensured:
            return
            
        buckets = [
            'primedata-raw',
            'primedata-clean', 
            'primedata-chunk',
            'primedata-embed',
            'primedata-exports',
            'primedata-config'
        ]
        
        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info(f"Created bucket: {bucket}")
            except S3Error as e:
                logger.warning(f"Failed to create bucket {bucket}: {e}")
                # Don't raise - just log warning and continue
                # This allows the app to start even if MinIO is not available
                
        self._buckets_ensured = True
    
    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: Optional[str] = None) -> bool:
        """Upload bytes data to MinIO.
        
        Args:
            bucket: Bucket name
            key: Object key
            data: Bytes data to upload
            content_type: MIME type (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_buckets()
            from io import BytesIO
            data_stream = BytesIO(data)
            
            self.client.put_object(
                bucket,
                key,
                data_stream,
                length=len(data),
                content_type=content_type or 'application/octet-stream'
            )
            logger.info(f"Uploaded {len(data)} bytes to {bucket}/{key}")
            return True
        except S3Error as e:
            logger.error(f"Failed to upload to {bucket}/{key}: {e}")
            return False
    
    def put_json(self, bucket: str, key: str, obj: Any) -> bool:
        """Upload JSON object to MinIO.
        
        Args:
            bucket: Bucket name
            key: Object key
            obj: Python object to serialize as JSON
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_buckets()
            json_data = json.dumps(obj, indent=2, default=str)
            return self.put_bytes(bucket, key, json_data.encode('utf-8'), 'application/json')
        except Exception as e:
            logger.error(f"Failed to upload JSON to {bucket}/{key}: {e}")
            return False
    
    def list_objects(self, bucket: str, prefix: str = '') -> List[Dict[str, Any]]:
        """List objects in bucket with optional prefix.
        
        Args:
            bucket: Bucket name
            prefix: Key prefix to filter by
            
        Returns:
            List of object metadata dictionaries
        """
        try:
            self._ensure_buckets()
            objects = []
            for obj in self.client.list_objects(bucket, prefix=prefix, recursive=True):
                # Get full object metadata including content type
                try:
                    stat = self.client.stat_object(bucket, obj.object_name)
                    content_type = stat.content_type
                except S3Error:
                    content_type = None
                
                objects.append({
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'etag': obj.etag,
                    'content_type': content_type
                })
            return objects
        except S3Error as e:
            logger.error(f"Failed to list objects in {bucket} with prefix {prefix}: {e}")
            return []
    
    def presign(self, bucket: str, key: str, expiry: int = 3600) -> Optional[str]:
        """Generate presigned URL for object access.
        
        Args:
            bucket: Bucket name
            key: Object key
            expiry: URL expiry time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL or None if failed
        """
        try:
            self._ensure_buckets()
            from datetime import timedelta
            url = self.client.presigned_get_object(bucket, key, expires=timedelta(seconds=expiry))
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {bucket}/{key}: {e}")
            return None
    
    def get_object(self, bucket: str, key: str) -> Optional[bytes]:
        """Download object as bytes.
        
        Args:
            bucket: Bucket name
            key: Object key
            
        Returns:
            Object data as bytes or None if failed
        """
        try:
            logger.info(f"[MinIOClient.get_object] Attempting to get object: bucket={bucket}, key={key}")
            self._ensure_buckets()
            logger.info(f"[MinIOClient.get_object] Buckets ensured, calling client.get_object...")
            response = self.client.get_object(bucket, key)
            logger.info(f"[MinIOClient.get_object] Got response, reading data...")
            data = response.read()
            logger.info(f"[MinIOClient.get_object] Read {len(data)} bytes successfully")
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            error_msg = f"[MinIOClient.get_object] S3Error getting object {bucket}/{key}: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"[MinIOClient.get_object] S3Error code: {getattr(e, 'code', 'unknown')}, message: {getattr(e, 'message', 'unknown')}")
            return None
        except Exception as e:
            error_msg = f"[MinIOClient.get_object] Unexpected exception getting object {bucket}/{key}: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None
    
    def put_object(self, bucket: str, key: str, data: bytes, content_type: str = 'application/octet-stream') -> bool:
        """Upload object data.
        
        Args:
            bucket: Bucket name
            key: Object key
            data: Object data as bytes
            content_type: Content type of the object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_buckets()
            from io import BytesIO
            data_stream = BytesIO(data)
            self.client.put_object(bucket, key, data_stream, len(data), content_type=content_type)
            return True
        except S3Error as e:
            logger.error(f"Failed to put object {bucket}/{key}: {e}")
            return False
    
    def object_exists(self, bucket: str, key: str) -> bool:
        """Check if object exists.
        
        Args:
            bucket: Bucket name
            key: Object key
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            self._ensure_buckets()
            self.client.stat_object(bucket, key)
            return True
        except S3Error:
            return False
    
    def get_bytes(self, bucket: str, key: str) -> Optional[bytes]:
        """Download object as bytes (alias for get_object for consistency).
        
        Args:
            bucket: Bucket name
            key: Object key
            
        Returns:
            Object data as bytes or None if failed
        """
        return self.get_object(bucket, key)
    
    def get_json(self, bucket: str, key: str) -> Optional[Any]:
        """Download and parse JSON object.
        
        Args:
            bucket: Bucket name
            key: Object key
            
        Returns:
            Parsed JSON object (dict/list) or None if failed
        """
        data = self.get_object(bucket, key)
        if data is None:
            return None
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse JSON from {bucket}/{key}: {e}")
            return None


# Global instance
minio_client = MinIOClient()
