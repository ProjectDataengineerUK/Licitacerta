"""AT-001: Submit edital — 202 + run_id. AT-007: Payload inválido — 422."""
import pytest
from httpx import AsyncClient


async def test_at001_submit_returns_202_and_run_id(client: AsyncClient):
    resp = await client.post(
        "/analyze",
        json={"edital_raw": "Pregão 001/2026 — Papel A4", "cnpj": "12345678000195"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "run_id" in body
    assert len(body["run_id"]) == 36  # UUID format


async def test_at001_run_id_is_unique(client: AsyncClient):
    r1 = await client.post(
        "/analyze",
        json={"edital_raw": "edital 1", "cnpj": "12345678000195"},
    )
    r2 = await client.post(
        "/analyze",
        json={"edital_raw": "edital 2", "cnpj": "12345678000195"},
    )
    assert r1.json()["run_id"] != r2.json()["run_id"]


async def test_at007_missing_cnpj_returns_422(client: AsyncClient):
    resp = await client.post("/analyze", json={"edital_raw": "texto"})
    assert resp.status_code == 422


async def test_at007_missing_edital_raw_returns_422(client: AsyncClient):
    resp = await client.post("/analyze", json={"cnpj": "12345678000195"})
    assert resp.status_code == 422


async def test_at007_empty_body_returns_422(client: AsyncClient):
    resp = await client.post("/analyze", json={})
    assert resp.status_code == 422
