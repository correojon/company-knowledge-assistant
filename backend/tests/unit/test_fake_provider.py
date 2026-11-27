"""FakeProvider is deterministic, does no I/O, and honours the LLMProvider contract."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.llm.base import LLMProvider
from app.llm.fake import DEFAULT_REPLY, FakeProvider
from app.llm.types import Availability, ChatMessage, Completion, LLMProviderError

HELLO = [ChatMessage(role="user", content="Hello")]


async def _collect(provider: FakeProvider, messages: list[ChatMessage]) -> list[str]:
    return [chunk async for chunk in provider.stream(messages)]


def test_fake_provider_satisfies_the_protocol() -> None:
    provider: LLMProvider = FakeProvider()

    assert provider.name == "fake"
    assert provider.model == "fake"


async def test_default_reply() -> None:
    completion = await FakeProvider().complete(HELLO)

    assert DEFAULT_REPLY == "This is a canned reply from the fake provider."
    assert completion == Completion(text=DEFAULT_REPLY, model="fake", provider="fake")


async def test_custom_replies_cycle_in_order() -> None:
    provider = FakeProvider(["one", "two"])

    texts = [(await provider.complete(HELLO)).text for _ in range(5)]

    assert texts == ["one", "two", "one", "two", "one"]


async def test_complete_and_stream_share_one_cycle() -> None:
    provider = FakeProvider(["first", "second", "third"])

    first = (await provider.complete(HELLO)).text
    second = "".join(await _collect(provider, HELLO))
    third = (await provider.complete(HELLO)).text

    assert [first, second, third] == ["first", "second", "third"]


async def test_stream_advances_the_cycle_when_called_not_when_iterated() -> None:
    provider = FakeProvider(["first", "second"])

    pending = provider.stream(HELLO)
    completion = await provider.complete(HELLO)

    assert completion.text == "second"
    assert "".join([chunk async for chunk in pending]) == "first"


@pytest.mark.parametrize(
    "reply",
    [
        DEFAULT_REPLY,
        "  leading and trailing  ",
        "tabs\tand\nnew lines\r\n  mixed",
        "single",
        "",
    ],
)
async def test_stream_chunks_join_to_exactly_the_reply(reply: str) -> None:
    provider = FakeProvider([reply])

    chunks = await _collect(provider, HELLO)

    assert "".join(chunks) == reply
    assert "".join(chunks) == (await provider.complete(HELLO)).text


async def test_stream_yields_more_than_one_chunk_for_several_words() -> None:
    chunks = await _collect(FakeProvider(), HELLO)

    assert len(chunks) == len(DEFAULT_REPLY.split())


async def test_calls_record_the_messages_of_each_call() -> None:
    provider = FakeProvider()
    second = [
        ChatMessage(role="system", content="Be brief."),
        ChatMessage(role="user", content="Hi again"),
    ]

    await provider.complete(HELLO)
    await _collect(provider, second)

    assert provider.calls == [HELLO, second]


async def test_calls_are_copies_of_the_callers_list() -> None:
    provider = FakeProvider()
    messages = list(HELLO)

    await provider.complete(messages)
    messages.append(ChatMessage(role="assistant", content="later"))

    assert provider.calls == [HELLO]


async def test_check_reports_available() -> None:
    before = datetime.now(UTC)

    availability = await FakeProvider().check()

    assert availability.status == "available"
    assert availability.reason is None
    assert availability.checked_at.tzinfo is not None
    assert before <= availability.checked_at <= datetime.now(UTC)


async def test_check_does_not_advance_the_cycle_or_record_a_call() -> None:
    provider = FakeProvider(["first", "second"])

    await provider.check()

    assert provider.calls == []
    assert (await provider.complete(HELLO)).text == "first"


async def _run_script(provider: FakeProvider) -> list[str]:
    outputs = [(await provider.complete(HELLO)).text]
    outputs.append("".join(await _collect(provider, HELLO)))
    outputs.append((await provider.complete(HELLO)).text)
    return outputs


async def test_fresh_instances_are_deterministic() -> None:
    replies = ["alpha beta", "gamma"]

    assert await _run_script(FakeProvider(replies)) == await _run_script(
        FakeProvider(replies)
    )


def test_empty_replies_are_rejected() -> None:
    with pytest.raises(ValueError):
        FakeProvider([])


def test_unavailable_requires_a_reason() -> None:
    with pytest.raises(ValidationError):
        Availability(status="unavailable", reason=None)


def test_available_has_no_reason() -> None:
    with pytest.raises(ValidationError):
        Availability(status="available", reason="should not be here")


def test_checked_at_is_converted_to_utc() -> None:
    cet = timezone(timedelta(hours=1))
    local = datetime(2026, 1, 1, 13, 0, tzinfo=cet)

    availability = Availability(status="available", checked_at=local)

    assert availability.checked_at == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert availability.checked_at.utcoffset() == timedelta(0)


def test_checked_at_rejects_naive_datetimes() -> None:
    with pytest.raises(ValidationError):
        Availability(status="available", checked_at=datetime(2026, 1, 1, 12, 0))


@pytest.mark.parametrize("role", ["tool", "", "USER"])
def test_chat_message_rejects_unknown_roles(role: str) -> None:
    with pytest.raises(ValidationError):
        ChatMessage(role=role, content="x")


def test_completion_rejects_unknown_providers() -> None:
    with pytest.raises(ValidationError):
        Completion(text="x", model="m", provider="banana")


def test_llm_provider_error_carries_its_reason() -> None:
    error = LLMProviderError("Ollama at http://localhost:11434 timed out")

    assert error.reason == "Ollama at http://localhost:11434 timed out"
    assert str(error) == error.reason
