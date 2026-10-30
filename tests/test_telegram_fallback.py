"""Telegram 连通性预检与固定计时回退的单元测试"""
import socket
from unittest.mock import MagicMock

import pytest

from src.core import game_base
from src.core.game_base import MultiAppBase
from src.telegram_bridge_api_client import TelegramBridgeApiClient


def _make_client(**overrides):
    """构造一个启用状态的Telegram客户端配置"""
    cfg = {
        'enabled': True,
        'mode': 'telegram',
        'api_url': 'http://192.168.100.65:51151',
        'bot_token': 'dummy-token',
    }
    cfg.update(overrides)
    return TelegramBridgeApiClient(cfg)


def _make_executor(client):
    """绕过__init__构造执行器，只测与Telegram等待相关的逻辑"""
    executor = object.__new__(MultiAppBase)
    executor.telegram_bridge_client = client
    return executor


def _free_port() -> int:
    """占用再释放一个端口，得到一个大概率无人监听的端口号"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


# ===================== 配置与地址解析 =====================

def test_reachability_config_defaults():
    client = _make_client()
    assert client.reachability_check is True
    assert client.reachability_timeout == 3
    assert client.reachability_fallback_seconds == 1800


def test_reachability_config_overrides():
    client = _make_client(
        reachability_check=False,
        reachability_timeout=1.5,
        reachability_fallback_seconds=600,
    )
    assert client.reachability_check is False
    assert client.reachability_timeout == 1.5
    assert client.reachability_fallback_seconds == 600


@pytest.mark.parametrize('mode,api_url,expected', [
    ('telegram', 'http://192.168.100.65:51151', ('192.168.100.65', 51151)),
    ('telegram', 'https://api.telegram.org', ('api.telegram.org', 443)),
    ('telegram', 'http://api.telegram.org', ('api.telegram.org', 80)),
    ('telegram', '192.168.1.10:7000', ('192.168.1.10', 7000)),
    ('bridge', 'http://127.0.0.1:8080', ('127.0.0.1', 8080)),
])
def test_get_api_endpoint(mode, api_url, expected):
    client = _make_client(mode=mode, api_url=api_url)
    assert client.get_api_endpoint() == expected


def test_get_api_endpoint_empty():
    client = _make_client(api_url='')
    assert client.get_api_endpoint() == ('', 0)
    assert client.check_api_reachable() is False


# ===================== 连通性探测 =====================

def test_check_api_reachable_true():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        client = _make_client(api_url=f'http://127.0.0.1:{port}')
        assert client.check_api_reachable(timeout=2) is True
    finally:
        listener.close()


def test_check_api_reachable_false_for_closed_port():
    port = _free_port()
    client = _make_client(api_url=f'http://127.0.0.1:{port}')
    assert client.check_api_reachable(timeout=1) is False


def test_check_api_reachable_is_cached(monkeypatch):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        client = _make_client(api_url=f'http://127.0.0.1:{port}')
        assert client.check_api_reachable(timeout=2) is True

        # 缓存命中后不应再发起连接
        def boom(*args, **kwargs):
            raise AssertionError('不应重复探测')

        monkeypatch.setattr(socket, 'create_connection', boom)
        assert client.check_api_reachable() is True

        # force=True 时重新探测，此时连接失败
        assert client.check_api_reachable(force=True, timeout=1) is False
    finally:
        listener.close()


def test_reset_reachability_cache(monkeypatch):
    client = _make_client()
    client._reachable_cache = True
    client.reset_reachability_cache()
    assert client._reachable_cache is None


# ===================== 等待步骤回退逻辑 =====================

def _step():
    return {'type': 'wait_for_telegram_text', 'text': '崩坏三任务已全部完成', 'timeout': 1800}


def _waited_seconds(executor):
    """把_fixed_wait替换为记录调用参数的桩，避免真实等待"""
    record = {}

    def fake_fixed_wait(seconds, reason=''):
        record['seconds'] = seconds
        record['reason'] = reason

    executor._fixed_wait = fake_fixed_wait
    return record


def test_fallback_when_client_missing():
    executor = _make_executor(None)
    record = _waited_seconds(executor)
    step = _step()

    assert executor._step_wait_for_telegram_text(step) is True
    assert record['seconds'] == 1800
    assert step['_telegram_fallback'] is True


def test_fallback_when_client_not_enabled():
    client = _make_client(enabled=False)
    executor = _make_executor(client)
    record = _waited_seconds(executor)

    assert executor._step_wait_for_telegram_text(_step()) is True
    assert record['seconds'] == 1800


def test_fallback_when_api_unreachable():
    client = MagicMock()
    client.enabled = True
    client.reachability_check = True
    client.reachability_fallback_seconds = 1800
    client.check_api_reachable.return_value = False

    executor = _make_executor(client)
    record = _waited_seconds(executor)
    step = _step()

    assert executor._step_wait_for_telegram_text(step) is True
    client.check_api_reachable.assert_called_once()
    assert record['seconds'] == 1800
    assert step['_telegram_fallback'] is True


def test_fallback_seconds_from_config():
    client = MagicMock()
    client.enabled = True
    client.reachability_check = True
    client.reachability_fallback_seconds = 600
    client.check_api_reachable.return_value = False

    executor = _make_executor(client)
    record = _waited_seconds(executor)

    assert executor._step_wait_for_telegram_text(_step()) is True
    assert record['seconds'] == 600


def test_wait_uses_telegram_when_reachable():
    client = MagicMock()
    client.enabled = True
    client.reachability_check = True
    client.reachability_fallback_seconds = 1800
    client.check_api_reachable.return_value = True

    executor = _make_executor(client)
    record = _waited_seconds(executor)
    executor.wait_for_telegram_text = MagicMock(return_value={'text': '崩坏三任务已全部完成'})
    step = _step()

    assert executor._step_wait_for_telegram_text(step) is True
    client.check_api_reachable.assert_called_once()
    executor.wait_for_telegram_text.assert_called_once()
    assert 'seconds' not in record
    assert step['_result'] == {'text': '崩坏三任务已全部完成'}


def test_wait_returns_false_when_message_not_received():
    client = MagicMock()
    client.enabled = True
    client.reachability_check = True
    client.check_api_reachable.return_value = True

    executor = _make_executor(client)
    _waited_seconds(executor)
    executor.wait_for_telegram_text = MagicMock(return_value=None)

    assert executor._step_wait_for_telegram_text(_step()) is False


def test_reachability_check_disabled_skips_probe():
    client = MagicMock()
    client.enabled = True
    client.reachability_check = False

    executor = _make_executor(client)
    _waited_seconds(executor)
    executor.wait_for_telegram_text = MagicMock(return_value=None)

    assert executor._step_wait_for_telegram_text(_step()) is False
    client.check_api_reachable.assert_not_called()


def test_missing_text_fails_without_probe():
    client = MagicMock()
    client.enabled = True
    client.reachability_check = True

    executor = _make_executor(client)
    assert executor._step_wait_for_telegram_text({'type': 'wait_for_telegram_text'}) is False
    client.check_api_reachable.assert_not_called()


# ===================== 固定等待实现 =====================

def test_fixed_wait_sleeps_in_chunks(monkeypatch):
    sleeps = []
    monkeypatch.setattr(game_base.time, 'sleep', lambda s: sleeps.append(s))

    executor = _make_executor(None)
    executor._fixed_wait(150)

    assert sleeps == [60.0, 60.0, 30.0]


def test_fixed_wait_ignores_invalid_seconds(monkeypatch):
    sleeps = []
    monkeypatch.setattr(game_base.time, 'sleep', lambda s: sleeps.append(s))

    executor = _make_executor(None)
    executor._fixed_wait(0)

    assert sleeps == []
