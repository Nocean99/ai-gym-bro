# AI Gym Bro

A workout tracker with a conversational assistant. You log training by typing the way you would text a friend, and the assistant records the sets, keeps the context of the session and answers questions about your history.

## What it does

- **Natural-language logging.** "Did 3 sets of 8 on bench at 185" becomes structured sets in the database.
- **Session memory.** The exercise carries across messages, so "another set of 6" is logged against the right lift.
- **History and summaries.** Recaps by day or period, with totals for cardio minutes, volume lifted and reps.
- **Personal records.** New bests are detected when a set is logged.
- **Cautious recommendations.** Suggested weights take declining reps into account instead of always increasing the load.

## Stack

| Layer | Technology |
|---|---|
| API | Python, Flask, Gunicorn |
| Language model | OpenAI API |
| Database | PostgreSQL |
| Mobile client | Flutter |
| Hosting | Render |

## API

| Method | Route | Purpose |
|---|---|---|
| POST | `/register` | Create an account |
| POST | `/login` | Sign in |
| POST | `/chat` | Send a message: log a workout or ask a question |
| GET | `/history` | Workout history for a user and period |
| DELETE | `/delete-set` | Remove a logged set |
| GET | `/health` | Service check |

## Running the backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then fill in your own values
psql "$DATABASE_URL" -f database/schema.sql
psql "$DATABASE_URL" -f database/migration_001_conversation_memory.sql

gunicorn --chdir backend api_server:app
```

You need your own OpenAI API key and a PostgreSQL database. Keys belong in `.env`, which is ignored by Git.

## Tests

The scripts in `tests/` are integration checks. They call a running local server and the OpenAI API, so they need the backend up and a key in the environment.

## Layout

```
backend/     Flask API, workout logic, conversation memory
database/    Schema and migrations
mobile/      Flutter client
tests/       Integration scripts
```

## Status

A personal project built in late 2025. It was developed with AI coding assistants, and the commit history shows which commits were agent-authored.
