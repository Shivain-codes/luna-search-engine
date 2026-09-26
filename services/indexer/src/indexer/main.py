"""Indexer service: consumes index tasks and exposes a direct index endpoint."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from luna_shared.app import create_app
from luna_shared.config import IndexerSettings
from luna_shared.database import close_db, db, init_db
from luna_shared.errors import NotFoundError
from luna_shared.messaging import Broker, Envelope, QueueNames, get_broker
from pydantic import BaseModel

from indexer.service import index_document

logger = logging.getLogger("indexer")
settings = IndexerSettings()
broker: Broker = get_broker()


async def _handle_index_task(envelope: Envelope) -> None:
    document_id = envelope.payload.get("document_id")
    if not document_id:
        raise ValueError("index task missing document_id")
    async with db.session() as session:
        await index_document(session, uuid.UUID(document_id))
    logger.info("indexed document %s", document_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_startup()
    await init_db()
    await broker.connect()
    await broker.consume(QueueNames.INDEX_REQUESTED, _handle_index_task)
    logger.info("indexer consuming %s", QueueNames.INDEX_REQUESTED)
    yield
    await broker.close()
    await close_db()


app, health = create_app(settings, title="Luna Indexer", lifespan=lifespan)
health.register("postgres", db.ping)
health.register("rabbitmq", broker.ping)


class IndexRequest(BaseModel):
    document_id: str


@app.post("/api/v1/index")
async def index_now(request: IndexRequest) -> dict:
    """Synchronously (re)index a document by id."""
    async with db.session() as session:
        try:
            return await index_document(session, uuid.UUID(request.document_id))
        except ValueError as exc:
            raise NotFoundError(str(exc)) from exc


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    run()
