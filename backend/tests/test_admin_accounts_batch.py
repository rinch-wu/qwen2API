from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from backend.core.account_pool import Account
from backend.main import app


class DummyPool:
    def __init__(self, accounts):
        self.accounts = accounts
        self.saved = False

    async def save(self):
        self.saved = True


class DummyAuthResolver:
    async def refresh_token(self, acc):
        # 模拟登录成功获取 token（不启动真实浏览器）
        acc.token = f"mock-token-{acc.email}"
        acc.valid = True
        return True


def test_batch_import_accounts_adds_and_updates_accounts():
    with TestClient(app) as client:
        original_pool = app.state.account_pool
        dummy_pool = DummyPool([Account(email="exists@example.com", password="old-pass")])
        # 注入 mock auth_resolver，避免真实浏览器启动
        dummy_resolver = DummyAuthResolver()
        app.state.account_pool = dummy_pool
        app.state.qwen_client.auth_resolver = dummy_resolver
        app.state.qwen_executor.auth_resolver = dummy_resolver
        try:
            response = client.post(
                "/api/admin/accounts/batch",
                headers={"Authorization": "Bearer admin"},
                json={
                    "content": "exists@example.com:new-pass\nnew@example.com:new-user-pass\n",
                },
            )
        finally:
            app.state.account_pool = original_pool
            app.state.qwen_client.auth_resolver = original_pool and app.state.qwen_client.auth_resolver
            app.state.qwen_executor.auth_resolver = original_pool and app.state.qwen_executor.auth_resolver

    assert response.status_code == 200
    payload = response.json()

    assert payload["ok"] is True
    assert payload["added"] == 2
    assert payload["skipped"] == 0
    assert payload["failed"] == 0
    assert payload["errors"] == []

    exists = next(acc for acc in dummy_pool.accounts if acc.email == "exists@example.com")
    created = next(acc for acc in dummy_pool.accounts if acc.email == "new@example.com")

    assert exists.password == "new-pass"
    assert created.password == "new-user-pass"
    assert dummy_pool.saved is True


def test_batch_import_accounts_reports_invalid_lines():
    with TestClient(app) as client:
        original_pool = app.state.account_pool
        dummy_pool = DummyPool([])
        dummy_resolver = DummyAuthResolver()
        app.state.account_pool = dummy_pool
        app.state.qwen_client.auth_resolver = dummy_resolver
        app.state.qwen_executor.auth_resolver = dummy_resolver
        try:
            response = client.post(
                "/api/admin/accounts/batch",
                headers={"Authorization": "Bearer admin"},
                json={
                    "content": "bad-line\n\nmissing-password@example.com:\n",
                },
            )
        finally:
            app.state.account_pool = original_pool
            app.state.qwen_client.auth_resolver = original_pool and app.state.qwen_client.auth_resolver
            app.state.qwen_executor.auth_resolver = original_pool and app.state.qwen_executor.auth_resolver

    assert response.status_code == 200
    payload = response.json()

    assert payload["ok"] is True
    assert payload["added"] == 0
    assert payload["skipped"] == 0
    assert payload["failed"] == 2
    assert payload["errors"] == [
        {"line": 1, "error": "格式错误，需为 email:password"},
        {"line": 3, "error": "email 或 password 为空"},
    ]
    assert dummy_pool.saved is True
