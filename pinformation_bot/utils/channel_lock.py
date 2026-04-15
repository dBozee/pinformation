from asyncio import Lock


class ChannelLock:
    """
    An independent context manager for channel-level locks. Maintains its own registry of locks keyed by channel_id.
    """
    _locks: dict[int, Lock] = {}

    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.lock: Lock | None = None

    async def __aenter__(self):
        if self.channel_id not in ChannelLock._locks:
            ChannelLock._locks[self.channel_id] = Lock()
        self.lock = ChannelLock._locks[self.channel_id]
        await self.lock.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.lock:
            await self.lock.__aexit__(exc_type, exc_val, exc_tb)

    @classmethod
    def cleanup(cls, channel_id: int) -> None:
        """
        Remove a channel's lock from the registry.
        Call this when a pin is removed from a channel.
        """
        cls._locks.pop(channel_id, None)

    @classmethod
    def is_locked(cls, channel_id: int) -> bool:
        """Check if a channel's lock is currently held."""
        return channel_id in cls._locks and cls._locks[channel_id].locked()
