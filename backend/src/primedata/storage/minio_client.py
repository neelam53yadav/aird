"""
MinIO client wrapper for PrimeData storage operations.
Supports both MinIO (local) and GCS (Google Cloud Storage) via Application Default Credentials.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

# Try to import google-cloud-storage (optional, only needed for GCS)
try:
    from google.cloud import storage as gcs_storage
    from google.auth.exceptions import DefaultCredentialsError
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    logger.warning("google-cloud-storage not available. GCS support disabled.")


class MinIOClient:
    """MinIO client wrapper with PrimeData-specific operations.
    
    Supports both MinIO (local development) and GCS (production) via Application Default Credentials.
    Set USE_GCS=true to use GCS instead of MinIO.
    """

    def __init__(self):
        """Initialize storage client from environment variables.
        
        Supports both MinIO (local) and GCS (Google Cloud Storage) via Application Default Credentials.
        """
        self.use_gcs = os.getenv("USE_GCS", "false").lower() == "true"
        
        if self.use_gcs:
            # Initialize GCS client using Application Default Credentials
            if not GCS_AVAILABLE:
                raise ImportError(
                    "google-cloud-storage is required for GCS support. "
                    "Install it with: pip install google-cloud-storage"
                )
            
            try:
                self.gcs_client = gcs_storage.Client()
                self.project_id = os.getenv("GCS_PROJECT_ID")
                if self.project_id:
                    logger.info(f"Initialized GCS client for project: {self.project_id}")
                else:
                    logger.info("Initialized GCS client using Application Default Credentials")
            except DefaultCredentialsError as e:
                raise ValueError(
                    "GCS credentials not found. Ensure Application Default Credentials are configured. "
                    "When running on GCP, the service account will be used automatically. "
                    f"Error: {str(e)}"
                )
            self.client = None  # MinIO client not used for GCS
        else:
            # Initialize MinIO client for local development
            self.host = os.getenv("MINIO_HOST", "localhost:9000")
            self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
            self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
            self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
            self.client = Minio(self.host, access_key=self.access_key, secret_key=self.secret_key, secure=self.secure)
            self.gcs_client = None  # GCS client not used for MinIO
            logger.info(f"Initialized MinIO client for local MinIO at {self.host}")

        # Don't ensure buckets during initialization - do it lazily
        self._buckets_ensured = False

    def _ensure_buckets(self):
        """Ensure all required buckets exist.
        
        For MinIO: Creates buckets if they don't exist.
        For GCS: Only checks if buckets exist (buckets must be created manually in GCP).
        """
        if self._buckets_ensured:
            return

        buckets = [
            "primedata-raw",
            "primedata-clean",
            "primedata-chunk",
            "primedata-embed",
            "primedata-exports",
            "primedata-config",
        ]

        if self.use_gcs:
            # For GCS, just verify buckets exist (don't create)
            for bucket_name in buckets:
                try:
                    bucket = self.gcs_client.bucket(bucket_name)
                    if bucket.exists():
                        logger.debug(f"GCS bucket {bucket_name} exists")
                    else:
                        logger.warning(
                            f"GCS bucket {bucket_name} does not exist. "
                            f"Please create it manually using: gsutil mb gs://{bucket_name}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to check GCS bucket {bucket_name}: {e}")
        else:
            # For MinIO, create buckets if they don't exist
            for bucket in buckets:
                try:
                    if not self.client.bucket_exists(bucket):
                        self.client.make_bucket(bucket)
                        logger.info(f"Created MinIO bucket: {bucket}")
                except S3Error as e:
                    logger.warning(f"Failed to create MinIO bucket {bucket}: {e}")
                    # Don't raise - just log warning and continue
                    # This allows the app to start even if MinIO is not available

        self._buckets_ensured = True

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: Optional[str] = None) -> bool:
        """Upload bytes data to storage (MinIO or GCS).

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
            
            if self.use_gcs:
                # Upload to GCS
                gcs_bucket = self.gcs_client.bucket(bucket)
                blob = gcs_bucket.blob(key)
                blob.upload_from_string(data, content_type=content_type or "application/octet-stream")
                logger.info(f"Uploaded {len(data)} bytes to GCS {bucket}/{key}")
                return True
            else:
                # Upload to MinIO
                from io import BytesIO
                data_stream = BytesIO(data)
                self.client.put_object(
                    bucket, key, data_stream, length=len(data), content_type=content_type or "application/octet-stream"
                )
                logger.info(f"Uploaded {len(data)} bytes to MinIO {bucket}/{key}")
                return True
        except S3Error as e:
            logger.error(f"Failed to upload to {bucket}/{key}: {e}")
            return False
        except Exception as e:
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
            return self.put_bytes(bucket, key, json_data.encode("utf-8"), "application/json")
        except Exception as e:
            logger.error(f"Failed to upload JSON to {bucket}/{key}: {e}")
            return False

    def list_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
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
            
            if self.use_gcs:
                # List objects from GCS
                gcs_bucket = self.gcs_client.bucket(bucket)
                for blob in gcs_bucket.list_blobs(prefix=prefix):
                    objects.append(
                        {
                            "name": blob.name,
                            "size": blob.size,
                            "last_modified": blob.time_created.isoformat() if blob.time_created else None,
                            "etag": blob.etag,
                            "content_type": blob.content_type,
                        }
                    )
            else:
                # List objects from MinIO
                for obj in self.client.list_objects(bucket, prefix=prefix, recursive=True):
                    # Get full object metadata including content type
                    try:
                        stat = self.client.stat_object(bucket, obj.object_name)
                        content_type = stat.content_type
                    except S3Error:
                        content_type = None

                    objects.append(
                        {
                            "name": obj.object_name,
                            "size": obj.size,
                            "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                            "etag": obj.etag,
                            "content_type": content_type,
                        }
                    )
            return objects
        except S3Error as e:
            logger.error(f"Failed to list objects in {bucket} with prefix {prefix}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to list objects in {bucket} with prefix {prefix}: {e}")
            return []

    def presign(self, bucket: str, key: str, expiry: int = 3600, inline: bool = False) -> Optional[str]:
        """Generate presigned URL for object access.

        Args:
            bucket: Bucket name
            key: Object key
            expiry: URL expiry time in seconds (default: 1 hour)
            inline: If True, add response-content-disposition=inline to make content display in browser instead of downloading (default: False)

        Returns:
            Presigned URL or None if failed
        """
        try:
            self._ensure_buckets()
            
            if self.use_gcs:
                # Generate signed URL for GCS
                from datetime import timedelta, datetime
                gcs_bucket = self.gcs_client.bucket(bucket)
                blob = gcs_bucket.blob(key)
                
                # GCS signed URL parameters
                url = blob.generate_signed_url(
                    expiration=datetime.utcnow() + timedelta(seconds=expiry),
                    method="GET",
                    response_disposition="inline" if inline else "attachment"
                )
                return url
            else:
                # Generate presigned URL for MinIO
                from datetime import timedelta
                response_headers = None
                if inline:
                    response_headers = {"response-content-disposition": "inline"}

                url = self.client.presigned_get_object(
                    bucket_name=bucket, object_name=key, expires=timedelta(seconds=expiry), response_headers=response_headers
                )
                return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {bucket}/{key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {bucket}/{key}: {e}", exc_info=True)
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
            
            if self.use_gcs:
                # Download from GCS
                logger.info(f"[MinIOClient.get_object] Using GCS, downloading blob...")
                gcs_bucket = self.gcs_client.bucket(bucket)
                blob = gcs_bucket.blob(key)
                data = blob.download_as_bytes()
                logger.info(f"[MinIOClient.get_object] Read {len(data)} bytes successfully from GCS")
                return data
            else:
                # Download from MinIO
                logger.info(f"[MinIOClient.get_object] Using MinIO, calling client.get_object...")
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
            logger.error(
                f"[MinIOClient.get_object] S3Error code: {getattr(e, 'code', 'unknown')}, message: {getattr(e, 'message', 'unknown')}"
            )
            return None
        except Exception as e:
            error_msg = (
                f"[MinIOClient.get_object] Unexpected exception getting object {bucket}/{key}: {type(e).__name__}: {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            return None

    def put_object(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
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
            
            if self.use_gcs:
                # Upload to GCS
                gcs_bucket = self.gcs_client.bucket(bucket)
                blob = gcs_bucket.blob(key)
                blob.upload_from_string(data, content_type=content_type)
                return True
            else:
                # Upload to MinIO
                from io import BytesIO
                data_stream = BytesIO(data)
                self.client.put_object(bucket, key, data_stream, len(data), content_type=content_type)
                return True
        except S3Error as e:
            logger.error(f"Failed to put object {bucket}/{key}: {e}")
            return False
        except Exception as e:
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
            
            if self.use_gcs:
                # Check existence in GCS
                gcs_bucket = self.gcs_client.bucket(bucket)
                blob = gcs_bucket.blob(key)
                return blob.exists()
            else:
                # Check existence in MinIO
                self.client.stat_object(bucket, key)
                return True
        except S3Error:
            return False
        except Exception:
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
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse JSON from {bucket}/{key}: {e}")
            return None

    def copy_object(self, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> bool:
        """Copy an object from source to destination.

        Args:
            source_bucket: Source bucket name
            source_key: Source object key
            dest_bucket: Destination bucket name
            dest_key: Destination object key

        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_buckets()

            if self.use_gcs:
                # Copy in GCS (more efficient - uses server-side copy)
                source_bucket_obj = self.gcs_client.bucket(source_bucket)
                dest_bucket_obj = self.gcs_client.bucket(dest_bucket)
                source_blob = source_bucket_obj.blob(source_key)
                new_blob = source_bucket_obj.copy_blob(source_blob, dest_bucket_obj, dest_key)
                logger.info(f"Copied object from GCS {source_bucket}/{source_key} to {dest_bucket}/{dest_key}")
                return True
            else:
                # Copy in MinIO (read and write)
                # Read the source object
                source_data = self.get_object(source_bucket, source_key)
                if source_data is None:
                    logger.error(f"Failed to read source object {source_bucket}/{source_key}")
                    return False

                # Get content type from source object
                try:
                    stat = self.client.stat_object(source_bucket, source_key)
                    content_type = stat.content_type or "application/octet-stream"
                except S3Error:
                    content_type = "application/octet-stream"

                # Write to destination
                success = self.put_object(dest_bucket, dest_key, source_data, content_type)
                if success:
                    logger.info(f"Copied object from MinIO {source_bucket}/{source_key} to {dest_bucket}/{dest_key}")
                return success
        except S3Error as e:
            logger.error(f"Failed to copy object from {source_bucket}/{source_key} to {dest_bucket}/{dest_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error copying object: {e}", exc_info=True)
            return False


# Global instance
minio_client = MinIOClient()
