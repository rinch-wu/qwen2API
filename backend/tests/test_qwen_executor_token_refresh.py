import pytest

from backend.upstream.qwen_executor import QwenExecutor


class DummyAccount:
    def __init__(self, email="user@example.com", password="pass", token=""):
        self.email = email
        self.password = password
        self.token = token
        self.valid = True
        self.activation_pending = False
        self.status_code = "valid"
        self.last_error = ""
        self.healing = False


class DummyPool:
    def __init__(self):
        self.released = []
        self.invalid_marked = []

    def release(self, acc):
        self.released.append(acc.email)

    def mark_invalid(self, acc, reason="invalid", error_message=""):
        acc.valid = False
        acc.status_code = reason
        acc.last_error = error_message
        self.invalid_marked.append((acc.email, reason, error_message))

    def mark_rate_limited(self, acc, cooldown=None, error_message=""):
        pass


class DummyAuthResolver:
    def __init__(self, refresh_results):
        self.refresh_results = list(refresh_results)
        self.refresh_calls = 0
        self.auto_heal_calls = 0

    async def refresh_token(self, acc):
        self.refresh_calls += 1
        result = self.refresh_results.pop(0) if self.refresh_results else False
        if result and not acc.token:
            acc.token = "fresh-token"
        return result

    async def auto_heal_account(self, acc):
        self.auto_heal_calls += 1


@pytest.mark.asyncio
async def test_fixed_account_missing_token_refreshes_before_create_chat():
    pool = DummyPool()
    executor = QwenExecutor(engine=object(), account_pool=pool)
    resolver = DummyAuthResolver([True])
    executor.auth_resolver = resolver

    acc = DummyAccount(token="")
    calls = []

    async def fake_create_chat(token, model):
        calls.append((token, model))
        return "chat-1"

    async def fake_stream(token, chat_id, model, content, has_custom_tools=False, files=None):
        yield {"type": "delta", "phase": "answer", "content": "ok"}

    executor.create_chat = fake_create_chat
    executor.stream = fake_stream

    items = []
    async for item in executor.chat_stream_events_with_retry(
        model="qwen-plus",
        content="hello",
        fixed_account=acc,
    ):
        items.append(item)

    assert resolver.refresh_calls == 1
    assert calls == [("fresh-token", "qwen-plus")]
    assert items[0]["type"] == "meta"
    assert items[1]["type"] == "event"


@pytest.mark.asyncio
async def test_fixed_account_unauthorized_triggers_heal_and_retry_once():
    pool = DummyPool()
    executor = QwenExecutor(engine=object(), account_pool=pool)
    resolver = DummyAuthResolver([True])
    executor.auth_resolver = resolver

    acc = DummyAccount(token="stale-token")
    call_tokens = []

    async def fake_create_chat(token, model):
        call_tokens.append(token)
        if len(call_tokens) == 1:
            raise Exception("unauthorized: create_chat HTTP 401")
        return "chat-2"

    async def fake_stream(token, chat_id, model, content, has_custom_tools=False, files=None):
        yield {"type": "delta", "phase": "answer", "content": "ok"}

    executor.create_chat = fake_create_chat
    executor.stream = fake_stream

    # Ensure refreshed token is distinguishable for second attempt
    async def refresh_with_new_token(account):
        resolver.refresh_calls += 1
        account.token = "refreshed-token"
        return True

    resolver.refresh_token = refresh_with_new_token

    items = []
    async for item in executor.chat_stream_events_with_retry(
        model="qwen-plus",
        content="hello",
        fixed_account=acc,
    ):
        items.append(item)

    assert call_tokens == ["stale-token", "refreshed-token"]
    assert len(pool.invalid_marked) == 1
    assert pool.invalid_marked[0][1] == "auth_error"
    assert resolver.auto_heal_calls == 0
    # release happens at higher-level runtime cleanup after execution completes
    assert pool.released == []
    assert items[0]["type"] == "meta"
    assert items[1]["type"] == "event"
