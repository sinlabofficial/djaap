import factory

from apps.core.models import User


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating test users with custom User model."""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")

    @factory.post_generation
    def set_password(self, create, extracted, **kwargs):
        self.set_password("testpass123")
        if create:
            self.save()
