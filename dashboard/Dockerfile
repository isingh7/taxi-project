FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN pip install dash==2.17.1 plotly==5.22.0 requests==2.32.3 gunicorn==22.0.0
COPY dashboard ./dashboard
RUN useradd --create-home app
USER app
EXPOSE 8050
CMD ["gunicorn", "dashboard.app:server", "--bind", "0.0.0.0:8050", "--workers", "2", "--timeout", "120"]
