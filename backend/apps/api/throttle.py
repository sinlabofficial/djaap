from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class CustomAnonRateThrottle(AnonRateThrottle):
    """Custom throttle for anonymous users."""
    rate = "100/hour"


class CustomUserRateThrottle(UserRateThrottle):
    """Custom throttle for authenticated users."""
    rate = "1000/hour"
