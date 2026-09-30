FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN useradd --create-home --uid 10001 internfly
COPY pyproject.toml README.md ./
COPY internfly ./internfly
COPY data ./data
RUN pip install --no-cache-dir .
USER internfly
EXPOSE 8000
CMD ["uvicorn", "internfly.api:app", "--host", "0.0.0.0", "--port", "8000"]

