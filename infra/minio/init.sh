#!/bin/sh
set -eu

MINIO_URL="http://minio:${MINIO_PORT:-9000}"
BUCKET="${MINIO_BUCKET_NAME:-aird}"

echo "Waiting for MinIO at ${MINIO_URL} ..."
until mc alias set local "${MINIO_URL}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; do
  sleep 2
done

echo "MinIO reachable. Ensuring bucket exists -> ${BUCKET}"
mc mb --ignore-existing "local/${BUCKET}" >/dev/null

echo "MinIO init complete. Buckets:"
mc ls local
