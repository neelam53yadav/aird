#!/usr/bin/env bash
set -euo pipefail

echo "Airflow init: running db migrate..."
airflow db migrate

echo "Airflow init: verifying DB is ready..."
airflow db check

echo "Airflow init: creating admin user (if not exists)..."
if airflow users list | awk '{print $2}' | grep -qx "${AIRFLOW_ADMIN_USER}"; then
  echo "Admin user already exists: ${AIRFLOW_ADMIN_USER}"
else
  airflow users create \
    -u "${AIRFLOW_ADMIN_USER}" \
    -f "${AIRFLOW_ADMIN_FIRSTNAME}" \
    -l "${AIRFLOW_ADMIN_LASTNAME}" \
    -r "Admin" \
    -e "${AIRFLOW_ADMIN_EMAIL}" \
    -p "${AIRFLOW_ADMIN_PASSWORD}"
  echo "Admin user created: ${AIRFLOW_ADMIN_USER}"
fi

echo "Airflow init complete."
EOF

chmod +x infra/airflow/init.sh

