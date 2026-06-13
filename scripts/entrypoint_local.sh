#!/bin/bash
set -e
airflow db init
airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin123 || true
exec airflow webserver -p 8080
