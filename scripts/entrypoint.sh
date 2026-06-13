#!/bin/bash
set -e
mkdir -p /home/airflow/logs /home/airflow/plugins
airflow db init
airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin123 || true
exec airflow webserver -p ${PORT:-8080}
