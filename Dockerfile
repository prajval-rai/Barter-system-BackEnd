FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# ⛔ REMOVED: RUN python manage.py collectstatic --noinput
# collectstatic needs FIELD_ENCRYPTION_KEY / DATABASE_URL etc. at import time,
# but those env vars aren't available during the Docker build step — only at
# container runtime. So it's now run in CMD below, right before the server starts.

CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && python manage.py shell -c \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@gmail.com', 'Admin@1234')\" && daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application"]