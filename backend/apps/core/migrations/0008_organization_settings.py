import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_user_profile_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizationSettings",
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
                (
                    "key",
                    models.CharField(
                        default="default",
                        editable=False,
                        max_length=20,
                        unique=True,
                    ),
                ),
                ("organization_name", models.CharField(default="djaapp", max_length=150)),
                ("logo", models.FileField(blank=True, null=True, upload_to="organization/")),
                ("description", models.TextField(blank=True)),
                ("address", models.TextField(blank=True)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("email", models.EmailField(blank=True, max_length=254)),
            ],
            options={
                "verbose_name": "organization settings",
                "verbose_name_plural": "organization settings",
            },
        ),
    ]
