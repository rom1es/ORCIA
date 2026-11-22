"""Redis 7.4 Turn Registry, Streams Buffer, Liveness Key & Cross-Worker Stop (`AD-25`, `R1`)."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

from orcia_core.orchestration._redis_turn_helpers import (
    build_rfc9457_stream_error_payload as build_rfc9457_stream_error_payload,
)
from orcia_core.orchestration._redis_turn_helpers import (
    cursor_gt,
    decode_redis_val,
    parse_redis_stream_entries,
    record_from_json,
    record_to_json,
)
from orcia_core.orchestration._redis_turn_helpers import (
    resolve_liveness_ttl_seconds as resolve_liveness_ttl_seconds,
)
from orcia_core.ports.assistant_turn_stream_port import (
    AssistantTurnRecord,
    AssistantTurnRegistryPort,
    AssistantTurnStreamEvent,
    AssistantTurnStreamPort,
)


class RedisAssistantTurnRegistry(AssistantTurnRegistryPort, AssistantTurnStreamPort):
    """Cross-worker Redis 7.4 turn registry, liveness tracker, stop channel & Streams buffer."""

    def __init__(
        self,
        redis_client: Any | None = None,
        *,
        turn_ttl_seconds: int = 3600,
        post_completion_ttl_seconds: int = 1800,
        stream_maxlen: int = 1000,
    ) -> None:
        self._redis = redis_client
        self._turn_ttl_seconds = turn_ttl_seconds
        self._post_completion_ttl_seconds = post_completion_ttl_seconds
        self._stream_maxlen = stream_maxlen
        self._local_turns: dict[str, AssistantTurnRecord] = {}
        self._local_idx: dict[tuple[str, str], list[str]] = {}
        self._local_live: dict[str, float] = {}
        self._local_stops: dict[str, str] = {}
        self._local_synth: set[str] = set()
        self._local_streams: dict[str, list[AssistantTurnStreamEvent]] = {}
        self._local_seq: dict[str, int] = {}
        self._local_conds: dict[str, asyncio.Condition] = {}

    def set_redis_client(self, redis_client: Any | None) -> None:
        """Attach or replace the async Redis client after Composition Root startup."""
        self._redis = redis_client

    @staticmethod
    def _tkey(kind: str, turn_id: str) -> str:
        prefix = f"{kind}:" if kind else ""
        return f"orcia:assistant:turn:{prefix}{turn_id}"

    @staticmethod
    def _idx_key(workspace_id: str, user_id: str) -> str:
        return f"orcia:assistant:turns:idx:{workspace_id}:{user_id}"

    @staticmethod
    def stop_channel(turn_id: str) -> str:
        return f"orcia:assistant:turn:stop_chan:{turn_id}"

    async def register_turn(self, record: AssistantTurnRecord, *, ttl_seconds: int = 3600) -> None:
        ttl = ttl_seconds or self._turn_ttl_seconds
        if self._redis is None:
            self._local_turns[record.turn_id] = record
            bucket = self._local_idx.setdefault((record.workspace_id, record.user_id), [])
            if record.turn_id not in bucket:
                bucket.insert(0, record.turn_id)
            return
        idx_k = self._idx_key(record.workspace_id, record.user_id)
        await self._redis.set(self._tkey("", record.turn_id), record_to_json(record), ex=ttl)
        await self._redis.zadd(
            idx_k, {record.turn_id: record.started_at_ms or time.time() * 1000.0}
        )
        await self._redis.expire(idx_k, ttl)

    async def update_turn(self, record: AssistantTurnRecord, *, ttl_seconds: int = 1800) -> None:
        ttl = (
            ttl_seconds
            if record.status in ("COMPLETED", "STOPPED", "ERROR")
            else self._turn_ttl_seconds
        )
        if self._redis is None:
            self._local_turns[record.turn_id] = record
            return
        await self._redis.set(self._tkey("", record.turn_id), record_to_json(record), ex=ttl)

    async def get_turn(
        self, workspace_id: str, user_id: str, turn_id: str
    ) -> AssistantTurnRecord | None:
        rec = await self.get_turn_by_id(turn_id)
        if rec is None or rec.workspace_id != workspace_id or rec.user_id != user_id:
            return None
        return rec

    async def get_turn_by_id(self, turn_id: str) -> AssistantTurnRecord | None:
        if self._redis is None:
            return self._local_turns.get(turn_id)
        return record_from_json(await self._redis.get(self._tkey("", turn_id)))

    async def list_active_turns(
        self, workspace_id: str, user_id: str
    ) -> tuple[AssistantTurnRecord, ...]:
        if self._redis is None:
            ids = self._local_idx.get((workspace_id, user_id), [])
            return tuple(self._local_turns[tid] for tid in ids if tid in self._local_turns)
        idx_k = self._idx_key(workspace_id, user_id)
        raw_ids = await self._redis.zrevrange(idx_k, 0, 29)
        results: list[AssistantTurnRecord] = []
        stale_ids: list[str] = []
        for raw_tid in raw_ids:
            tid = decode_redis_val(raw_tid)
            rec = await self.get_turn_by_id(tid)
            if rec is None:
                stale_ids.append(tid)
            else:
                results.append(rec)
        if stale_ids:
            await self._redis.zrem(idx_k, *stale_ids)
        return tuple(results)

    async def get_latest_turn(self, workspace_id: str, user_id: str) -> AssistantTurnRecord | None:
        turns = await self.list_active_turns(workspace_id, user_id)
        return turns[0] if turns else None

    async def refresh_liveness(self, turn_id: str, *, ttl_seconds: int = 15) -> None:
        eff_ttl = max(1, ttl_seconds)
        if self._redis is None:
            self._local_live[turn_id] = time.monotonic() + eff_ttl
            return
        await self._redis.set(self._tkey("live", turn_id), "1", ex=eff_ttl)

    async def is_live(self, turn_id: str) -> bool:
        if self._redis is None:
            exp = self._local_live.get(turn_id)
            return exp is not None and exp > time.monotonic()
        return bool(await self._redis.exists(self._tkey("live", turn_id)))

    async def clear_liveness(self, turn_id: str) -> None:
        if self._redis is None:
            self._local_live.pop(turn_id, None)
            return
        await self._redis.delete(self._tkey("live", turn_id))

    async def request_stop(
        self, turn_id: str, *, stopped_by_user_id: str, ttl_seconds: int = 300
    ) -> None:
        if self._redis is None:
            self._local_stops[turn_id] = stopped_by_user_id
            cond = self._local_conds.get(turn_id)
            if cond is not None:
                async with cond:
                    cond.notify_all()
            return
        await self._redis.set(self._tkey("stop", turn_id), stopped_by_user_id, ex=ttl_seconds)
        await self._redis.publish(self.stop_channel(turn_id), stopped_by_user_id)

    async def is_stop_requested(self, turn_id: str) -> str | None:
        if self._redis is None:
            return self._local_stops.get(turn_id)
        raw = await self._redis.get(self._tkey("stop", turn_id))
        return decode_redis_val(raw) if raw is not None else None

    async def request_synthesize_now(self, turn_id: str, *, ttl_seconds: int = 300) -> None:
        if self._redis is None:
            self._local_synth.add(turn_id)
            return
        await self._redis.set(self._tkey("synth", turn_id), "1", ex=ttl_seconds)

    async def is_synthesize_now_requested(self, turn_id: str) -> bool:
        if self._redis is None:
            return turn_id in self._local_synth
        return bool(await self._redis.exists(self._tkey("synth", turn_id)))

    async def append_event(
        self,
        turn_id: str,
        *,
        event: str,
        data: dict[str, Any],
        maxlen: int = 1000,
        ttl_seconds: int | None = None,
    ) -> str:
        cursor, _ = await self.append_event_with_seq(
            turn_id, event=event, data=data, maxlen=maxlen, ttl_seconds=ttl_seconds
        )
        return cursor

    async def append_event_with_seq(
        self,
        turn_id: str,
        *,
        event: str,
        data: dict[str, Any],
        maxlen: int = 1000,
        ttl_seconds: int | None = None,
    ) -> tuple[str, int]:
        if self._redis is None:
            seq = self._local_seq.get(turn_id, 0) + 1
            self._local_seq[turn_id] = seq
        else:
            seq_k = self._tkey("seq", turn_id)
            seq = int(await self._redis.incr(seq_k))
            await self._redis.expire(seq_k, max(ttl_seconds or self._turn_ttl_seconds, 1800))
        payload_data = dict(data)
        payload_data.setdefault("turn_id", turn_id)
        if int(payload_data.get("seq") or 0) <= 0:
            payload_data["seq"] = seq
        assigned_seq = int(payload_data["seq"])
        payload_data.setdefault("timestamp", datetime.now(UTC).isoformat())
        encoded = json.dumps({"seq": seq, "event": event, "data": payload_data}, ensure_ascii=False)
        eff_maxlen = maxlen or self._stream_maxlen

        if self._redis is None:
            cursor = f"{int(time.time() * 1000)}-{seq}"
            stream_evt = AssistantTurnStreamEvent(
                cursor=cursor, seq=seq, event=event, data=payload_data
            )
            self._local_streams.setdefault(turn_id, []).append(stream_evt)
            cond = self._local_conds.setdefault(turn_id, asyncio.Condition())
            async with cond:
                cond.notify_all()
            return cursor, assigned_seq

        s_key = self._tkey("stream", turn_id)
        raw_id = await self._redis.xadd(
            s_key, {"payload": encoded}, maxlen=eff_maxlen, approximate=True
        )
        if ttl_seconds is not None:
            await self._redis.expire(s_key, ttl_seconds)
        return decode_redis_val(raw_id), assigned_seq

    async def read_events(
        self,
        turn_id: str,
        *,
        after_cursor: str = "0-0",
        block_ms: int = 0,
        count: int = 200,
    ) -> tuple[AssistantTurnStreamEvent, ...]:
        cursor = (after_cursor or "0-0").strip() or "0-0"
        if self._redis is None:
            events = self._local_streams.get(turn_id, [])
            filtered = [e for e in events if cursor_gt(e.cursor, cursor)]
            if not filtered and block_ms > 0:
                cond = self._local_conds.setdefault(turn_id, asyncio.Condition())
                try:
                    async with cond:
                        await asyncio.wait_for(cond.wait(), timeout=block_ms / 1000.0)
                except TimeoutError:
                    pass
                events = self._local_streams.get(turn_id, [])
                filtered = [e for e in events if cursor_gt(e.cursor, cursor)]
            return tuple(filtered[:count])

        s_key = self._tkey("stream", turn_id)
        resp = await self._redis.xread(
            {s_key: cursor}, count=count, block=block_ms if block_ms > 0 else None
        )
        return parse_redis_stream_entries(resp)

    async def set_stream_ttl(self, turn_id: str, ttl_seconds: int = 1800) -> None:
        if self._redis is not None:
            await self._redis.expire(self._tkey("stream", turn_id), ttl_seconds)


__all__ = [
    "RedisAssistantTurnRegistry",
    "build_rfc9457_stream_error_payload",
    "resolve_liveness_ttl_seconds",
]
