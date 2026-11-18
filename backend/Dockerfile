FROM python:3.11-slim-bookworm@sha256:a83ba18aef0f865b1a4a611c2cf460fe446f2795673bbb9fe43be570439e3b39 AS builder
WORKDIR /build
COPY backend/requirements.lock ./requirements.lock
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir --no-compile --require-hashes -r requirements.lock && find /opt/venv -type d -name __pycache__ -exec rm -rf {} +

FROM python:3.11-slim-bookworm@sha256:a83ba18aef0f865b1a4a611c2cf460fe446f2795673bbb9fe43be570439e3b39 AS runtime
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY auth_service/main.py /app/auth_service/main.py
COPY task_service/main.py /app/task_service/main.py
USER 10001:10001
EXPOSE 8001 8002
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8001')+'/health',timeout=2)"
CMD ["uvicorn", "auth_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
