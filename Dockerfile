FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
COPY migrations ./migrations

RUN pip install --no-cache-dir .

# No default; the Kubernetes manifest sets `command:` to one of the
# scripts/run_*.py entrypoints.
CMD ["python", "scripts/run_collector.py"]
