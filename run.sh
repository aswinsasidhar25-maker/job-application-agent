#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "venv not found — creating it and installing dependencies..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

if ! pgrep -x ollama >/dev/null; then
  echo "Starting Ollama in the background..."
  ollama serve >/tmp/ollama.log 2>&1 &
  sleep 2
fi

exec streamlit run app.py
