import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _reset_throttles():
    """The login endpoint is rate-limited (10/min); tests sign in many times."""
    cache.clear()
    yield
