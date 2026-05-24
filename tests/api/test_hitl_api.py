"""AT-003: Status pausado no HITL. AT-004: Approve. AT-005: Reject."""
import asyncio

from httpx import AsyncClient


async def _submit_and_wait_decided(client: AsyncClient) -> str:
    resp = await client.post(
        "/analyze",
        json={"edital_raw": "Pregão 001/2026 — Papel A4", "cnpj": "12345678000195"},
    )
    run_id = resp.json()["run_id"]

    deadline = asyncio.get_event_loop().time() + 5.0
    while asyncio.get_event_loop().time() < deadline:
        body = (await client.get(f"/runs/{run_id}")).json()
        if body["current_step"] == "decided":
            return run_id
        await asyncio.sleep(0.05)

    raise TimeoutError(f"pipeline did not reach 'decided' in time; last step: {body.get('current_step')}")


async def test_at003_status_paused_at_decided(client: AsyncClient):
    run_id = await _submit_and_wait_decided(client)
    resp = await client.get(f"/runs/{run_id}")
    body = resp.json()
    assert body["current_step"] == "decided"
    assert body["bid_decision"]["recommendation"] == "participar"


async def test_at004_approve_runs_to_completed(client: AsyncClient):
    run_id = await _submit_and_wait_decided(client)

    resp = await client.post(
        f"/runs/{run_id}/approve",
        json={"approver": "jonatas", "comment": "aprovado no teste"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_step"] == "completed"


async def test_at004_approve_results_has_proposal(client: AsyncClient):
    run_id = await _submit_and_wait_decided(client)
    await client.post(
        f"/runs/{run_id}/approve",
        json={"approver": "jonatas", "comment": "ok"},
    )
    resp = await client.get(f"/runs/{run_id}/results")
    assert resp.status_code == 200
    result = resp.json()
    assert result["proposal_draft"] is not None
    assert result["proposal_draft"]["price"] == "47058.82"


async def test_at005_reject_sets_rejected_step(client: AsyncClient):
    run_id = await _submit_and_wait_decided(client)

    resp = await client.post(
        f"/runs/{run_id}/reject",
        json={"approver": "jonatas", "reason": "margem insuficiente"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_step"] == "rejected"


async def test_approve_non_approvable_step_returns_409(client: AsyncClient):
    resp = await client.post(
        "/analyze",
        json={"edital_raw": "edital", "cnpj": "12345678000195"},
    )
    run_id = resp.json()["run_id"]

    resp = await client.post(
        f"/runs/{run_id}/approve",
        json={"approver": "jonatas", "comment": "muito cedo"},
    )
    assert resp.status_code == 409


async def test_approve_unknown_run_returns_404(client: AsyncClient):
    resp = await client.post(
        "/runs/00000000-0000-0000-0000-000000000000/approve",
        json={"approver": "jonatas", "comment": ""},
    )
    assert resp.status_code == 404
