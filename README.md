<div align="center">

<img src="assets/gitsage-banner.jpg" alt="GitSage" width="640"/>

# GitSage

**A self-hosted Git interface with AI-powered commit messages and error diagnosis**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-pytest-yellow?style=flat-square&logo=pytest)](tests/)

</div>

---

## What is GitSage?

GitSage is a locally-hosted web UI for Git, built on FastAPI and HTMX. It gives you a clean browser-based dashboard for your daily Git workflow, staging files, committing, branching, and syncing with remotes, without memorising terminal commands.

The standout feature is its deep integration with **Google Gemini AI**:

- **AI Commit Writer** — analyses your staged diff and writes a Conventional Commits-style message in one click.
- **AI Error Medic** — when a Git operation fails, it captures the error, explains the root cause in plain language, and (where safe) offers an auto-fix button.

Everything runs on your machine. No data leaves your environment except the calls you explicitly make to the Gemini API.

---

## Features

| Category | Feature |
|----------|---------|
| Status | Visual file status with staged / unstaged / untracked grouping |
| Staging | Stage or unstage individual files, or stage all at once |
| Commits | Write and commit with a single click; view history with author and date |
| AI | Generate commit messages from staged diff (Gemini) |
| AI | Diagnose Git errors with step-by-step remediation |
| Branches | List, create, switch, and delete local branches |
| Remotes | Fetch, pull, and push to configured remotes |
| Security | All subprocess calls use list arguments, no shell injection surface |

---

## Quick Start

**Requirements:** Python 3.11+, Git

```bash
# Clone
git clone https://github.com/yourname/gitsage.git
cd gitsage

# Install and start
./scripts/setup.sh
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

For development mode (auto-reload + API docs at `/api/docs`):

```bash
./scripts/setup.sh --dev
```

---

## Configuration

Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | _(empty)_ | Google Gemini API key. Get one at [aistudio.google.com](https://aistudio.google.com/). AI features are disabled when not set. |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model name |
| `DEFAULT_REPO_PATH` | `.` | Absolute path of the repository to manage |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Enable auto-reload and API docs |
| `MAX_DIFF_BYTES` | `50000` | Max bytes of diff forwarded to AI |

---

## Running Tests

```bash
./scripts/run_tests.sh          # full suite with coverage report
./scripts/run_tests.sh --fast   # fast run, no coverage
```

Or directly:

```bash
pytest tests/ -v
```

---

## Project Structure

```
gitsage/
├── main.py                        # Application entry point
├── .env.example                   # Configuration template
├── requirements.txt
├── pyproject.toml                 # Pytest and coverage config
│
├── app/
│   ├── api/                       # FastAPI route handlers
│   │   ├── status.py              # Staging and repo status
│   │   ├── commits.py             # Commit and log
│   │   ├── branches.py            # Branch management
│   │   ├── remotes.py             # Remote operations
│   │   └── ai.py                  # AI endpoints
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── exceptions.py          # Custom exception types
│   │   └── git_runner.py          # Git subprocess executor
│   └── services/
│       ├── status_service.py
│       ├── commit_service.py
│       ├── branch_service.py
│       ├── remote_service.py
│       └── ai_service.py          # Gemini integration
│
├── frontend/
│   ├── templates/index.html       # Main page (HTMX + Tailwind)
│   └── static/
│       ├── css/app.css
│       └── js/app.js
│
├── tests/
│   ├── conftest.py                # Shared fixtures (temp git repo)
│   ├── unit/
│   │   └── test_validation.py     # Validation and sanitisation logic
│   └── integration/
│       └── test_api.py            # API endpoint tests
│
└── scripts/
    ├── setup.sh                   # Install and run
    └── run_tests.sh               # Test runner
```

---

## Security

GitSage is designed for local use only. Key decisions:

- `TrustedHostMiddleware` restricts access to `localhost` / `127.0.0.1` only.
- Git commands are executed with a list of arguments (`shell=False`) — no shell injection is possible.
- The repository path is validated and canonicalised on every request; `..` traversal is rejected.
- Credential prompts are disabled via `GIT_TERMINAL_PROMPT=0`. Git credentials come from your system's credential store, never from GitSage.
- AI-suggested auto-fix commands are validated against a whitelist of known-safe patterns before being presented to the user.
- Commit messages are sanitised to strip control characters before being passed to git.
- The Gemini API key is read from the environment and never logged or surfaced in API responses.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Uvicorn |
| AI | Google Gemini API (via httpx) |
| Frontend | HTMX, Tailwind CSS |
| Config | pydantic-settings |
| Testing | pytest, pytest-asyncio, pytest-cov |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Write tests for new behaviour
4. Open a pull request

---

## License

MIT — see [LICENSE](LICENSE).