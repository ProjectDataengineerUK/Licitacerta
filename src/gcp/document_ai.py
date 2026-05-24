from __future__ import annotations

import os
from typing import Any

from src.schemas.tender import PageContent


class DocumentAIClient:
    def __init__(self, client: Any, processor_name: str) -> None:
        self._client = client
        self._processor_name = processor_name

    @classmethod
    def from_env(cls) -> DocumentAIClient:
        from google.cloud import documentai  # lazy import

        location = os.environ.get("DOCUMENT_AI_LOCATION", "us")
        client = documentai.DocumentProcessorServiceClient(
            client_options={"api_endpoint": f"{location}-documentai.googleapis.com"}
        )
        processor_name = (
            f"projects/{os.environ['GCP_PROJECT_ID']}"
            f"/locations/{location}"
            f"/processors/{os.environ['DOCUMENT_AI_PROCESSOR_ID']}"
        )
        return cls(client, processor_name)

    def process_pdf(self, content: bytes) -> list[PageContent]:
        from google.cloud import documentai  # lazy import

        raw_document = documentai.RawDocument(content=content, mime_type="application/pdf")
        request = documentai.ProcessRequest(
            name=self._processor_name, raw_document=raw_document
        )
        result = self._client.process_document(request=request)
        return self._to_page_contents(result.document)

    def _to_page_contents(self, document: Any) -> list[PageContent]:
        pages: list[PageContent] = []
        full_text = document.text

        for page in document.pages:
            page_num = page.page_number
            segments = page.layout.text_anchor.text_segments if page.layout.text_anchor.text_segments else []
            text_parts = [
                full_text[int(s.start_index):int(s.end_index)]
                for s in segments
            ]
            page_text = "".join(text_parts)

            tables: list[dict] = []
            for table in page.tables:
                rows = []
                for row in list(table.header_rows) + list(table.body_rows):
                    cells = []
                    for cell in row.cells:
                        cell_segs = cell.layout.text_anchor.text_segments
                        cell_text = "".join(
                            full_text[int(s.start_index):int(s.end_index)]
                            for s in cell_segs
                        )
                        cells.append(cell_text.strip())
                    rows.append(cells)
                tables.append({"rows": rows})

            is_ocr = any(
                block.layout.confidence < 0.95
                for block in page.blocks
            ) if page.blocks else False

            pages.append(
                PageContent(
                    page_number=page_num,
                    text=page_text,
                    tables=tables,
                    is_ocr=is_ocr,
                )
            )

        return pages
