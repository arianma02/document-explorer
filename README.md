# Document Explorer

Upload PDFs or text files, explore connections between them, and inspect the source passages behind each match.

[Live demo](https://arianma02.github.io/document-explorer/) · [API docs](https://document-explorer.onrender.com/docs)

The demo uses a shared collection without accounts. Anyone can view or delete uploaded documents, so use public or sample material. The free Render backend sleeps after inactivity and can take about a minute to start on the next visit.

## How it works

1. FastAPI extracts text from an upload and splits it into passages, preserving PDF page numbers. Passages contain up to 150 words and are shortened when needed to fit the model's 256-token limit.
2. The `all-MiniLM-L6-v2` embedding model converts each passage into a vector of 384 numbers. ONNX Runtime runs the model on the backend. Extracted text, passage vectors and source locations are saved in PostgreSQL. Original files are not stored.
3. The backend compares passage vectors using cosine similarity. Each document pair receives the score of its **strongest passage match**.
4. The frontend displays these connections in a graph. Adjust the similarity threshold or select a connection to read the two matching passages and their page numbers.

A score of `0.99` describes that passage pair, not 99% similarity between entire documents. References and repeated text can dominate a match. The English embedding model measures related content, not factual agreement, and bibliography filtering is not implemented.

## Stack

- **Frontend:** React, TypeScript and Vite, with an SVG graph.
- **Backend:** Python, FastAPI, Psycopg, NumPy and ONNX Runtime.
- **Database:** PostgreSQL with Alembic migrations.
- **Deployment:** GitHub Pages → Render API → Neon PostgreSQL. GitHub Actions runs tests, lint, formatting and builds before publishing the frontend.

## Run locally

Requires Python 3.12+, Node.js 24 and Docker with Compose. The commands below use PowerShell.

```powershell
git clone https://github.com/arianma02/document-explorer.git
cd document-explorer
docker compose up -d --wait
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

On macOS/Linux, use `python3 -m venv .venv` and `source .venv/bin/activate` in place of the Windows virtual environment commands.

The first backend startup downloads the pinned model and tokenizer from Hugging Face into `backend/.models/` and verifies their SHA-256 checksums. Later startups use the cache. Document text is processed on the backend, not sent to an external model API.

In a second terminal, from the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open [localhost:5173](http://127.0.0.1:5173/). Vite forwards API requests to FastAPI on port 8000. Local API documentation is at [localhost:8000/docs](http://127.0.0.1:8000/docs).

The default database connection matches `compose.yaml` on port 5433. To use another PostgreSQL database, set the `DATABASE_URL` environment variable before running migrations and starting the backend. A separately hosted frontend uses `VITE_API_URL` at build time and needs its origin allowed in the backend's CORS configuration.

## Checks

With the virtual environment active and local PostgreSQL running, from `backend/`:

```powershell
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
```

Database tests create and drop isolated test databases. Model tests use the real embedding model and download it if it is not cached.

From `frontend/`:

```powershell
npm test
npm run lint
npm run format:check
npm run build
```

## Limits

- Text-based PDFs and UTF-8 `.txt` files only. Scanned PDFs need OCR, which is not included.
- Maximum upload size: 2 MiB and 100 passages per document.
- The graph compares the newest 20 documents. Older documents remain stored.
- Graph positions are for layout and do not represent similarity. Scores belong to connections.
