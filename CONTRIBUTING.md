# 🤝 Contributing to Flow-Studio (Google Flow AI Studio)

First off, thank you for considering contributing to **Flow-Studio**! 🎉 Projects like this thrive because of people like you who dedicate their time to building, testing, documenting, and improving developer tools for the open-source community.

Please read through these guidelines to ensure a smooth, productive, and collaborative contribution process.

---

## 📑 Table of Contents

1. [Code of Conduct](#-code-of-conduct)
2. [How Can I Contribute?](#-how-can-i-contribute)
   - [Reporting Bugs](#reporting-bugs)
   - [Suggesting Features & New Models](#suggesting-features--new-models)
   - [Improving Documentation](#improving-documentation)
   - [Submitting Pull Requests](#submitting-pull-requests)
3. [Development Setup](#-development-setup)
   - [Local Environment](#local-environment)
   - [Installing Dependencies](#installing-dependencies)
   - [Running the Web Studio & CLI Locally](#running-the-web-studio--cli-locally)
4. [Architecture & Codebase Overview](#-architecture--codebase-overview)
5. [Coding & Style Guidelines](#-coding--style-guidelines)
   - [Python Standards](#python-standards)
   - [Frontend Standards](#frontend-standards)
   - [Commit Message Conventions](#commit-message-conventions)
6. [Security & Privacy](#-security--privacy)

---

## 📜 Code of Conduct

By participating in this project, you agree to uphold a welcoming, respectful, and harassment-free environment for everyone, regardless of experience level, background, or identity. Treat fellow contributors with kindness, empathy, and professional respect.

---

## 💡 How Can I Contribute?

### Reporting Bugs

Encountered an issue or unexpected error? Please check existing GitHub Issues before submitting a new one.

When opening a bug report, include:
- **Clear Title**: Brief summary of the bug.
- **Environment**: OS (Windows / Linux / macOS), Python version, browser version (if Web UI).
- **Reproduction Steps**: Exact commands or Web UI interactions that trigger the bug.
- **Expected vs. Actual Behavior**: What should have happened vs. what actually occurred.
- **Error Logs**: Terminal traceback or browser DevTools console output (remove any personal cookies or sensitive tokens before pasting).

### Suggesting Features & New Models

Google Flow frequently updates its models (Imagen, Veo, Gemini Omni) and RPC endpoints. If you notice new models or features on `flow.google.com`:
- Describe the feature or model (Model name, badge, token cost, aspect ratios).
- If possible, provide network inspect snippets showing the RPC ID or payload structure.
- Explain the real-world use case.

### Improving Documentation

Documentation improvements are always welcome! This includes:
- Clarifying setup instructions.
- Fixing typos or grammatical errors.
- Adding code examples for CLI automation scripts.
- Translating guides into different languages.

---

## 🛠️ Development Setup

### Local Environment

1. **Fork the repository** on GitHub to your personal account.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/<your-username>/Flow-Studio.git
   cd Flow-Studio
   ```
3. **Add upstream remote** to keep your branch updated:
   ```bash
   git remote add upstream https://github.com/NePreby/Flow-Studio.git
   ```

### Installing Dependencies

Create an isolated virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

*(Optional) If working on browser automation components in `flow_worker.py`:*
```bash
playwright install chromium
```

### Running the Web Studio & CLI Locally

- **Run Web Studio:**
  ```bash
  python -m uvicorn app:app --host 127.0.0.1 --port 7860 --reload
  ```
  Open `http://localhost:7860` in your browser.

- **Test CLI Commands:**
  ```bash
  # Check credits
  python cli.py credits

  # List models
  python cli.py models
  ```

---

## 🏛️ Architecture & Codebase Overview

Before making edits, familiarize yourself with the primary components:

| File / Directory | Purpose |
| :--- | :--- |
| `flow_client.py` | Core engine reverse-engineering Google Flow's `/batchexecute` RPCs (`nzlxg`, `DviW9c`, `ogiZ0b`, etc.). |
| `flow_worker.py` | Playwright-based headless browser automation worker for direct canvas interactions. |
| `app.py` | FastAPI server exposing RESTful endpoints (`/api/generate/image`, `/api/generate/video`, etc.). |
| `cli.py` | Command-line interface with `argparse`, colored terminal outputs, and parameter validation. |
| `config.py` | Configuration manager handling `config.json` loading, path management, and cookie storage. |
| `web/index.html` | Single-page Web Studio dashboard built with TailwindCSS, Alpine.js, and FontAwesome. |
| `downloads/` | Default directory for saving generated media. |

---

## 📐 Coding & Style Guidelines

### Python Standards

- Follow **PEP 8** style guidelines.
- Use explicit type annotations where appropriate (`typing.Dict`, `typing.Optional`, `typing.List`).
- Ensure async safety: use `asyncio.to_thread` for blocking I/O calls inside FastAPI route handlers.
- Handle Windows compatibility (e.g. `WindowsProactorEventLoopPolicy` and UTF-8 console encoding).
- Avoid silent error suppression: log exceptions meaningfully and return structured JSON responses with `{"success": False, "error": "..."}`.

### Frontend Standards

- Keep `web/index.html` responsive, clean, and styled with TailwindCSS utility classes.
- Use Alpine.js reactive components (`x-data`, `x-init`, `x-model`) instead of heavy external frameworks.
- Preserve the modern dark-mode aesthetic (`#090d16` background with blue/purple glow accents).

### Commit Message Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Adds a new feature or model (e.g., `feat: add support for Veo 3.1 4K resolution`)
- `fix:` Fixes a bug (e.g., `fix: resolve credit status parsing error on RPC DviW9c`)
- `docs:` Documentation only changes (e.g., `docs: update setup instructions in README`)
- `refactor:` Code changes that neither fix a bug nor add a feature (e.g., `refactor: modularize RPC payload builder`)
- `style:` Formatting, missing semi-colons, whitespace fixes
- `perf:` Performance improvements

---

## 🚀 Submitting Pull Requests

1. **Create a new branch** from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Make your changes** cleanly with appropriate tests and documentation.
3. **Verify locally**: Test both CLI commands and Web UI functionality.
4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: your concise commit summary"
   ```
5. **Push to your fork**:
   ```bash
   git push origin feat/your-feature-name
   ```
6. **Open a Pull Request (PR)** against the `main` branch of `NePreby/Flow-Studio`.
   - Provide a clear summary of what was added or fixed.
   - Attach screenshots or terminal output if visual or CLI changes were made.
   - Reference any related issues (e.g., `Fixes #12`).

---

## 🔒 Security & Privacy

- **Never commit active cookies, passwords, or authentication tokens** to Git.
- Always verify that `config.json` is listed in `.gitignore` before committing.
- If you discover a security vulnerability or exploit, please disclose it responsibly by opening a private security advisory or contacting the repository owner directly.

---

Thank you for helping make **Flow-Studio** better for everyone! 🚀
