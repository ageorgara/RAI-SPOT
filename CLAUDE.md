what # CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RAI Cafe** (formerly CollabHub) is an AI-powered team-formation platform for research collaborations. It helps researchers find collaborators and uses Claude AI to recommend optimal team compositions for projects.

## Running the Application

```bash
# Install dependencies
pip install -r requirements

# Set up environment variables
cp .env .env.local  # then add ANTHROPIC_API_KEY

# Seed the database with demo data
python seed.py

# Run the Flask dev server (port 5000)
python app.py
```

Demo credentials after seeding: `admin@collabhub.io / admin` (admin), or any of the 5 approved users with password `password`.

## Architecture

Single-file Flask application with server-side rendering.

- **`app.py`** — All routes and business logic (444 lines). No blueprints; everything lives here.
- **`models.py`** — SQLAlchemy models: `User`, `Project`, `Bid`, `Message`, `AIRecommendation`
- **`seed.py`** — Demo data population
- **`templates/`** — Jinja2 templates with Tailwind CSS (CDN), dark theme, fixed sidebar layout

Database is SQLite at `instance/collabhub.db`, auto-created on first run.

## Key Flows

**User lifecycle**: Register → pending → admin approves/rejects → approved users can bid on projects

**Project modes**:
- `public`: visible to all; users bid; AI recommends from bidders when project is closed
- `private`: only owner sees; AI recommends from all approved users immediately on creation

**AI recommendations** (`_run_ai_recommendation()`, app.py ~line 298):
- Calls Anthropic API directly via `requests` (not the SDK)
- Uses `claude-sonnet-4-20250514`
- Returns 1-2 teams of 2-4 people as JSON
- Result cached in `AIRecommendation` table
- Triggered on: private project creation, public project closure, manual re-run

## Environment Variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session secret |
| `ANTHROPIC_API_KEY` | Required for AI recommendations |

## No Test Infrastructure

There are no tests, no Makefile, no CI/CD. This is an intentional prototype setup.