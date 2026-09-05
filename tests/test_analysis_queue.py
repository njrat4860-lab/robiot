import asyncio

import pytest

from bot.analysis_queue import AnalysisQueue, QUEUE_DUPLICATE, QUEUE_FULL

CAPACITY = 2


async def _silent(position):
    return None


@pytest.mark.asyncio
async def test_first_entry_starts_immediately():
    queue = AnalysisQueue()
    entry = await queue.enqueue(1, CAPACITY, _silent)
    assert await asyncio.wait_for(entry.wait_turn(), 0.1) is True
    await queue.release(entry)


@pytest.mark.asyncio
async def test_second_entry_waits_until_first_is_released():
    queue = AnalysisQueue()
    first = await queue.enqueue(1, CAPACITY, _silent)
    second = await queue.enqueue(2, CAPACITY, _silent)
    assert await queue.position(2) == 1
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(second.wait_turn(), 0.05)
    await queue.release(first)
    assert await asyncio.wait_for(second.wait_turn(), 0.1) is True
    await queue.release(second)


@pytest.mark.asyncio
async def test_queue_rejects_over_capacity_and_duplicates():
    queue = AnalysisQueue()
    first = await queue.enqueue(1, CAPACITY, _silent)
    await queue.enqueue(2, CAPACITY, _silent)
    assert await queue.enqueue(3, CAPACITY, _silent) == QUEUE_FULL
    assert await queue.enqueue(1, CAPACITY, _silent) == QUEUE_DUPLICATE
    await queue.release(first)


@pytest.mark.asyncio
async def test_cancelled_entry_does_not_get_its_turn():
    queue = AnalysisQueue()
    first = await queue.enqueue(1, CAPACITY, _silent)
    second = await queue.enqueue(2, CAPACITY, _silent)
    assert await queue.cancel(2) is True
    assert await asyncio.wait_for(second.wait_turn(), 0.1) is False
    await queue.release(second)
    await queue.release(first)
    assert await queue.position(2) is None


@pytest.mark.asyncio
async def test_waiting_users_receive_new_positions():
    queue = AnalysisQueue()
    seen = []

    async def record(position):
        seen.append(position)

    first = await queue.enqueue(1, 3, _silent)
    await queue.enqueue(2, 3, _silent)
    await queue.enqueue(3, 3, record)
    await queue.release(first)
    assert seen == [1]


@pytest.mark.asyncio
async def test_running_entry_cannot_be_cancelled():
    queue = AnalysisQueue()
    entry = await queue.enqueue(1, CAPACITY, _silent)
    assert await entry.wait_turn() is True
    assert await queue.cancel(1) is False
    await queue.release(entry)
