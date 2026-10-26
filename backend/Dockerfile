FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.11.14 && uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"
COPY app ./app
COPY tests ./tests
COPY migrations ./migrations
COPY alembic.ini ./
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
