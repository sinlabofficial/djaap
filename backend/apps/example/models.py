from django.db import models

from apps.core.models import BaseModel


class Item(BaseModel):
    """Example model demonstrating BaseModel usage."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return self.name
