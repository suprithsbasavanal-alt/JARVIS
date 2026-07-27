FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

FROM python:3.11-slim as runner

WORKDIR /app

RUN groupadd -r jarvis && useradd -r -g jarvis jarvis

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=jarvis:jarvis src/ ./src/
COPY --chown=jarvis:jarvis config/ ./config/

USER jarvis

EXPOSE 8000 8001

CMD ["python", "-m", "src.backend.bootstrap.main"]
