from django import forms

from .models import Item


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": (
                        "mt-2 block min-h-12 w-full rounded-lg border border-outline "
                        "bg-surface-container-lowest px-4 text-base text-on-surface "
                        "placeholder:text-on-surface-variant/60 focus:border-primary "
                        "focus:outline-none focus:ring-2 focus:ring-primary/20"
                    ),
                    "placeholder": "e.g. Customer onboarding",
                    "autocomplete": "off",
                    "aria-describedby": "name-hint",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": (
                        "mt-2 block min-h-36 w-full resize-y rounded-lg border border-outline "
                        "bg-surface-container-lowest px-4 py-3 text-base leading-6 text-on-surface "
                        "placeholder:text-on-surface-variant/60 focus:border-primary "
                        "focus:outline-none focus:ring-2 focus:ring-primary/20"
                    ),
                    "placeholder": "Add a short description to help your team understand this item.",
                    "rows": 5,
                    "aria-describedby": "description-hint",
                }
            ),
        }
