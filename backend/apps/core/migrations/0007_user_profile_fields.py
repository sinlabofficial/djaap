from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_permission_deleted_permission_deleted_by_cascade_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="profile_name",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="user",
            name="profile_photo",
            field=models.FileField(blank=True, null=True, upload_to="profile_photos/"),
        ),
    ]
