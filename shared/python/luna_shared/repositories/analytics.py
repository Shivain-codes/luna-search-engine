"""Repository for query logs, click logs, and analytics aggregation."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from luna_shared.models import ClickLog, QueryLog


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_query(self, **kwargs) -> QueryLog:
        log = QueryLog(**kwargs)
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_query_log(self, query_log_id: uuid.UUID) -> QueryLog | None:
        return await self.session.get(QueryLog, query_log_id)

    async def log_click(
        self,
        *,
        query_log_id: uuid.UUID,
        document_id: uuid.UUID,
        position: int,
        dwell_time_ms: int | None = None,
    ) -> ClickLog:
        click = ClickLog(
            query_log_id=query_log_id,
            document_id=document_id,
            position=position,
            dwell_time_ms=dwell_time_ms,
        )
        self.session.add(click)
        await self.session.flush()
        return click

    def _range(self, stmt, start: datetime | None, end: datetime | None):
        if start:
            stmt = stmt.where(QueryLog.created_at >= start)
        if end:
            stmt = stmt.where(QueryLog.created_at <= end)
        return stmt

    async def query_volume(self, start: datetime | None, end: datetime | None) -> int:
        stmt = self._range(select(func.count()).select_from(QueryLog), start, end)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def top_queries(
        self, start: datetime | None, end: datetime | None, limit: int = 10
    ) -> list[dict]:
        stmt = self._range(
            select(QueryLog.normalized_query, func.count().label("c")), start, end
        ).group_by(QueryLog.normalized_query).order_by(func.count().desc()).limit(limit)
        result = await self.session.execute(stmt)
        return [{"query": row[0], "count": int(row[1])} for row in result.all()]

    async def zero_result_queries(
        self, start: datetime | None, end: datetime | None, limit: int = 10
    ) -> list[dict]:
        stmt = self._range(
            select(QueryLog.normalized_query, func.count().label("c")), start, end
        ).where(QueryLog.results_count == 0).group_by(
            QueryLog.normalized_query
        ).order_by(func.count().desc()).limit(limit)
        result = await self.session.execute(stmt)
        return [{"query": row[0], "count": int(row[1])} for row in result.all()]

    async def latency_samples(
        self, start: datetime | None, end: datetime | None
    ) -> list[float]:
        stmt = self._range(select(QueryLog.search_time_ms), start, end)
        result = await self.session.execute(stmt)
        return [float(r[0]) for r in result.all() if r[0] is not None]

    async def click_through_rate(
        self, start: datetime | None, end: datetime | None
    ) -> float | None:
        queries = await self.query_volume(start, end)
        if queries == 0:
            return None
        stmt = select(func.count(func.distinct(ClickLog.query_log_id))).select_from(
            ClickLog
        ).join(QueryLog, ClickLog.query_log_id == QueryLog.id)
        stmt = self._range(stmt, start, end)
        result = await self.session.execute(stmt)
        clicked = int(result.scalar_one())
        return clicked / queries


def percentile(values: list[float], pct: float) -> float | None:
    """Return the pct-th percentile (0-100) using nearest-rank."""
    if not values:
        return None
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1))))
    return ordered[k]


__all__ = ["AnalyticsRepository", "percentile"]
