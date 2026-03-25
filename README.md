# TFT-Style Auto-Battler (COMP2116 submission)

This repository contains **only** the Teamfight Tactics–style auto-battler (“金铲铲”-style) game: shop, economy, augments, items, combat, and scoring. It is **not** the Snake or Mario demos from the same local workspace.

## Requirements

- Python 3.10+ (uses the standard library `tkinter` for the UI)
- Dependencies: see `requirements.txt` (`pytest` for running tests)

Install:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the game

From the **repository root** (this folder):

```bash
python -m src.tft_game
```

On first run, a high-score file may be created under `data/tft_highscores.json` (ignored by git).

## Demo / grading shortcuts (in-game)

- **F1** — Demo boost (for presentation)
- **F2** — Advance phase
- **F3** — Auto demo script

## Tests

```bash
pytest
```

## Project structure

| Path | Role |
|------|------|
| `src/tft_engine.py` | Rules: shop, pool, economy, battle, score |
| `src/tft_game.py` | Tkinter UI and game loop |
| `tests/test_tft_engine.py` | Unit tests for engine logic |

## Push to GitHub (only this folder)

1. On [GitHub](https://github.com/new), create a **new empty repository** (no README/license if you will push from local first).
2. In a terminal:

```bash
cd "/path/to/tft_github_only"
git init
git add .
git commit -m "Initial commit: TFT auto-battler (course project)"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your account and repo name. Use SSH if you prefer: `git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git`.

If GitHub already created a README on the web, use `git pull origin main --rebase` once before the first push, or create an empty repo without initializing files.

---

*Report-style documentation for grading: this README describes purpose, dependencies, how to run, tests, and repository layout.*
