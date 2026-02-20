FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHON_JULIAPKG_PROJECT=/opt/graphbees_runtime/juliapkg \
    JULIA_DEPOT_PATH=/opt/graphbees_runtime/julia_depot \
    GRAPHBEES_RUNTIME_DIR=/opt/graphbees_runtime

WORKDIR /app

RUN mkdir -p /opt/graphbees_runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN python - <<'PY'
from app.julia_bridge.runner import init_julialg
init_julialg()
print("Julia dependencies initialized")
PY

EXPOSE 8501

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "streamlit run app/main.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.fileWatcherType=none"]
