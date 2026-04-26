# Running the App

## One-time setup

```bash
cd ~/job-application-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ollama pull llama3.2
```

## Every time you want to run the app

**Terminal 1 — Ollama:**
```bash
ollama serve
```

**Terminal 2 — the app:**
```bash
cd ~/job-application-agent
source venv/bin/activate
streamlit run app.py
```

Open `http://localhost:8501`. Stop with `Ctrl+C` in each terminal.

## One-liner (single terminal)

Starts Ollama in the background if it isn't already running, then launches the app:

```bash
cd ~/job-application-agent && source venv/bin/activate && (pgrep -x ollama >/dev/null || ollama serve &) && streamlit run app.py
```

Or just use the helper script:

```bash
./run.sh
```

## Reset the database

Wipes all jobs, profile, and cache:

```bash
rm ~/job-application-agent/data/app.db
```
