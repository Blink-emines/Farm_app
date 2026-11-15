"""Lock the Django tables against Supabase's public Data API.

Supabase can expose every table in the `public` schema over its REST/GraphQL API
(roles `anon` and `authenticated`). Our app never uses that API: Django talks to
Postgres directly as the table owner. So we:

1. turn on row-level security (RLS) on every table in `public`, with no policies,
   which means the API roles see zero rows even if they get access;
2. revoke table privileges from `anon` and `authenticated` when those roles exist
   (they only exist on Supabase).

Django is not affected: it connects as `postgres`, the owner of the tables, and
owners bypass RLS unless FORCE ROW LEVEL SECURITY is set (we don't set it).

Runs only on PostgreSQL. On SQLite (tests, local dev) it does nothing.

Tables added by later migrations are not covered by this one. Supabase also
turns RLS on for new tables by default; check with:
    select tablename from pg_tables where schemaname = 'public' and not rowsecurity;
"""

from django.db import migrations

API_ROLES = ('anon', 'authenticated')


def public_tables(cursor):
    cursor.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    return [row[0] for row in cursor.fetchall()]


def existing_api_roles(cursor):
    cursor.execute('SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)', [list(API_ROLES)])
    return [row[0] for row in cursor.fetchall()]


def enable_rls(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return
    quote = schema_editor.quote_name
    with connection.cursor() as cursor:
        roles = existing_api_roles(cursor)
        for table in public_tables(cursor):
            cursor.execute(f'ALTER TABLE public.{quote(table)} ENABLE ROW LEVEL SECURITY')
            for role in roles:
                cursor.execute(f'REVOKE ALL ON TABLE public.{quote(table)} FROM {quote(role)}')


def disable_rls(apps, schema_editor):
    # Undo only the RLS switch; we do not hand privileges back to the API roles.
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return
    quote = schema_editor.quote_name
    with connection.cursor() as cursor:
        for table in public_tables(cursor):
            cursor.execute(f'ALTER TABLE public.{quote(table)} DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):

    # Run after every app that creates tables, so they all exist by now.
    dependencies = [
        ('farms', '0001_initial'),
        ('admin', '0003_logentry_add_action_flag_choices'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('sessions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
