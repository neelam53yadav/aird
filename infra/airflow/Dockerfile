FROM apache/airflow:2.7.1-python3.11

USER root

# Optional: avoid failing apt-get update on corp networks / extra repos
# (Base image sometimes carries extra apt sources; we only need Debian official repos)
RUN rm -f /etc/apt/sources.list.d/*microsoft* /etc/apt/sources.list.d/*pgdg* || true

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy Airflow constraints + extra requirements
COPY constraints/constraints-3.11.txt /opt/airflow/constraints-3.11.txt
COPY requirements-extra.txt /opt/airflow/requirements-extra.txt

# Keep pip sane; use constraints to avoid dependency conflicts
RUN python -m pip install --no-cache-dir --upgrade "pip<25" "setuptools<67" "wheel"

RUN pip install --no-cache-dir \
  --constraint /opt/airflow/constraints-3.11.txt \
  -r /opt/airflow/requirements-extra.txt

# Set the working directory
WORKDIR /opt/airflow

# The source code will be mounted as a volume
