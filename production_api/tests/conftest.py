import pytest

@pytest.fixture(autouse=True)
def clear_local_rate_limit_between_independent_tests():
    import main
    with main.rate_lock:
        main.rate.clear()
