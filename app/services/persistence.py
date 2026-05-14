import logging
import time
from collections import deque
from fastapi import WebSocket
from typing import List

logger = logging.getLogger(__name__)
fh = logging.FileHandler("/tmp/proxy.log")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(fh)
logger.setLevel(logging.INFO)


# ── Connection Manager ────────────────────────────────────────────────────────


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await websocket.send_json(
            {
                "type": "initial_state",
                "payload": {
                    "events": list(interaction_store.get_all()),
                    "stats": interaction_store.get_stats(),
                    "policy": {},
                },
            }
        )

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast failed: {e}")
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


# ── In-memory store ───────────────────────────────────────────────────────────


def _empty_stats() -> dict:
    return {
        "total_requests": 0,
        "allowed_count": 0,
        "blocked_count": 0,
        "avg_risk_score": 0.0,
        "action_counts": {},
        "intent_counts": {},
        "rule_counts": {},
        "risk_histogram": [0] * 10,  # buckets: 0-0.1, 0.1-0.2, …, 0.9-1.0
        "time_series": [],  # computed fresh on each get_stats() call
    }


class LiveInteractionStore:
    def __init__(self, maxlen: int = 200):
        self.interactions: deque = deque(maxlen=maxlen)
        self.seen_ids: set = set()
        self._stats = _empty_stats()

    # ── write ──

    def add(self, interaction: dict) -> bool:
        req_id = interaction.get("request_id")

        # Deduplicate
        if req_id and req_id in self.seen_ids:
            return False
        if req_id:
            self.seen_ids.add(req_id)
            # Prevent unbounded growth
            if len(self.seen_ids) > 2000:
                self.seen_ids.clear()

        self.interactions.append(interaction)
        self._update_stats(interaction)
        return True

    def _update_stats(self, interaction: dict):
        s = self._stats
        s["total_requests"] += 1

        verdict = (interaction.get("verdict") or "ALLOW").upper()
        if verdict == "ALLOW":
            s["allowed_count"] += 1
        else:
            s["blocked_count"] += 1

        # action_counts uses the verdict string directly
        s["action_counts"][verdict] = s["action_counts"].get(verdict, 0) + 1

        # rule
        rule = interaction.get("rule_name") or "(default)"
        s["rule_counts"][rule] = s["rule_counts"].get(rule, 0) + 1

        # intent
        meta = interaction.get("metadata") or {}
        intent = meta.get("intent_category") or "general"
        s["intent_counts"][intent] = s["intent_counts"].get(intent, 0) + 1

        # risk score
        risk = float(meta.get("risk_score") or 0)
        bucket = min(int(risk * 10), 9)
        s["risk_histogram"][bucket] += 1

        # running average
        total = s["total_requests"]
        s["avg_risk_score"] = ((s["avg_risk_score"] * (total - 1)) + risk) / total

    # ── read ──

    def get_all(self):
        return self.interactions

    def get_stats(self) -> dict:
        s = dict(self._stats)
        s["time_series"] = self._build_time_series()
        return s

    def _build_time_series(self) -> list:
        """Return 60 one-minute buckets covering the last hour."""
        now_ms = time.time() * 1000
        buckets = [{"count": 0, "blocked": 0} for _ in range(60)]

        for item in self.interactions:
            ts = float(item.get("timestamp") or 0)
            age_ms = now_ms - ts
            if not (0 <= age_ms < 60 * 60_000):
                continue
            idx = 59 - int(age_ms // 60_000)
            buckets[idx]["count"] += 1
            verdict = (item.get("verdict") or "ALLOW").upper()
            if verdict != "ALLOW":
                buckets[idx]["blocked"] += 1

        return buckets


# ── Singletons ────────────────────────────────────────────────────────────────

manager = ConnectionManager()
interaction_store = LiveInteractionStore()


# ── Public API ────────────────────────────────────────────────────────────────


async def get_interactions(limit: int = 50, request_id: str = None):
    history = list(interaction_store.get_all())
    if request_id:
        return [i for i in history if i.get("request_id") == request_id]
    return history[-limit:]


async def log_interaction(
    request_id: str,
    model: str,
    user_message: str,
    verdict: str,
    final_response: str,
    policy_reason: str = None,
    metadata: dict = None,
):
    verdict_upper = (verdict or "ALLOW").upper()

    interaction = {
        "request_id": request_id,
        "timestamp": time.time() * 1000,  # ms — JS Date-compatible
        "model": model,
        "user_message": user_message,
        "verdict": verdict_upper,
        "policy_reason": policy_reason,
        "final_response": final_response,
        "direction": "ingress",
        "action": verdict_upper,
        "rule_name": policy_reason
        or ("(default)" if verdict_upper == "ALLOW" else "Policy Block"),
        "blocked": verdict_upper != "ALLOW",
        "metadata": metadata or {},
    }

    added = interaction_store.add(interaction)
    if not added:
        logger.debug(f"Duplicate interaction skipped: {request_id}")
        return

    await manager.broadcast({"type": "event", "payload": interaction})
    await manager.broadcast(
        {"type": "stats_update", "payload": interaction_store.get_stats()}
    )

    logger.info(
        f"Interaction logged and broadcast | request_id={request_id} | verdict={verdict_upper}"
    )
