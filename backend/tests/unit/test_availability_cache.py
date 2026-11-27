"""AvailabilityCache probes at most once per TTL, whatever the result (SC-008)."""

import asyncio

import pytest

from app.llm.base import AvailabilityCache
from app.llm.types import Availability


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class CountingProvider:
    """Only what the cache uses: ``check()``. Returns the queued results in order."""

    def __init__(self, *results: Availability) -> None:
        self._results = list(results) or [Availability(status="available")]
        self.probes = 0

    async def check(self) -> Availability:
        index = min(self.probes, len(self._results) - 1)
        self.probes += 1
        # Yield to the loop so concurrent callers really overlap with this probe.
        for _ in range(3):
            await asyncio.sleep(0)
        return self._results[index]


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


async def test_calls_inside_the_ttl_make_one_probe(clock: FakeClock) -> None:
    provider = CountingProvider()
    cache = AvailabilityCache(provider, clock=clock)

    first = await cache.get()
    clock.now += 59
    second = await cache.get()

    assert provider.probes == 1
    assert second is first


async def test_a_call_at_exactly_the_ttl_probes_again(clock: FakeClock) -> None:
    down = Availability(status="unavailable", reason="cannot reach ollama")
    provider = CountingProvider(Availability(status="available"), down)
    cache = AvailabilityCache(provider, clock=clock)

    await cache.get()
    clock.now += 60
    result = await cache.get()

    assert provider.probes == 2
    assert result == down


async def test_the_ttl_restarts_from_the_latest_probe(clock: FakeClock) -> None:
    provider = CountingProvider()
    cache = AvailabilityCache(provider, clock=clock)

    await cache.get()
    clock.now += 60
    await cache.get()
    clock.now += 59
    await cache.get()

    assert provider.probes == 2


async def test_unavailable_results_are_cached_too(clock: FakeClock) -> None:
    down = Availability(status="unavailable", reason="cannot reach ollama")
    provider = CountingProvider(down, Availability(status="available"))
    cache = AvailabilityCache(provider, clock=clock)

    await cache.get()
    clock.now += 30
    result = await cache.get()

    assert provider.probes == 1
    assert result == down


async def test_concurrent_calls_share_one_probe(clock: FakeClock) -> None:
    provider = CountingProvider()
    cache = AvailabilityCache(provider, clock=clock)

    results = await asyncio.gather(*(cache.get() for _ in range(5)))

    assert provider.probes == 1
    assert all(result is results[0] for result in results)


async def test_custom_ttl(clock: FakeClock) -> None:
    provider = CountingProvider()
    cache = AvailabilityCache(provider, ttl_seconds=5, clock=clock)

    await cache.get()
    clock.now += 4.9
    await cache.get()
    clock.now += 0.1
    await cache.get()

    assert provider.probes == 2


async def test_an_hour_of_refreshes_probes_at_most_60_times(clock: FakeClock) -> None:
    provider = CountingProvider()
    cache = AvailabilityCache(provider, clock=clock)

    # The web interface refreshes every 10 seconds (SC-008).
    for _ in range(360):
        await cache.get()
        clock.now += 10

    assert provider.probes == 60


def test_ttl_must_be_positive() -> None:
    with pytest.raises(ValueError):
        AvailabilityCache(CountingProvider(), ttl_seconds=0)
