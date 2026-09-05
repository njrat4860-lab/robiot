import asyncio

QUEUE_FULL = "full"
QUEUE_DUPLICATE = "duplicate"


class QueueEntry:
    def __init__(self, user_id, on_position):
        self.user_id = user_id
        self.on_position = on_position
        self.cancelled = False
        self.started = False
        self._turn = asyncio.Event()

    async def wait_turn(self):
        await self._turn.wait()
        if self.cancelled:
            return False
        self.started = True
        return True

    def grant(self):
        self._turn.set()

    def cancel(self):
        self.cancelled = True
        self._turn.set()


class AnalysisQueue:
    def __init__(self):
        self._entries = []
        self._lock = asyncio.Lock()

    async def enqueue(self, user_id, capacity, on_position):
        async with self._lock:
            if any(entry.user_id == user_id for entry in self._entries):
                return QUEUE_DUPLICATE
            if len(self._entries) >= capacity:
                return QUEUE_FULL
            entry = QueueEntry(user_id, on_position)
            self._entries.append(entry)
            if len(self._entries) == 1:
                entry.grant()
            return entry

    async def release(self, entry):
        async with self._lock:
            if entry in self._entries:
                self._entries.remove(entry)
            head = self._entries[0] if self._entries else None
            waiting = list(self._entries)
        if head is not None:
            head.grant()
        await _notify_positions(waiting)

    async def cancel(self, user_id):
        async with self._lock:
            entry = next((item for item in self._entries if item.user_id == user_id), None)
            if entry is None or entry.started:
                return False
            entry.cancel()
            return True

    async def position(self, user_id):
        async with self._lock:
            for index, entry in enumerate(self._entries):
                if entry.user_id == user_id:
                    return index
        return None


async def _notify_positions(entries):
    for index, entry in enumerate(entries):
        if index == 0 or entry.cancelled:
            continue
        await entry.on_position(index)
