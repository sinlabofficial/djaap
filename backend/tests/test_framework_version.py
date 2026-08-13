import django


def test_runtime_uses_django_61():
    assert django.VERSION[:2] == (6, 1)
