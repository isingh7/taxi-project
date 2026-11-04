# Backend API image (also used for the one-off ETL task on ECS).
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY manage.py ./
COPY taxi_project ./taxi_project
COPY taxi_api ./taxi_api
RUN useradd --create-home app && chown -R app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/health/')"
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn taxi_project.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]
