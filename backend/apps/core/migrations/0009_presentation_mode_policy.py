from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_organization_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationsettings",
            name="mobile_presentation_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="organizationsettings",
            name="presentation_mode",
            field=models.CharField(
                choices=[
                    ("default", "Default"),
                    ("dashboard", "Dashboard"),
                    ("mobile", "Mobile"),
                ],
                default="default",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="role",
            name="presentation_mode_policy",
            field=models.CharField(
                choices=[
                    ("default", "Default"),
                    ("dashboard", "Dashboard"),
                    ("mobile", "Mobile"),
                ],
                default="default",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="presentation_mode",
            field=models.CharField(
                choices=[
                    ("default", "Default"),
                    ("dashboard", "Dashboard"),
                    ("mobile", "Mobile"),
                ],
                default="default",
                max_length=20,
            ),
        ),
    ]
