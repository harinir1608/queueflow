"""
smartqueue.py
Core DSA logic for QueueFlow.

Data Structures used:
- Min-Heap (heapq)   -> priority scheduling (Emergency > Senior > General)
- Hash Map (dict)    -> O(1) token status / lookup
- Greedy Least-Load  -> counter assignment (load balancing)
"""

import heapq
import itertools
import time

PRIORITY_LEVELS = {"emergency": 0, "senior": 1, "general": 2}
PRIORITY_LABELS = {0: "Emergency", 1: "Senior", 2: "General"}

NUM_COUNTERS = 4


class TokenQueue:
    """Priority queue built on a binary min-heap."""

    def __init__(self):
        self.heap = []                      # (priority, seq, token_id, name, created_at)
        self._seq = itertools.count()       # tie-breaker so heap never compares dicts
        self.token_status = {}              # hash map: token_id -> status/metadata
        self.counters = [None] * NUM_COUNTERS
        self.counter_loads = [0] * NUM_COUNTERS
        self.served_log = []
        self._token_counter = itertools.count(1)
        self.service_durations = []
        self.wait_durations = []
        self.category_totals = {"Emergency": 0, "Senior": 0, "General": 0}

    # ---------- Queue operations ----------
    def add_token(self, name, category):
        category = category.lower()
        if category not in PRIORITY_LEVELS:
            category = "general"

        priority = PRIORITY_LEVELS[category]
        prefix = {"emergency": "E", "senior": "S", "general": "G"}[category]
        token_id = f"{prefix}-{next(self._token_counter):03d}"
        created_at = time.time()

        heapq.heappush(self.heap, (priority, next(self._seq), token_id, name, created_at))
        self.token_status[token_id] = {
            "name": name,
            "category": PRIORITY_LABELS[priority],
            "status": "waiting",
            "created_at": created_at,
        }
        self.category_totals[PRIORITY_LABELS[priority]] += 1
        return token_id

    def peek_waiting(self):
        """Return waiting tokens sorted by priority (heap order) without popping."""
        return sorted(self.heap, key=lambda x: (x[0], x[1]))

    def serve_next(self):
        if not self.heap:
            return None
        priority, seq, token_id, name, created_at = heapq.heappop(self.heap)
        counter_idx = self._assign_counter()
        self.counters[counter_idx] = token_id
        self.counter_loads[counter_idx] += 1
        called_at = time.time()
        self.wait_durations.append(called_at - created_at)
        self.wait_durations = self.wait_durations[-30:]
        self.token_status[token_id]["status"] = "serving"
        self.token_status[token_id]["counter"] = counter_idx + 1
        self.token_status[token_id]["called_at"] = called_at
        self.served_log.insert(0, {"token_id": token_id, "counter": counter_idx + 1})
        self.served_log = self.served_log[:10]
        return {
            "token_id": token_id,
            "name": name,
            "category": PRIORITY_LABELS[priority],
            "counter": counter_idx + 1,
        }

    def complete_token(self, counter_idx):
        """Mark the token at a counter as served/completed, freeing the counter."""
        token_id = self.counters[counter_idx]
        if token_id and token_id in self.token_status:
            info = self.token_status[token_id]
            info["status"] = "completed"
            called_at = info.get("called_at")
            if called_at:
                duration = time.time() - called_at
                self.service_durations.append(duration)
                self.service_durations = self.service_durations[-20:]  # keep last 20
        self.counters[counter_idx] = None
        return token_id

    def serve_next_to_counter(self, counter_idx):
        """Pop the highest-priority waiting token directly into a specific counter
        (used by the single-operator staff dashboard, bypassing auto load-balancing)."""
        if not self.heap:
            return None
        priority, seq, token_id, name, created_at = heapq.heappop(self.heap)
        self.counters[counter_idx] = token_id
        self.counter_loads[counter_idx] += 1
        called_at = time.time()
        self.wait_durations.append(called_at - created_at)
        self.wait_durations = self.wait_durations[-30:]
        self.token_status[token_id]["status"] = "serving"
        self.token_status[token_id]["counter"] = counter_idx + 1
        self.token_status[token_id]["called_at"] = called_at
        self.served_log.insert(0, {"token_id": token_id, "counter": counter_idx + 1})
        self.served_log = self.served_log[:10]
        return {
            "token_id": token_id,
            "name": name,
            "category": PRIORITY_LABELS[priority],
            "counter": counter_idx + 1,
        }

    def tokens_served_count(self):
        return sum(1 for v in self.token_status.values() if v.get("status") == "completed")

    # ---------- Load balancing (Greedy least-load-first) ----------
    def _assign_counter(self):
        free = [i for i, c in enumerate(self.counters) if c is None]
        if free:
            return min(free, key=lambda i: self.counter_loads[i])
        return self.counter_loads.index(min(self.counter_loads))

    # ---------- Serialization for the frontend ----------
    def get_state(self):
        waiting = []
        now = time.time()
        for priority, seq, token_id, name, created_at in self.peek_waiting():
            waiting.append({
                "token_id": token_id,
                "name": name,
                "category": PRIORITY_LABELS[priority],
                "priority": priority,
                "wait_seconds": int(now - created_at),
            })

        counters = []
        for i in range(NUM_COUNTERS):
            token_id = self.counters[i]
            counters.append({
                "counter": i + 1,
                "token_id": token_id,
                "info": self.token_status.get(token_id) if token_id else None,
            })

        avg_service = None
        if self.service_durations:
            avg_service = int(sum(self.service_durations) / len(self.service_durations))

        avg_wait = None
        if self.wait_durations:
            avg_wait = int(sum(self.wait_durations) / len(self.wait_durations))

        active_counters = sum(1 for c in self.counters if c is not None)
        total_categorized = sum(self.category_totals.values())
        category_pct = {}
        for cat, count in self.category_totals.items():
            category_pct[cat] = round((count / total_categorized) * 100, 1) if total_categorized else 0

        counter_details = []
        for i in range(NUM_COUNTERS):
            counter_details.append({
                "counter": i + 1,
                "token_id": self.counters[i],
                "tokens_handled": self.counter_loads[i],
                "status": "Busy" if self.counters[i] else "Idle",
            })

        return {
            "waiting": waiting,
            "waiting_count": len(waiting),
            "counters": counters,
            "served_log": self.served_log,
            "tokens_served_today": self.tokens_served_count(),
            "avg_service_seconds": avg_service,
            "avg_wait_seconds": avg_wait,
            "active_counters": active_counters,
            "total_counters": NUM_COUNTERS,
            "category_totals": self.category_totals,
            "category_pct": category_pct,
            "counter_details": counter_details,
        }
