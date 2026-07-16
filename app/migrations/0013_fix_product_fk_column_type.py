# On production the product_id column and its FK constraint were never
# migrated when CalculatorLead.product switched from an old catalog.Product
# (varchar PK) to cars.Vehicle (bigint PK) -- 0012 only updated Django's
# migration state, the real column stayed varchar with a stale FK pointing
# at the long-gone catalog_product table. That mismatch made Postgres
# reject any query joining CalculatorLead to Vehicle (admin changelist,
# product filter) with "operator does not exist: character varying = bigint".
#
# Fresh installs never hit this: 0005 already declares product as a
# ForeignKey to cars.Vehicle, so the column is bigint from the start. This
# migration only acts when it finds the old varchar column for real.
from django.db import migrations


def fix_product_fk(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'app_calculatorlead' AND column_name = 'product_id'"
        )
        data_type = cursor.fetchone()[0]
        if data_type != "character varying":
            return

        cursor.execute(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'app_calculatorlead'::regclass "
            "AND contype = 'f' AND conname LIKE 'app_calculatorlead_product_id%%'"
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                f'ALTER TABLE app_calculatorlead DROP CONSTRAINT "{row[0]}"'
            )

        # Any index on the varchar column (plain btree + the _like/
        # varchar_pattern_ops one Django adds for indexed CharFields) has to
        # go before the type change -- varchar_pattern_ops rejects bigint.
        cursor.execute(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'app_calculatorlead' AND indexdef LIKE '%%(product_id%%'"
        )
        for (indexname,) in cursor.fetchall():
            cursor.execute(f'DROP INDEX "{indexname}"')

        # Old catalog.Product ids that no longer match a real cars_vehicle
        # row (e.g. left over from before the switch) become NULL instead
        # of blocking the type conversion or the new FK below.
        cursor.execute(
            "UPDATE app_calculatorlead SET product_id = NULL "
            "WHERE product_id IS NOT NULL "
            "AND product_id !~ '^[0-9]+$'"
        )
        cursor.execute(
            "UPDATE app_calculatorlead SET product_id = NULL "
            "WHERE product_id IS NOT NULL "
            "AND product_id::bigint NOT IN (SELECT id FROM cars_vehicle)"
        )

        cursor.execute(
            "ALTER TABLE app_calculatorlead "
            "ALTER COLUMN product_id TYPE bigint USING product_id::bigint"
        )
        cursor.execute(
            "ALTER TABLE app_calculatorlead "
            "ADD CONSTRAINT app_calculatorlead_product_id_fk_cars_vehicle_id "
            "FOREIGN KEY (product_id) REFERENCES cars_vehicle(id) "
            "DEFERRABLE INITIALLY DEFERRED"
        )
        cursor.execute(
            "CREATE INDEX app_calculatorlead_product_id_idx "
            "ON app_calculatorlead (product_id)"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0012_alter_calculatorlead_product"),
        ("cars", "0013_vehicle_remove_name_and_max_speed_add_category_city_price_kzt"),
    ]

    operations = [
        migrations.RunPython(fix_product_fk, migrations.RunPython.noop),
    ]
