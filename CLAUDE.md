# Farm App

Each user logs in and adds their farm fields (name, latitude, longitude). The
backend fetches daily weather for each field from the free **NASA POWER API**
(`community=AG`, daily temperature + rainfall, no API key needed), analyses it
with **pandas** (e.g. rainfall this month vs average, number of heat days), and
the frontends show the results as charts.

**Golden rule: every user sees ONLY their own data.** Every query that touches
Field / Measurement / Result must be filtered by the logged-in user.

## Stack (do not change without asking the user)

| Folder     | Tech                                                                     |
|------------|--------------------------------------------------------------------------|
| `backend/` | Django + Django REST Framework + pandas, SQLite, JWT via djangorestframework-simplejwt |
| `web/`     | React + Vite, charts with Recharts                                       |
| `mobile/`  | Expo (React Native), same API — built LAST                               |

Secrets live in `backend/.env` (gitignored). `.env.example` documents the keys.

## Data model (planned)

- **User**: Django's user model
- **Field**: `owner` (FK User), name, latitude, longitude
- **Measurement**: FK Field, date, temperature, rainfall (from NASA POWER)
- **Result**: FK Field, analysis output from pandas

## Build order (one layer at a time)

1. Project setup + this file
2. Django models (User, Field, Measurement, Result) + admin
3. JWT login + per-user data isolation, with a test proving user A cannot see user B's data
4. Script: fetch NASA POWER data per field → Measurements
5. pandas analysis → Results + `/api/results/`
6. React web: sign up, login, add fields, result charts
7. Expo mobile app, same screens
8. Explain deployment (never deploy without asking)

## Working rules

- The user is a **beginner who wants to understand**. Act as a mentor:
  - Before each layer: explain WHAT and WHY in simple words with an everyday analogy, then the plan.
  - Before every terminal command: one line saying what it does.
  - For every new file: 1-3 sentences on its role.
  - When asked "why?", explain the reasoning, not just the code.
- If a tool is missing (venv, Node.js…), give the exact install command and wait.
- Test-driven development where it makes sense (tests first).
- Review each layer with a code-reviewer agent before finishing it.
- After each layer: 5-line summary, how to run/see it, 3 check questions,
  a git commit, then **STOP until the user types "next"**.
- Never skip ahead or build several layers at once.

## Commands

Run from `backend/` (first time: `python3 -m venv .venv`, then copy
`.env.example` to `backend/.env` and set a secret key).

| What                          | Command                                          |
|-------------------------------|--------------------------------------------------|
| Install libraries             | `.venv/bin/pip install -r requirements.txt`      |
| Build/update database tables  | `.venv/bin/python manage.py migrate`             |
| Run tests                     | `.venv/bin/python manage.py test`                |
| Create an admin login         | `.venv/bin/python manage.py createsuperuser`     |
| Start the server (admin at http://127.0.0.1:8000/admin/) | `.venv/bin/python manage.py runserver` |

### API endpoints

All need the header `Authorization: Bearer <access token>` except the first three.

| Endpoint                    | What it does                                        |
|-----------------------------|-----------------------------------------------------|
| `POST /api/register/`       | Sign up (`username`, `password`)                    |
| `POST /api/token/`          | Log in → `access` + `refresh` tokens                |
| `POST /api/token/refresh/`  | Swap a `refresh` token for a new `access` token     |
| `/api/fields/`              | List / create / edit / delete your own fields       |
| `GET /api/measurements/`    | Read weather measurements of your own fields        |
