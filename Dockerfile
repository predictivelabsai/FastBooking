FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    DEPLOY_MODE=monolith \
    HOST=0.0.0.0 \
    PORT=5023

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system fastbooking \
    && adduser --system --ingroup fastbooking fastbooking

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R fastbooking:fastbooking /app

USER fastbooking

EXPOSE 5023
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail http://127.0.0.1:5023/healthz || exit 1

CMD ["sh", "-c", "alembic upgrade head && python -m app.main_monolith"]
