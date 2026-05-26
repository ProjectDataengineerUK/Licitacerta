#!/usr/bin/env python3
"""
CLI: Ingere documento jurídico (TXT) na tabela juridical_chunks (pgvector).

Uso:
  python scripts/ingest_juridical.py \\
      --file docs/seeds/acordao_2500_2015.txt \\
      --tipo acordao \\
      --numero "2500/2015-Plenario" \\
      --fonte "TCU" \\
      [--chunk-size 512] [--overlap 64]

  python scripts/ingest_juridical.py --seed   # carrega os 7 precedentes hardcoded
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import psycopg
from pgvector.psycopg import register_vector

from src.config import settings
from src.gcp.vertex_ai import VertexAIEmbeddings

SEED_PRECEDENTS = [
    (
        "acordao", "2500/2015-Plenario", "TCU",
        "Acórdão 2.500/2015-Plenário (TCU): É vedada a inclusão, em editais de licitação, de "
        "exigências que restrinjam o caráter competitivo do certame, especialmente especificações "
        "que direcionem a contratação para marca, modelo ou fabricante determinado, salvo quando "
        "houver justificativa técnica devidamente fundamentada nos autos. Art. 41, §1º, "
        "Lei 14.133/2021.",
    ),
    (
        "acordao", "1284/2023-Plenario", "TCU",
        "Acórdão 1.284/2023-Plenário (TCU): Exigências de atestados de capacidade técnica "
        "desproporcionais ao objeto licitado configuram restrição indevida à competitividade. "
        "Quantitativos mínimos em atestados devem guardar pertinência e proporcionalidade com "
        "o objeto do contrato.",
    ),
    (
        "acordao", "936/2011-Plenario", "TCU",
        "Acórdão 936/2011-Plenário (TCU): A garantia contratual exigida na licitação não pode "
        "ultrapassar 5% do valor estimado do contrato, salvo nas hipóteses excepcionais previstas "
        "em lei, nas quais o percentual pode chegar a 10%. Percentuais superiores configuram "
        "restrição desproporcional à participação.",
    ),
    (
        "acordao", "2696/2022-Plenario", "TCU",
        "Acórdão 2.696/2022-Plenário (TCU): Prazos de entrega manifestamente inexequíveis, "
        "incompatíveis com o lead time do mercado para o produto ou serviço licitado, configuram "
        "restrição indevida à competitividade e devem ser motivados com base em pesquisa de mercado.",
    ),
    (
        "acordao", "1510/2021-Plenario", "TCU",
        "Acórdão 1.510/2021-Plenário (TCU): A habilitação técnica restritiva, exigindo "
        "comprovações além das necessárias e suficientes para a execução do objeto contratual, "
        "viola o princípio da ampla competitividade e constitui restrição indevida.",
    ),
    (
        "acordao", "3243/2020-Plenario", "TCU",
        "Acórdão 3.243/2020-Plenário (TCU): Critérios de julgamento subjetivos, sem parâmetros "
        "objetivos e verificáveis de avaliação, permitem arbítrio da Administração, comprometem "
        "a isonomia entre licitantes e violam o princípio da vinculação ao instrumento convocatório.",
    ),
    (
        "sumula", "Sumula-269", "TCU",
        "Súmula TCU 269: Nas contratações para a aquisição de bens e serviços comuns, "
        "as exigências de habilitação técnica devem se limitar ao mínimo necessário para garantir "
        "o adimplemento das obrigações contratuais, sendo vedadas exigências excessivas que "
        "restrinjam a competitividade do certame.",
    ),
]


def chunk_text(text: str, size: int = 512, overlap: int = 64) -> list[str]:
    if size <= 0:
        raise ValueError("chunk size must be > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = end - overlap
    return chunks


def insert_chunks(db_url: str, tipo: str, numero: str, fonte: str,
                  texts: list[str], embeddings: list[list[float]]) -> int:
    with psycopg.connect(db_url) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO juridical_chunks (tipo, numero, fonte, texto, embedding) "
                "VALUES (%s, %s, %s, %s, %s)",
                [(tipo, numero, fonte, t, e) for t, e in zip(texts, embeddings)],
            )
        conn.commit()
    return len(texts)


def ingest_file(file: Path, tipo: str, numero: str, fonte: str,
                chunk_size: int, overlap: int) -> int:
    text = file.read_text(encoding="utf-8")
    chunks = chunk_text(text, size=chunk_size, overlap=overlap)
    if not chunks:
        return 0
    emb_client = VertexAIEmbeddings.from_env()
    embeddings = emb_client.embed_documents(chunks)
    return insert_chunks(settings.database_url, tipo, numero, fonte, chunks, embeddings)


def run_seed() -> int:
    emb_client = VertexAIEmbeddings.from_env()
    texts = [p[3] for p in SEED_PRECEDENTS]
    vectors = emb_client.embed_documents(texts)
    total = 0
    for (tipo, numero, fonte, _), vec, text in zip(SEED_PRECEDENTS, vectors, texts):
        n = insert_chunks(settings.database_url, tipo, numero, fonte, [text], [vec])
        total += n
        print(f"  Seed: {n} chunk(s) para [{tipo}] {numero}")
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ingest_juridical",
        description="Ingere documento jurídico na base pgvector.",
    )
    parser.add_argument("--file", type=Path, help="Arquivo .txt a ingerir")
    parser.add_argument("--tipo", choices=["acordao", "sumula", "lei", "artigo"])
    parser.add_argument("--numero", help='Identificador do documento, ex: "2500/2015-Plenario"')
    parser.add_argument("--fonte", default="TCU", help="Fonte do documento (padrão: TCU)")
    parser.add_argument("--chunk-size", type=int, default=512, dest="chunk_size")
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument("--seed", action="store_true", help="Carrega os 7 precedentes hardcoded")
    args = parser.parse_args(argv)

    if args.seed:
        total = run_seed()
        print(f"Seed concluído: {total} chunk(s) inseridos no total.")
        return 0

    if not args.file or not args.tipo or not args.numero:
        parser.error("--file, --tipo e --numero são obrigatórios (ou use --seed)")

    n = ingest_file(args.file, args.tipo, args.numero, args.fonte,
                    args.chunk_size, args.overlap)
    print(f"Inseridos {n} chunk(s) de {args.file} [{args.tipo}] {args.numero}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
