"""
Event bus for publishing status updates via Server-Sent Events (SSE).
"""
import asyncio
from typing import Dict, Set
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class StatusEvent:
    """Event for image processing status update."""
    image_id: str
    status: str
    error: str = None


class EventBus:
    """
    Simple in-memory event bus for SSE.
    Supports multiple subscribers per user.
    """
    
    def __init__(self):
        # user_id -> set of asyncio.Queue
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
    
    def subscribe(self, user_id: str) -> asyncio.Queue:
        """Subscribe to events for a user. Returns a queue to receive events."""
        queue = asyncio.Queue()
        self._subscribers[user_id].add(queue)
        return queue
    
    def unsubscribe(self, user_id: str, queue: asyncio.Queue):
        """Unsubscribe from events."""
        if user_id in self._subscribers:
            self._subscribers[user_id].discard(queue)
            if not self._subscribers[user_id]:
                del self._subscribers[user_id]
    
    async def publish(self, user_id: str, event: StatusEvent):
        """Publish an event to all subscribers for a user."""
        if user_id in self._subscribers:
            for queue in self._subscribers[user_id]:
                try:
                    await queue.put(event)
                except Exception:
                    pass  # Ignore errors on individual queues
    
    def has_subscribers(self, user_id: str) -> bool:
        """Check if a user has any active subscribers."""
        return user_id in self._subscribers and len(self._subscribers[user_id]) > 0


# Global event bus instance
event_bus = EventBus()
