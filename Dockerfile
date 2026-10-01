FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Зависимости ставятся отдельным слоем — пересборка кода не переустанавливает пакеты.
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv==0.12.13 \
    && uv pip install --system --no-cache -r pyproject.toml

COPY alembic.ini ./
COPY app ./app
COPY scripts ./scripts

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
