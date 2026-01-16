#!/usr/bin/env bash
set -euo pipefail

echo "Airflow init: waiting for DB..."
for i in {1..30}; do
  if airflow db check >/dev/null 2>&1; then
    echo "DB is reachable."
    break
  fi
  echo "DB not ready yet... ($i/30)"
  sleep 2
done

echo "Airflow init: running db migrate..."
airflow db migrate

echo "Airflow init: verifying DB is ready..."
airflow db check

echo "Airflow init: ensuring admin user exists..."
if airflow users list 2>/dev/null | awk 'NR>2 {print $2}' | grep -Fxq "${AIRFLOW_ADMIN_USER}"; then
  echo "Admin user already exists: ${AIRFLOW_ADMIN_USER}"
else
  airflow users create \
    --username "${AIRFLOW_ADMIN_USER}" \
    --firstname "${AIRFLOW_ADMIN_FIRSTNAME}" \
    --lastname "${AIRFLOW_ADMIN_LASTNAME}" \
    --role Admin \
    --email "${AIRFLOW_ADMIN_EMAIL}" \
    --password "${AIRFLOW_ADMIN_PASSWORD}" \
  || echo "Admin user create skipped (may already exist): ${AIRFLOW_ADMIN_USER}"
fi

 echo "Airflow init complete."