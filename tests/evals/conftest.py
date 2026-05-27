"""Eval infrastructure: EvalRecorder + session-scoped fixture."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest


class EvalRecorder:
    """Records eval results to a JSONL file in .pytest_cache/eval_runs/."""

    def __init__(self, output_path: Path) -> None:
        self._path = output_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self._path.open("a", encoding="utf-8")

    def record(
        self,
        *,
        agent: str,
        eval_id: str,
        description: str,
        passed: bool,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        entry = {
            "agent": agent,
            "eval_id": eval_id,
            "description": description,
            "passed": passed,
            "result": result,
            "error": error,
        }
        self._fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


@pytest.fixture(scope="session")
def eval_recorder(tmp_path_factory: pytest.TempPathFactory) -> EvalRecorder:
    cache_dir = Path(".pytest_cache") / "eval_runs"
    output_path = cache_dir / f"{date.today()}.jsonl"
    recorder = EvalRecorder(output_path)
    yield recorder
    recorder.close()
