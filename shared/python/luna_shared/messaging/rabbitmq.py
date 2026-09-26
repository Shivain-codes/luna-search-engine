"""Message broker with RabbitMQ and in-memory backends.

When ``RABBITMQ_URL`` is ``memory://`` an in-process asyncio queue backend
is used so producer/consumer flows work without RabbitMQ. The public
publish/consume API is identical across backends.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from luna_shared.config import get_settings
from luna_shared.messaging.envelope import Envelope
from luna_shared.messaging.queue_names import ExchangeNames

logger = logging.getLogger(__name__)

Handler = Callable[[Envelope], Awaitable[None]]


class _MemoryBroker:
    """Process-local broker. Routes by queue name (== routing key)."""

    _queues: dict[str, asyncio.Queue[Envelope]] = {}
    _consumers: dict[str, asyncio.Task] = {}

    async def connect(self) -> None:  # noqa: D401
        return None

    def _queue(self, name: str) -> asyncio.Queue[Envelope]:
        return self._queues.setdefault(name, asyncio.Queue())

    async def publish(self, exchange: str, routing_key: str, envelope: Envelope) -> None:
        await self._queue(routing_key).put(envelope)

    async def consume(self, queue_name: str, handler: Handler) -> None:
        async def _loop() -> None:
            queue = self._queue(queue_name)
            while True:
                envelope = await queue.get()
                try:
                    await handler(envelope)
                except Exception:  # noqa: BLE001
                    logger.exception("handler failed for %s", queue_name)
                    await self._queue(f"{queue_name}.dead-letter").put(envelope)
                finally:
                    queue.task_done()

        self._consumers[queue_name] = asyncio.create_task(_loop())

    async def drain(self, queue_name: str) -> None:
        """Testing helper: wait until a queue is fully processed."""
        await self._queue(queue_name).join()

    async def process_pending(self, queue_name: str, handler: Handler) -> int:
        """Synchronously process all currently-queued messages with a handler.

        Used for in-process pipelines/tests where a background consumer would
        contend with the producer over a shared DB connection.
        """
        queue = self._queue(queue_name)
        count = 0
        while not queue.empty():
            envelope = queue.get_nowait()
            try:
                await handler(envelope)
                count += 1
            except Exception:  # noqa: BLE001
                logger.exception("handler failed for %s", queue_name)
                await self._queue(f"{queue_name}.dead-letter").put(envelope)
            finally:
                queue.task_done()
        return count

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        for task in self._consumers.values():
            task.cancel()
        self._consumers.clear()


class _RabbitBroker:
    def __init__(self, url: str) -> None:
        self.url = url
        self._connection: Any = None
        self._channel: Any = None

    async def connect(self) -> None:
        if self._connection and not self._connection.is_closed:
            return
        import aio_pika

        self._connection = await aio_pika.connect_robust(self.url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)
        for name in (ExchangeNames.CRAWL, ExchangeNames.INDEX, ExchangeNames.EVENTS):
            await self._channel.declare_exchange(name, aio_pika.ExchangeType.TOPIC, durable=True)

    async def publish(self, exchange: str, routing_key: str, envelope: Envelope) -> None:
        import aio_pika

        await self.connect()
        exch = await self._channel.get_exchange(exchange)
        await exch.publish(
            aio_pika.Message(
                body=envelope.to_json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
                message_id=envelope.event_id,
            ),
            routing_key=routing_key,
        )

    async def consume(self, queue_name: str, handler: Handler) -> None:
        await self.connect()
        dlq = await self._channel.declare_queue(f"{queue_name}.dead-letter", durable=True)
        queue = await self._channel.declare_queue(
            queue_name,
            durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": dlq.name},
        )

        async def _on_message(message: Any) -> None:
            try:
                envelope = Envelope.from_bytes(message.body)
                await handler(envelope)
                await message.ack()
            except Exception:  # noqa: BLE001
                logger.exception("handler failed for %s", queue_name)
                await message.reject(requeue=False)

        await queue.consume(_on_message)

    async def ping(self) -> bool:
        try:
            await self.connect()
            return self._connection is not None and not self._connection.is_closed
        except Exception:
            return False

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()


class Broker:
    def __init__(self, url: str | None = None) -> None:
        self.url = url or get_settings().rabbitmq_url
        self.is_memory = self.url.startswith("memory://")
        self._backend: _MemoryBroker | _RabbitBroker = (
            _MemoryBroker() if self.is_memory else _RabbitBroker(self.url)
        )

    async def connect(self) -> None:
        await self._backend.connect()

    async def publish(self, exchange: str, routing_key: str, envelope: Envelope) -> None:
        await self._backend.publish(exchange, routing_key, envelope)

    async def consume(self, queue_name: str, handler: Handler) -> None:
        await self._backend.consume(queue_name, handler)

    async def drain(self, queue_name: str) -> None:
        if isinstance(self._backend, _MemoryBroker):
            await self._backend.drain(queue_name)

    async def process_pending(self, queue_name: str, handler: Handler) -> int:
        if isinstance(self._backend, _MemoryBroker):
            return await self._backend.process_pending(queue_name, handler)
        return 0

    async def ping(self) -> bool:
        return await self._backend.ping()

    async def close(self) -> None:
        await self._backend.close()


_broker: Broker | None = None


def get_broker() -> Broker:
    global _broker
    if _broker is None:
        _broker = Broker()
    return _broker


# Backwards-compatible alias
RabbitMQClient = Broker
get_rabbitmq_client = get_broker

__all__ = ["Broker", "RabbitMQClient", "get_broker", "get_rabbitmq_client"]
