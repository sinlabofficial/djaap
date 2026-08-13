
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates or updates a test user'

    def handle(self, *args, **options):
        try:
            user = User.all_objects.get(email='admin@example.com')
            user.set_password('admin')
            user.is_staff = True
            user.is_superuser = True
            user.deleted = None
            user.save()
            self.stdout.write(self.style.SUCCESS('Successfully updated superuser "admin"'))
        except User.DoesNotExist:
            User.objects.create_superuser('admin@example.com', 'admin', employee_id='admin')
            self.stdout.write(self.style.SUCCESS('Successfully created new superuser "admin"'))
