from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.ingest_juridical import chunk_text, main


def test_at007_chunk_text_splits_long_doc():
    text = "a" * 1200
    chunks = chunk_text(text, size=512, overlap=64)
    assert len(chunks) >= 3
    for c in chunks:
        assert len(c) <= 512


def test_chunk_text_single_chunk():
    text = "short text"
    chunks = chunk_text(text, size=512, overlap=64)
    assert chunks == ["short text"]


def test_chunk_text_empty_returns_empty():
    assert chunk_text("", size=512, overlap=64) == []


def test_chunk_text_invalid_size_raises():
    with pytest.raises(ValueError, match="chunk size"):
        chunk_text("text", size=0, overlap=0)


def test_chunk_text_invalid_overlap_raises():
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("text", size=100, overlap=100)


def test_at008_missing_required_args_exits_2():
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2


def test_at008_missing_tipo_exits_2():
    with pytest.raises(SystemExit) as exc_info:
        main(["--file", "x.txt", "--numero", "1/2024"])
    assert exc_info.value.code == 2


def _mock_embeddings_env(monkeypatch):
    fake_emb = MagicMock()
    fake_emb.embed_documents.return_value = [[0.0] * 768]
    monkeypatch.setattr(
        "scripts.ingest_juridical.VertexAIEmbeddings.from_env",
        classmethod(lambda cls: fake_emb),
    )
    return fake_emb


def _mock_db(monkeypatch):
    fake_cur = MagicMock()
    fake_cur.__enter__ = lambda s: s
    fake_cur.__exit__ = MagicMock(return_value=False)

    fake_conn = MagicMock()
    fake_conn.__enter__ = lambda s: s
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.cursor.return_value = fake_cur
    monkeypatch.setattr("scripts.ingest_juridical.psycopg.connect", lambda *a, **kw: fake_conn)
    monkeypatch.setattr("scripts.ingest_juridical.register_vector", lambda *a: None)
    return fake_conn, fake_cur


def test_at001_ingest_file_inserts_chunks(monkeypatch, tmp_path):
    doc = tmp_path / "acordao.txt"
    doc.write_text("Texto do acórdão TCU para fins de teste.", encoding="utf-8")
    _mock_embeddings_env(monkeypatch)
    fake_conn, fake_cur = _mock_db(monkeypatch)

    result = main([
        "--file", str(doc),
        "--tipo", "acordao",
        "--numero", "2500/2015-Plenario",
        "--fonte", "TCU",
    ])

    assert result == 0
    fake_cur.executemany.assert_called_once()
    call_args = fake_cur.executemany.call_args[0]
    rows = call_args[1]
    assert len(rows) >= 1
    assert rows[0][0] == "acordao"
    assert rows[0][1] == "2500/2015-Plenario"


def test_seed_inserts_seven_precedents(monkeypatch):
    _mock_embeddings_env(monkeypatch)
    fake_conn, fake_cur = _mock_db(monkeypatch)

    # Patch embed_documents to return 7 vectors (one per precedent in batch)
    fake_emb = MagicMock()
    fake_emb.embed_documents.return_value = [[0.0] * 768] * 7
    monkeypatch.setattr(
        "scripts.ingest_juridical.VertexAIEmbeddings.from_env",
        classmethod(lambda cls: fake_emb),
    )

    result = main(["--seed"])
    assert result == 0
    assert fake_cur.executemany.call_count == 7
