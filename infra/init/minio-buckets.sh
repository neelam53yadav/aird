#!/bin/bash

# MinIO bucket initialization script
# This script creates the required buckets for PrimeData

set -e

echo "Creating MinIO buckets for PrimeData..."

# Wait for MinIO to be ready
until mc alias set myminio http://minio:9000 minioadmin minioadmin123; do
  echo "Waiting for MinIO to be ready..."
  sleep 2
done

# Create buckets
mc mb myminio/primedata-raw --ignore-existing
mc mb myminio/primedata-clean --ignore-existing
mc mb myminio/primedata-chunk --ignore-existing
mc mb myminio/primedata-embed --ignore-existing
mc mb myminio/primedata-export --ignore-existing
mc mb myminio/mlflow-artifacts --ignore-existing

# Set bucket policies (public read for development)
mc anonymous set public myminio/primedata-export
mc anonymous set public myminio/mlflow-artifacts

echo "MinIO buckets created successfully!"
echo "Buckets:"
mc ls myminio
