from __future__ import annotations

import json
import threading
from typing import Optional

from .config import STORE_PATH
from .models import Candidate, Job, Store, Stats, utc_now


_lock = threading.Lock()


def _empty_store() -> Store:
    return Store(
        jobs=[],
        candidates=[],
        meta={"created_at": utc_now(), "version": "1.0.0"},
    )


def load_store() -> Store:
    if not STORE_PATH.exists():
        store = _empty_store()
        save_store(store)
        return store
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        return Store.model_validate(data)
    except Exception:
        return _empty_store()


def save_store(store: Store) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(
        store.model_dump_json(indent=2),
        encoding="utf-8",
    )


def with_store(mutator):
    """Thread-safe read-modify-write."""
    with _lock:
        store = load_store()
        result = mutator(store)
        save_store(store)
        return result


def list_jobs() -> list[Job]:
    return load_store().jobs


def get_job(job_id: str) -> Optional[Job]:
    for j in load_store().jobs:
        if j.id == job_id:
            return j
    return None


def list_candidates(job_id: Optional[str] = None) -> list[Candidate]:
    items = load_store().candidates
    if job_id:
        items = [c for c in items if c.job_id == job_id]
    return sorted(items, key=lambda c: c.uploaded_at, reverse=True)


def get_candidate(candidate_id: str) -> Optional[Candidate]:
    for c in load_store().candidates:
        if c.id == candidate_id:
            return c
    return None


def compute_stats() -> Stats:
    store = load_store()
    cands = store.candidates
    scores = [c.report.match_score for c in cands if c.report]
    by = {d: 0 for d in ("pending", "shortlist", "interview", "reject", "hold")}
    for c in cands:
        key = c.decision.value if hasattr(c.decision, "value") else str(c.decision)
        by[key] = by.get(key, 0) + 1
    return Stats(
        total_candidates=len(cands),
        pending=by.get("pending", 0),
        shortlist=by.get("shortlist", 0),
        interview=by.get("interview", 0),
        reject=by.get("reject", 0),
        hold=by.get("hold", 0),
        avg_score=round(sum(scores) / len(scores), 1) if scores else 0,
        jobs_open=sum(1 for j in store.jobs if j.status == "open"),
        high_match=sum(1 for s in scores if s >= 75),
    )
