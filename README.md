# Analogy Tutor

A chat-first AI learning assistant. It explains a topic Feynman-style, gives an
analogy from the student's favourite universe (cricket, Spider-Man, cooking...),
makes flashcards and a flowchart, then asks the student to teach it back and
scores the attempt.

**Stack:** React + Vite + Tailwind CSS, Python FastAPI + asyncpg, Neon
(serverless Postgres), Google Gemini (OpenAI-compatible endpoint), Mermaid.js,
WeasyPrint (PDF export).

---

## Quick start (recommended)

You need these installed first:

| Tool | Version | Get it |
|---|---|---|
| Python | 3.10 or newer | https://www.python.org/downloads/ (on Windows tick **Add Python to PATH**) |
| Node.js (includes npm) | 18 or newer | https://nodejs.org/ |
| Bash | any | WSL, **Git Bash** (comes with Git for Windows), Linux or macOS |

Then, from the project folder:

```bash
chmod +x setup.sh     # only needed once, and only on Linux/macOS/WSL
./setup.sh
```

The script does everything in order:

1. checks Python, Node and npm
2. creates `backend/.env` if it is missing (it asks for your Neon URL and Gemini key)
3. creates a virtualenv at `backend/.venv` and installs the backend packages
4. runs `npm install` in `frontend/`
5. applies the database migration to Neon (safe to re-run; it skips if already applied)
6. checks the database connection
7. starts the backend on http://localhost:8000 and the frontend on http://localhost:5173

When it prints the two URLs, open **http://localhost:5173**. Press `Ctrl+C` to stop both servers.

Other modes:

```bash
./setup.sh --setup-only   # install + migrate, don't start servers
./setup.sh --start-only   # just start the servers (after a previous setup)
./setup.sh --help
```

**Windows:** open *Git Bash* (or a WSL terminal) in the project folder and run `./setup.sh`.
Do not run it from PowerShell or cmd.

---

## Credentials expire in 24 hours

The `backend/.env` in this zip is pre-filled with a Neon connection string and a
Gemini API key. **Both are temporary and stop working after about 24 hours.**
When that happens:

1. Create a new Neon project (or reset the password) and copy the **pooled**
   connection string (the host contains `-pooler`).
2. Create a new key at https://aistudio.google.com/apikey.
3. Put them in `backend/.env` as `DATABASE_URL` and `LLM_API_KEY`
   (or delete `backend/.env` and run `./setup.sh` again; it will ask for them).
4. A brand-new Neon database is empty, so run `./setup.sh --setup-only` to apply the migration.

`backend/.env` is listed in `.gitignore`, so it won't be committed. Don't share
this zip publicly while it still contains live credentials.

---

## Manual setup (if you don't want to use the script)

### 1. Database (Neon)

1. Use the **pooled** connection string (host contains `-pooler`).
2. Put it in `backend/.env` as `DATABASE_URL` (copy `.env.example` to `backend/.env` as a template).
3. Apply the migration (either way works):
   ```bash
   cd backend
   python migrate.py                                   # no psql needed
   # or: psql "$DATABASE_URL" -f ../migrations/001_init.sql
   ```
4. Check the connection: `python verify_db.py`

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Git Bash on Windows: source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.api:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

`VITE_API_BASE` defaults to `http://localhost:8000`. Copy `frontend/.env.example`
to `frontend/.env` to change it.

---

## Project layout

```
analogy-tutor/
├── README.md
├── setup.sh                     # one-shot setup + launcher
├── .env.example                 # template for backend/.env
├── .gitignore
├── migrations/001_init.sql      # database schema
├── backend/
│   ├── .env                     # your secrets (pre-filled, gitignored)
│   ├── requirements.txt
│   ├── Dockerfile               # deploy target (installs Pango for WeasyPrint)
│   ├── migrate.py               # applies the migration (no psql needed)
│   ├── verify_db.py             # checks the Neon connection
│   ├── pytest.ini
│   ├── app/
│   │   ├── config.py            # env vars
│   │   ├── db.py                # asyncpg pool + pending-write queue
│   │   ├── llm_client.py        # the ONLY module that talks to Gemini
│   │   ├── messages.py          # backend user-facing strings
│   │   ├── prompts.py           # orchestrator + tool prompts
│   │   ├── schemas.py           # pydantic schemas for tool JSON
│   │   ├── tools.py             # extract_subconcepts, generate_*, evaluate_analogy
│   │   ├── orchestrator.py      # tool-calling loop
│   │   ├── export_pdf.py        # WeasyPrint session PDF
│   │   └── api.py               # FastAPI endpoints
│   └── tests/test_tools.py
└── frontend/
    ├── package.json, vite.config.js, tailwind.config.js, postcss.config.js, index.html
    └── src/
        ├── App.jsx, main.jsx, styles.css, ui.js
        ├── locale/en.js         # all user-facing strings
        ├── api/client.js        # fetch wrapper
        ├── store/storage.js     # localStorage cache + retry queue
        └── components/          # Sidebar, ChatPane, Message, Markdown, Flashcards,
                                 # MermaidChart, MemeCards, TeachBackCard, Composer,
                                 # ThinkingIndicator, Onboarding, SettingsModal, PrivacyModal
```

## Environment variables (`backend/.env`)

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | none | Neon **pooled** connection string |
| `LLM_API_KEY` | none | Google AI Studio key |
| `LLM_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai` | Gemini's OpenAI-compatible endpoint |
| `LLM_MODEL` | `gemini-2.5-flash` | |
| `LLM_MIN_INTERVAL_MS` | `6000` | Minimum gap between LLM calls. The Gemini free tier allows roughly 10 requests/minute, and one topic turn makes 5 to 6 calls. Lower it if your quota is higher. |
| `SESSION_IDLE_MINUTES` | `30` | Idle sessions end automatically |
| `EXPORT_DIR` | `static/exports` | Where PDFs are written |
| `FRONTEND_ORIGIN` | `*` | CORS origin |

Frontend: `VITE_API_BASE` (default `http://localhost:8000`) in `frontend/.env`.

## How a topic turn works

`extract_subconcepts` -> the model writes the Feynman explanation ->
`generate_analogy` -> `generate_flashcards` -> `generate_mermaid` (only when the
sub-concepts form a sequence) -> the student teaches back -> `evaluate_analogy`.

The rating band is computed in code, never by the model: coverage of at least
80% **and** correct relationships = Strong; coverage of at least 40% = Partial;
anything lower = Needs work. Meme cards are generated once per new topic.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Python 3.10+ not found` | Install Python and make sure it is on your PATH, then open a new terminal. |
| `python3-venv` error on WSL/Ubuntu | `sudo apt install python3-venv` |
| `./setup.sh: Permission denied` | `chmod +x setup.sh` |
| `bad interpreter` or `\r` errors | The file got Windows line endings. Run `sed -i 's/\r$//' setup.sh` and try again. |
| Migration or DB check fails | The Neon credentials have probably expired (see above), or the URL isn't the pooled one. |
| Every reply says "I'm having trouble right now" | The Gemini key is wrong or expired, or you hit the free-tier rate limit. Wait a minute and retry. |
| "Export PDF" fails on Windows | WeasyPrint needs the GTK/Pango runtime, which Windows doesn't ship. Everything else still works. Run the backend in WSL or Docker for PDF export. |
| Port 8000 or 5173 already in use | Stop whatever is using it, or change the port in `setup.sh`. |

## Tests

```bash
cd backend
source .venv/bin/activate     # Git Bash on Windows: source .venv/Scripts/activate
pytest
```

## Deployment

- **Backend:** Render, Railway or Fly.io using `backend/Dockerfile` (it installs
  the system libraries WeasyPrint needs). Set `DATABASE_URL`, `LLM_API_KEY`,
  `LLM_BASE_URL`, `LLM_MODEL`, `LLM_MIN_INTERVAL_MS`. The container honours `$PORT`.
- **Frontend:** Vercel (framework: Vite) with `VITE_API_BASE` pointing at the backend URL.
- Run the migration once before the first boot.

## Privacy

Data is kept until the student deletes it. `DELETE /profiles/{id}` removes the
profile and, through `ON DELETE CASCADE`, every session, message, evaluation and
asset. There are no analytics tables and no trackers. The "What we store" dialog
in the sidebar explains this in the app.
