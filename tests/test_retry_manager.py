import pytest
from src.core.retry_manager import RetryManager, with_retry

class DummyError(Exception):
    pass


def test_should_retry_flags():
    cfg = {
        'retry_on_timeout': True,
        'retry_on_image_not_found': False,
        'retry_on_network_error': True,
        'retry_on_game_error': False,
        'enabled': True,
        'max_retries': 2,
    }
    rm = RetryManager(cfg)
    assert rm.should_retry(Exception('timeout occurred'), 0) is True
    assert rm.should_retry(Exception('image not found'), 0) is False
    assert rm.should_retry(Exception('network failure'), 0) is True
    assert rm.should_retry(Exception('game launch error'), 0) is False
    # default fallback when no keyword matches
    assert rm.should_retry(Exception('unknown'), 0) is True


def test_calculate_delay_exponential():
    cfg = {'retry_delay': 5, 'backoff_factor': 2, 'max_delay_seconds': 30}
    rm = RetryManager(cfg)
    assert rm.calculate_delay(1) == 5
    assert rm.calculate_delay(2) == 10
    assert rm.calculate_delay(3) == 20
    # capped at max_delay_seconds
    assert rm.calculate_delay(4) == 30


def test_retry_decorator_success(mocker):
    call_order = []
    def flaky():
        call_order.append('call')
        if len(call_order) < 3:
            raise DummyError('fail')
        return 'ok'
    rm = RetryManager({'max_retries': 5, 'retry_delay': 0, 'backoff_factor': 1})
    decorated = rm.retry_decorator()(flaky)
    result = decorated()
    assert result == 'ok'
    assert len(call_order) == 3


def test_with_retry_strategy():
    @with_retry(strategy='quick')
    def func():
        return 'done'
    assert func() == 'done'
