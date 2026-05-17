# CommLab Glossary Trainer

Vocabulary practice app for the CommLab English glossary — 12 units, 444 terms.

![demo](media/comlab.webp)

## Features

- **Definition → Term**: given the definition, type the correct term  
  (graded instantly with exact/fuzzy string matching)
- **Term → Definition**: given the term, explain it in your own words  
  (graded by a local LLM via Ollama — rewards understanding over verbatim recall)
- Filter by unit or practice all units at once
- Spaced-repetition selector: unseen terms first, then weighted by score/speed/expiry
- Session stats (answered / correct / avg score / coverage)
- Study mode: browse cards grouped or mixed, term-first or definition-first
- Progress persisted in DuckDB (`progress.duckdb`)

---

## Running the application

### Step 1 — Install Ollama

Ollama runs the local AI model used for grading *Term → Definition* answers.

**macOS**

```bash
brew install ollama
ollama serve   # start the background service
```

Or download the desktop app from **https://ollama.com/download**.

**Windows**

Download and run the installer from **https://ollama.com/download**.  
Ollama installs as a system service and starts automatically.

**Linux**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve   # or: sudo systemctl enable --now ollama
```

Then pull the model (required for *Term → Definition* mode):

```bash
ollama pull mistral   # ~4 GB
```

---

### Step 2 — Install Docker

Download **Docker Desktop** from **https://www.docker.com/products/docker-desktop**  
(macOS and Windows — includes Compose).

On Linux, install the Docker Engine and the Compose plugin:

```bash
# example for Debian/Ubuntu
sudo apt-get install docker-ce docker-ce-cli docker-compose-plugin
```

---

### Step 3 — Run the container

**Create a `docker-compose.yml`** in any empty folder:

```yaml
services:
  comlab:
    image: mtdig/comlab:latest
    ports:
      - "9999:9999"
    environment:
      OLLAMA_HOST: "http://host.docker.internal:11434"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

> **Linux only** — `host.docker.internal` is not provided automatically.  
> Either replace it with your machine's LAN IP (`http://192.168.x.x:11434`),  
> or add `extra_hosts: ["host.docker.internal:host-gateway"]` to the service.

**Start it:**

```bash
docker compose up -d
```

Open **http://localhost:9999**.

To stop: `docker compose down`  
To update to a newer image: `docker compose pull && docker compose up -d`

---

## Development setup

> Only needed if you want to modify the source code.

**1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)**

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. Clone and install**

```bash
git clone https://github.com/mtdig/comlab.git
cd comlab
uv sync
```

**3. Run (with live reload)**

```bash
uv run comlab
```

**4. Run tests**

```bash
uv sync --group dev
uv run pytest
```

**Build the Docker image locally**

```bash
docker compose build
docker compose up
```

To change the model, edit `OLLAMA_MODEL` in `src/app/config.py`.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PORT` | `9999` | HTTP port the server listens on |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama API base URL |

`OLLAMA_MODEL` is set in `src/app/config.py` (default: `mistral`).

---

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/units` | List all units |
| `GET` | `/api/stats?unit=` | Stats by mode (optionally filtered by unit) |
| `GET` | `/api/weak_spots?limit=` | Lowest-scoring terms |
| `POST` | `/api/reset` | Delete all progress |

---

## Grading

**Definition → Term**: normalised string comparison with word-level fuzzy
matching for multi-word terms. Instant, no model required.

**Term → Definition**: Ollama grades the free-text answer (0–100) with
one-sentence feedback. Score ≥ 70 counts as correct. If Ollama is unavailable,
a keyword-overlap fallback is used.
