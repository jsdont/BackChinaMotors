import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cars", "0011_vehicle_engine_power_hp_vehicle_gearbox_and_more"),
        ("core", "0004_alter_user_role_bank_partner_serviceprovider"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="deal",
            name="client",
        ),
        migrations.AddField(
            model_name="deal",
            name="customer",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="deals_as_customer",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="deal",
            name="vehicle",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deals",
                to="cars.vehicle",
            ),
        ),
        migrations.AlterField(
            model_name="deal",
            name="manager",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="core.manager",
            ),
        ),
        migrations.AlterField(
            model_name="deal",
            name="title",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="deal",
            name="status",
            field=models.CharField(
                choices=[
                    ("AGREEMENT", "Согласование"),
                    ("CONTRACT", "Договор"),
                    ("PURCHASE_CHINA", "Покупка в Китае"),
                    ("DELIVERY_KZ", "Доставка в КЗ"),
                    ("SVH", "СВХ"),
                    ("CUSTOMS", "Таможня"),
                    ("DELIVERY_CLIENT", "Доставка клиенту"),
                    ("COMPLETED", "Завершена"),
                ],
                default="AGREEMENT",
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="DealAssignment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("BROKER", "Брокер (СВХ)"),
                            ("SVH", "СВХ"),
                            ("LAB", "Лаборатория"),
                            ("LOGISTIC", "Логист"),
                            ("DECLARANT", "Декларант (граница)"),
                            ("BANK", "Банк"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Ожидает"),
                            ("IN_PROGRESS", "В работе"),
                            ("DONE", "Завершено"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="deal_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="core.deal",
                    ),
                ),
            ],
            options={
                "unique_together": {("deal", "role")},
            },
        ),
    ]
