FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml requirements.lock ./
RUN python -c "import tomllib; deps = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; open('runtime-requirements.txt', 'w').write(chr(10).join(deps))" \
    && pip install -c requirements.lock -r runtime-requirements.txt

COPY app ./app
COPY migrations ./migrations

RUN useradd --create-home --uid 10001 brisamar \
    && mkdir -p /data/uploads \
    && chown -R brisamar /data
USER brisamar

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
