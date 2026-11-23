# Imagen de la aplicación Medimagen (Flask + gunicorn)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Primero las dependencias (se reutiliza la capa si requirements.txt no cambia)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY my-app/ .

# Usuario sin privilegios; solo puede escribir en /app/logs
RUN useradd --system --no-create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app/logs
USER appuser

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5001/salud', timeout=3).status == 200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "3", "--timeout", "30", "app:app"]
