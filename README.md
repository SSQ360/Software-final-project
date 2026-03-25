# TFT-Style Auto-Battler (COMP2116 submission)

This repository contains **only** a Teamfight Tactics-style auto-battler game: shop, economy, augments, items, combat, and scoring. It is **not** the Snake or Mario demos from the same local workspace.

## Game overview

You play a simplified TFT-style loop: **Planning** (buy and place units, roll the shop, buy XP, equip items) and **Combat** (automatic fights vs AI opponents). You must **place at least one unit on the board** before starting a battle.

- **Champions** have **traits** (e.g. Bruiser, Arcanist, Sniper). Enough copies of the same trait unlock **synergy bonuses** (extra HP or attack for your team).
- **Shop odds** depend on your **level**; higher levels roll more expensive units. A **shared champion pool** limits how many copies of each unit exist in the game—buying them removes them from the pool.
- **Stars**: three copies of the same 1-star unit merge into 2-star; three 2-stars merge into 3-star, with stronger stats.
- **Gold** pays for shop purchases, **rerolls** (2g), and **XP** (4g). **Interest** gives extra gold based on your bank (capped; some augments raise the cap). **Win/lose streaks** and round results affect income.
- **Items** (base components and combined items) boost attack and HP. **Augments** are pick-one bonuses that change economy or combat.
- **Opponents** are bots with their own HP. When your HP hits zero, the run ends. The game computes a **final score** and tracks a **local best score** in `data/tft_highscores.json`.

The UI is built with **Tkinter** (`window title: COMP2116 — TFT Style Auto-Battler`). Use **F1 / F2 / F3** during demos or grading (see below).

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
