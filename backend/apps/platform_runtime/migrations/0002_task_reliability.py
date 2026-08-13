import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("platform_runtime", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="runtimelog",
            name="attempt",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="runtimelog",
            name="idempotency_key",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="runtimelog",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("started", "Started"),
                    ("retrying", "Retrying"),
                    ("succeeded", "Succeeded"),
                    ("failed", "Failed"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="TaskIdempotency",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("task_name", models.CharField(max_length=255)),
                ("key", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("in_progress", "In progress"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        max_length=20,
                    ),
                ),
                ("task_result_id", models.CharField(max_length=64)),
            ],
        ),
        migrations.AddConstraint(
            model_name="taskidempotency",
            constraint=models.UniqueConstraint(
                fields=("task_name", "key"),
                name="platform_task_idempotency_unique",
            ),
        ),
    ]
