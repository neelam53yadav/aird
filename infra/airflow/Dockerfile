# infra/airflow/Dockerfile
# Airflow base image pinned to your current version
FROM apache/airflow:2.7.1-python3.11

USER root

# Optional: avoid failing apt-get update on corp networks / extra repos
# (Base image sometimes carries extra apt sources; we only need Debian official repos)
RUN rm -f /etc/apt/sources.list.d/*microsoft* /etc/apt/sources.list.d/*pgdg* || true
RUN rm -f /etc/apt/sources.list.d/* || true


RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy Airflow constraints + extra requirements (installed under constraints to avoid conflicts)
COPY constraints/constraints-3.11.txt /opt/airflow/constraints-3.11.txt
COPY requirements-extra.txt /opt/airflow/requirements-extra.txt

# Optional custom CA certs (place *.crt in infra/airflow/certs/)
USER root
COPY certs/ /usr/local/share/ca-certificates/
RUN update-ca-certificates
USER airflow

# Keep pip sane; use constraints to avoid dependency conflicts
RUN python -m pip install --no-cache-dir --upgrade "pip<25" "setuptools<67" "wheel"

# Install extra deps using Airflow constraints (prevents urllib3/cffi conflicts)
# Install deps that must respect Airflow constraints
RUN pip install --no-cache-dir \
  --constraint /opt/airflow/constraints-3.11.txt \
  -r /opt/airflow/requirements-extra.txt
