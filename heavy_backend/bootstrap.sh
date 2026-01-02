#!/usr/bin/env bash
set -euo pipefail
WORKDIR=/opt/heavy_backend
VENV_DIR=/opt/venvs/rag_env
APP_USER=ubuntu  # change as needed

# 1) update & prerequisites
apt-get update
apt-get install -y software-properties-common build-essential curl git wget unzip

# 2) add deadsnakes for Python 3.11
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# 3) create user folder & venv
mkdir -p $WORKDIR
mkdir -p $(dirname $VENV_DIR)
python3.11 -m venv $VENV_DIR
$VENV_DIR/bin/pip install --upgrade pip

# 4) copy your app files to /opt/heavy_backend (assumes you scp or git clone)
# Example: (you will run this locally) scp -r heavy_backend/* ubuntu@EC2_IP:/opt/heavy_backend/
# On the instance continue with:
cd $WORKDIR

# 5) install requirements
$VENV_DIR/bin/pip install wheel
$VENV_DIR/bin/pip install -r requirements.txt

# 6) ensure .env exists (create secure placeholder)
if [ ! -f $WORKDIR/.env ]; then
  cat > $WORKDIR/.env <<EOF
# Fill these in manually (do not commit)
GEMINI_API_KEY=***
PINECONE_API_KEY=***
INDEX_NAME=chatbot-rag
FORWARDER_TOKEN=super-secret-forwarder-token-placeholder
MODEL_CACHE_DIR=/opt/models
PORT=8000
LOG_LEVEL=info
EOF
  chown $APP_USER:$APP_USER $WORKDIR/.env
fi

# 7) create systemd unit (copy the file to /etc/systemd/system)
cat > /etc/systemd/system/myrag.service <<'UNIT'
[Unit]
Description=Prepsphere RAG FastAPI service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/heavy_backend
EnvironmentFile=/opt/heavy_backend/.env
ExecStart=/opt/venvs/rag_env/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 120
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

# 8) enable and start
systemctl daemon-reload
systemctl enable myrag.service
systemctl start myrag.service

echo "Bootstrap finished. Service status:"
systemctl status myrag.service --no-pager
