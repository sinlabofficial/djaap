from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("platform_runtime", "0002_task_reliability"),
    ]

    operations = [
        migrations.AddField(
            model_name="runtimelog",
            name="correlation_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=255,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="runtimelog",
            name="duration_ms",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="runtimelog",
            name="event_type",
            field=models.CharField(default="task", max_length=100),
        ),
        migrations.AddField(
            model_name="runtimelog",
            name="severity",
            field=models.CharField(db_index=True, default="info", max_length=20),
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
                    ("timeout", "Timeout"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
    ]
