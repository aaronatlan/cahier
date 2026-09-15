"""Traitement des slides PDF : texte par page + image PNG par page."""

from __future__ import annotations

from pathlib import Path

RENDER_ZOOM = 2.0  # ~144 DPI, suffisant pour lire schémas/formules


def process_pdf(pdf_bytes: bytes, slides_dir: Path) -> int:
    """Sauvegarde le PDF source, extrait le texte de chaque page dans texte.txt,
    et rend chaque page en PNG (slides/page-01.png, ...). Retourne le nombre de pages."""
    import pymupdf

    slides_dir.mkdir(parents=True, exist_ok=True)
    (slides_dir / "source.pdf").write_bytes(pdf_bytes)

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        text_parts = []
        matrix = pymupdf.Matrix(RENDER_ZOOM, RENDER_ZOOM)
        for i, page in enumerate(doc, start=1):
            text_parts.append(f"--- Page {i} ---\n{page.get_text().strip()}")
            pix = page.get_pixmap(matrix=matrix)
            pix.save(str(slides_dir / f"page-{i:02d}.png"))
        (slides_dir / "texte.txt").write_text("\n\n".join(text_parts), encoding="utf-8")
        return len(doc)
    finally:
        doc.close()
