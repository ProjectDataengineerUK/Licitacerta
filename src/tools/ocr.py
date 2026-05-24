from __future__ import annotations

import io
from pathlib import Path

from src.schemas.tender import PageContent


def extract_pages(source: bytes | str | Path) -> list[PageContent]:
    """
    Extrai texto de PDF. Tenta extração direta primeiro; cai para OCR se a página
    tiver menos de 50 caracteres (indicativo de página escaneada).
    """
    try:
        import pypdf
    except ImportError as exc:
        raise ImportError("pypdf not installed — run: uv pip install pypdf") from exc

    raw: bytes
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    else:
        raw = source

    reader = pypdf.PdfReader(io.BytesIO(raw))
    pages: list[PageContent] = []

    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        is_ocr = False

        if len(text.strip()) < 50:
            text = _ocr_page(page)
            is_ocr = True

        pages.append(
            PageContent(
                page_number=i,
                text=text.strip(),
                tables=_extract_tables(page),
                is_ocr=is_ocr,
            )
        )

    return pages


def _ocr_page(page) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""

    images = page.images
    if not images:
        return ""

    texts: list[str] = []
    for img_obj in images:
        img = Image.open(io.BytesIO(img_obj.data))
        texts.append(pytesseract.image_to_string(img, lang="por"))

    return "\n".join(texts)


def _extract_tables(page) -> list[dict]:
    return []
