FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install poetry && poetry self add poetry-plugin-export

COPY pyproject.toml poetry.lock ./

RUN poetry export -f requirements.txt --output requirements.txt --without dev --without-hashes

FROM python:3.13-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY ./src/ /app/

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app

USER appuser
# Expose the port your app runs on (default for FastAPI is 8000)
EXPOSE 8000

# Command to run the application using gunicorn as a process manager for uvicorn
# This is the production-grade command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "jobscraper.api.api:app"]
