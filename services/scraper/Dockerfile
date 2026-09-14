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

RUN mkdir services
RUN mkdir services/scraper
RUN touch services/__init__.py services/scraper/__init__.py

COPY services/scraper/src/ services/scraper/src/

COPY services/shared/ services/shared/

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "services.scraper.src.main:app"]
