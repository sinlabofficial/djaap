"""Tests for API throttle module."""


from apps.api.throttle import CustomAnonRateThrottle, CustomUserRateThrottle


class TestCustomAnonRateThrottle:
    """Tests for CustomAnonRateThrottle."""

    def test_throttle_rate(self):
        """Test that anon throttle has correct rate."""
        throttle = CustomAnonRateThrottle()
        assert throttle.rate == "100/hour"


class TestCustomUserRateThrottle:
    """Tests for CustomUserRateThrottle."""

    def test_throttle_rate(self):
        """Test that user throttle has correct rate."""
        throttle = CustomUserRateThrottle()
        assert throttle.rate == "1000/hour"
