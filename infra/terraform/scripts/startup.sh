#!/bin/bash
# PrimeData VM Startup Script
# This script runs when the VM is first created

set -e

echo "=== PrimeData VM Startup Script ==="
echo "Timestamp: $(date)"

# Update system
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Add current user to docker group
usermod -aG docker $USER || true

# Install Docker Compose
echo "Installing Docker Compose..."
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Git
echo "Installing Git..."
apt-get install -y git

# Install PostgreSQL client (for database migrations)
echo "Installing PostgreSQL client..."
apt-get install -y postgresql-client

# Install Google Cloud SDK (if not already installed)
if ! command -v gcloud &> /dev/null; then
    echo "Installing Google Cloud SDK..."
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
    apt-get update -y
    apt-get install -y google-cloud-sdk
fi

# Create application directories
echo "Creating application directories..."
mkdir -p /opt/primedata/data
mkdir -p /opt/primedata/logs
chmod 755 /opt/primedata

# Create docker network (idempotent - won't fail if exists)
docker network create primedata-network 2>/dev/null || echo "Docker network already exists"

# Set up log rotation
cat > /etc/logrotate.d/primedata << EOF
/opt/primedata/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
EOF

echo "=== Startup script completed ==="
echo "Timestamp: $(date)"

