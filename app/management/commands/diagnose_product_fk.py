from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Read-only diagnostic for the CalculatorLead.product_id column-type "
        "mismatch behind the /admin/app/calculatorlead/ 500 error."
    )

    def handle(self, *args, **options):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type, udt_name "
                "FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = %s",
                ["app_calculatorlead", "product_id"],
            )
            lead_col = cur.fetchone()
            self.stdout.write(f"app_calculatorlead.product_id -> {lead_col}")

            cur.execute(
                "SELECT column_name, data_type, udt_name "
                "FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = %s",
                ["cars_vehicle", "id"],
            )
            vehicle_col = cur.fetchone()
            self.stdout.write(f"cars_vehicle.id -> {vehicle_col}")

            cur.execute(
                "SELECT conname, pg_get_constraintdef(oid) "
                "FROM pg_constraint "
                "WHERE conrelid = 'app_calculatorlead'::regclass AND contype = 'f'"
            )
            self.stdout.write(f"FK constraints on app_calculatorlead: {cur.fetchall()}")

            cur.execute(
                "SELECT COUNT(*) FROM app_calculatorlead WHERE product_id IS NOT NULL"
            )
            self.stdout.write(f"non-null product_id rows: {cur.fetchone()[0]}")

            cur.execute(
                "SELECT DISTINCT product_id FROM app_calculatorlead "
                "WHERE product_id IS NOT NULL LIMIT 20"
            )
            self.stdout.write(f"sample product_id values: {cur.fetchall()}")

            cur.execute(
                "SELECT COUNT(*) FROM app_calculatorlead "
                "WHERE product_id IS NOT NULL AND product_id !~ '^[0-9]+$'"
            )
            self.stdout.write(f"non-numeric product_id rows: {cur.fetchone()[0]}")
