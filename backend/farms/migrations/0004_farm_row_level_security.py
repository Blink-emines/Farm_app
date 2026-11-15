"""Lock the new farms_farm table against Supabase's Data API (same rule as 0002).

PostgreSQL only; does nothing on SQLite.
"""

from django.db import migrations

TABLE = 'farms_farm'
API_ROLES = ('anon', 'authenticated')


def enable_rls(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return
    table = schema_editor.quote_name(TABLE)
    with connection.cursor() as cursor:
        cursor.execute(f'ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY')
        cursor.execute('SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)', [list(API_ROLES)])
        for (role,) in cursor.fetchall():
            cursor.execute(f'REVOKE ALL ON TABLE public.{table} FROM {schema_editor.quote_name(role)}')


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'ALTER TABLE public.{schema_editor.quote_name(TABLE)} DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):

    dependencies = [('farms', '0003_farm_and_field_area')]

    operations = [migrations.RunPython(enable_rls, disable_rls)]
