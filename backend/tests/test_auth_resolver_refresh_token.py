import pytest

from backend.core.account_pool import Account
from backend.services.auth_resolver import AuthResolver


class DummyPool:
    def __init__(self):
        self.saved = 0

    async def save(self):
        self.saved += 1


class _DummyPage:
    url = "https://chat.qwen.ai/auth"


class _DummyBrowser:
    def __init__(self, page):
        self._page = page

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def new_page(self):
        return self._page


@pytest.mark.asyncio
async def test_refresh_token_fails_when_old_and_new_tokens_both_empty(monkeypatch):
    pool = DummyPool()
    resolver = AuthResolver(pool)
    acc = Account(email="a@example.com", password="pw", token="")

    page = _DummyPage()
    monkeypatch.setattr("backend.services.auth_resolver._new_browser", lambda: _DummyBrowser(page))
    async def fake_login_and_get_token(*_args, **_kwargs):
        return ""

    monkeypatch.setattr("backend.services.auth_resolver._login_and_get_token", fake_login_and_get_token)

    ok = await resolver.refresh_token(acc)

    assert ok is False
    assert (acc.token or "") == ""
    assert acc.valid is False
    assert pool.saved == 0


@pytest.mark.asyncio
async def test_refresh_token_succeeds_when_non_empty_token_unchanged(monkeypatch):
    pool = DummyPool()
    resolver = AuthResolver(pool)
    existing = "tok-123"
    acc = Account(email="a@example.com", password="pw", token=existing)

    page = _DummyPage()
    monkeypatch.setattr("backend.services.auth_resolver._new_browser", lambda: _DummyBrowser(page))
    async def fake_login_and_get_token(*_args, **_kwargs):
        return existing

    monkeypatch.setattr("backend.services.auth_resolver._login_and_get_token", fake_login_and_get_token)

    ok = await resolver.refresh_token(acc)

    assert ok is True
    assert acc.token == existing
    assert acc.valid is True
