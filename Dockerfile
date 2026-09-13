FROM node:24-alpine AS web-builder
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production
WORKDIR /app
RUN apt-get update \
    && apt-get upgrade --yes \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system commerce \
    && adduser --system --ingroup commerce commerce
COPY pyproject.toml README.md ./
COPY app/ app/
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY alembic/ alembic/
COPY data/seeds/ data/seeds/
COPY scripts/ scripts/
COPY --from=web-builder /build/web/dist web/dist
USER commerce
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
