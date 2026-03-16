#!/bin/sh

# Function to check PostgreSQL availability
# Helper to get the first non-empty environment variable
get_env() {
    for var in "$@"; do
        eval "value=\${$var:-}"
        if [ -n "$value" ]; then
            printf '%s\n' "$value"
            return 0
        fi
    done

    return 1
}

check_postgres() {
    db_host=$(get_env PGHOST)
    db_host=${db_host:-localhost}
    db_port=$(get_env PGPORT)
    db_port=${db_port:-5432}
    db_user=$(get_env PGUSER POSTGRES_USER)
    db_name=$(get_env PGDATABASE POSTGRES_DB)
    db_pass=$(get_env PGPASSWORD POSTGRES_PASSWORD)

    "${VIRTUAL_ENV:-/opt/venv}/bin/python" - "$db_host" "$db_port" "$db_user" "$db_name" "$db_pass" <<'PY' >/dev/null 2>&1
import sys

import psycopg2

host, port, user, dbname, password = sys.argv[1:]

conn = psycopg2.connect(
    host=host,
    port=int(port),
    user=user,
    dbname=dbname,
    password=password,
    connect_timeout=1,
)
conn.close()
PY
}


# Wait for PostgreSQL to become available
until check_postgres; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - continuing..."

# run sql commands
# psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -f /app/backend/init-postgis.sql

# Apply Django migrations
${VIRTUAL_ENV:-/opt/venv}/bin/python manage.py migrate

# Create superuser if environment variables are set and there are no users present at all.
if [ -n "$DJANGO_ADMIN_USERNAME" ] && [ -n "$DJANGO_ADMIN_PASSWORD" ] && [ -n "$DJANGO_ADMIN_EMAIL" ]; then
  echo "Creating superuser..."
  ${VIRTUAL_ENV:-/opt/venv}/bin/python manage.py shell << EOF
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()

# Check if the user already exists
if not User.objects.filter(username='$DJANGO_ADMIN_USERNAME').exists():
    # Create the superuser
    superuser = User.objects.create_superuser(
        username='$DJANGO_ADMIN_USERNAME',
        email='$DJANGO_ADMIN_EMAIL',
        password='$DJANGO_ADMIN_PASSWORD'
    )
    print("Superuser created successfully.")

    # Create the EmailAddress object for AllAuth
    EmailAddress.objects.create(
        user=superuser,
        email='$DJANGO_ADMIN_EMAIL',
        verified=True,
        primary=True
    )
    print("EmailAddress object created successfully for AllAuth.")
else:
    print("Superuser already exists.")
EOF
fi


# Sync the countries and world travel regions
# Sync the countries and world travel regions
${VIRTUAL_ENV:-/opt/venv}/bin/python manage.py download-countries
if [ $? -eq 137 ]; then
  >&2 echo "WARNING: The download-countries command was interrupted. This is likely due to lack of memory allocated to the container or the host. Please try again with more memory."
  exit 1
fi

cat /code/voyage.txt

exec "$@"
