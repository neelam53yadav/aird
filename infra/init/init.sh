#!/usr/bin/env sh
set -eu

: "${MINIO_ROOT_USER:?MINIO_ROOT_USER not set}"
: "${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD not set}"
: "${MINIO_BUCKET:?MINIO_BUCKET not set}"

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"

echo "Waiting for MinIO at ${MINIO_ENDPOINT}..."
i=0
until mc alias set local "${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; do
  i=$((i+1))
  if [ "$i" -gt 60 ]; then
    echo "MinIO not reachable after 60 attempts."
    exit 1
  fi
  sleep 2
done

echo "Creating bucket: ${MINIO_BUCKET}"
mc mb -p "local/${MINIO_BUCKET}" >/dev/null 2>&1 || true

# Optional: set policy (comment out if you don't want public access)
# mc anonymous set download "local/${MINIO_BUCKET}" || true

echo "MinIO init done."

