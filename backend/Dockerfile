FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# --- Development target ---
FROM base AS dev

COPY requirements/base.txt requirements/dev.txt ./requirements/
RUN pip install --no-cache-dir -r requirements/dev.txt

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- Production target ---
FROM base AS prod

COPY requirements/base.txt requirements/prod.txt ./requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .

RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app
USER app

EXPOSE 8000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "salescount.wsgi:application"]
