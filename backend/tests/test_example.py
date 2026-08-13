import pytest


class TestExampleTDD:
    """
    Example test demonstrating TDD workflow.

    TDD Cycle:
    1. RED: Write failing test
    2. GREEN: Write minimal code to pass
    3. REFACTOR: Improve code while keeping tests green
    """

    def test_basic_math(self):
        """Example test - basic assertion."""
        assert 1 + 1 == 2

    def test_string_operations(self):
        """Example test - string operations."""
        result = "hello".upper()
        assert result == "HELLO"

    @pytest.mark.django_db
    def test_database_available(self):
        """Example test - database connection with custom User model."""
        from apps.core.models import User

        User.objects.create_user(email="test@example.com", password="password")
        assert User.objects.count() == 1


def calculate_discount(price: float, discount_percent: float) -> float:
    """
    Calculate discounted price.

    This function was created using TDD:
    1. First wrote tests (see below)
    2. Then implemented minimal code
    3. Refactored for clarity
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
    if not 0 <= discount_percent <= 100:
        raise ValueError("Discount must be between 0 and 100")

    discount_amount = price * (discount_percent / 100)
    return round(price - discount_amount, 2)


class TestCalculateDiscount:
    """Tests for calculate_discount function - TDD example."""

    def test_no_discount(self):
        """Test with 0% discount."""
        assert calculate_discount(100.0, 0) == 100.0

    def test_full_discount(self):
        """Test with 100% discount."""
        assert calculate_discount(100.0, 100) == 0.0

    def test_half_discount(self):
        """Test with 50% discount."""
        assert calculate_discount(100.0, 50) == 50.0

    def test_negative_price_raises_error(self):
        """Test that negative price raises ValueError."""
        with pytest.raises(ValueError, match="Price cannot be negative"):
            calculate_discount(-10.0, 10)

    def test_invalid_discount_raises_error(self):
        """Test that invalid discount raises ValueError."""
        with pytest.raises(ValueError, match="Discount must be between"):
            calculate_discount(100.0, 150)
