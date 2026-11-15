# Supabase setup (database for accounts, fields and plans)

Supabase is used only as the **Postgres database** behind Django. Login stays in Django
(JWT, `/api/token/`, `/api/register/`), so the frontend does not change and no Supabase key
goes into the browser.

## 1. Create the project (about 5 minutes)

1. Go to https://supabase.com, sign in and click **New project**.
   - Name: `safe-cycle`
   - Database password: click **Generate**, then **save it in your password manager**.
   - Region: **Europe (Paris or Frankfurt)**, the closest to Morocco.
2. Wait until the project is ready, then click **Connect** (top bar).
3. Under **Connection string**, choose **Session pooler** (it works on IPv4 networks). Copy the URI.
   It looks like:
   `postgresql://postgres.abcdxyz:[YOUR-PASSWORD]@aws-0-eu-west-3.pooler.supabase.com:5432/postgres`
4. Replace `[YOUR-PASSWORD]` with your database password. If the password has special
   characters, percent-encode them (`@` → `%40`, `#` → `%23`, `/` → `%2F`, `:` → `%3A`).
5. Add this line to `backend/.env` (gitignored, never commit it):
   ```
   DATABASE_URL=postgresql://postgres.abcdxyz:YOUR-PASSWORD@aws-0-eu-west-3.pooler.supabase.com:5432/postgres
   ```

## 2. Create the tables

```bash
cd backend
.venv/bin/pip install -r requirements.txt     # installs psycopg (Postgres driver)
.venv/bin/python manage.py migrate            # creates the tables + turns on RLS
.venv/bin/python manage.py createsuperuser    # your admin account for /admin/
```

`settings.py` uses Postgres when `DATABASE_URL` is set (SSL required, connections kept
60 s) and SQLite otherwise, so tests and local dev work without Supabase.

## 3. Check it

Check RLS from the Supabase **SQL Editor** (should return no rows):

```sql
select tablename from pg_tables where schemaname = 'public' and not rowsecurity;
```

Then open **Table Editor**:

| Table | What is in it | Filled today? |
|---|---|---|
| `auth_user` | the account (username, email, hashed password) | yes, via `POST /api/register/` |
| `farms_field` | the field location (latitude, longitude), linked to the user | yes, via `POST /api/fields/` (JWT) |
| `farms_result` | a saved plan, linked to the field | **not yet**: no endpoint writes it, and the web app has no login screen |

## Security

Django tables live in `public`, which Supabase's Data API (`anon`, `authenticated` roles)
can reach. Migration `farms/0002_enable_row_level_security` (PostgreSQL only):

- turns on row-level security on every table in `public`, with no policies, so the API
  roles see zero rows;
- revokes table privileges from `anon` and `authenticated` when those roles exist.

Django connects as `postgres`, the table owner, so it is not affected. Since
30 Oct 2026 Supabase also stops granting new `public` tables to the API roles, so this is
a second lock. Tables added by **later** migrations are not covered by 0002: run the SQL
check above after adding a model.

Never put the Supabase `service_role`/secret key or the database URL in the frontend.

## Why not Supabase Auth?

Django already has tested accounts and the rule "a user only ever sees their own data"
(`backend/farms/tests.py`, `IsolationTests`). Supabase Auth would mean a second login system,
supabase-js in the browser and rewriting those rules as Postgres policies. Using Supabase as
the database gives the hosted, visible database with no change to the app.
