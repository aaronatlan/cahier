"""Traitement des slides PDF : texte par page + image PNG par page."""

from __future__ import annotations

import shutil
from pathlib import Path

RENDER_ZOOM = 2.0  # ~144 DPI, suffisant pour lire schémas/formules


def process_pdf(pdf_bytes: bytes, slides_dir: Path) -> int:
    """Sauvegarde le PDF source, extrait le texte de chaque page dans texte.txt,
    et rend chaque page en PNG (slides/page-01.png, ...). Retourne le nombre de pages."""
    import pymupdf

    if slides_dir.exists():
        shutil.rmtree(slides_dir)  # efface un éventuel envoi précédent
    slides_dir.mkdir(parents=True)
    (slides_dir / "source.pdf").write_bytes(pdf_bytes)

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        text_parts = []
        matrix = pymupdf.Matrix(RENDER_ZOOM, RENDER_ZOOM)
        width = max(2, len(str(len(doc))))  # évite que "page-100" trie avant "page-11"
        for i, page in enumerate(doc, start=1):
            text_parts.append(f"--- Page {i} ---\n{page.get_text().strip()}")
            pix = page.get_pixmap(matrix=matrix)
            pix.save(str(slides_dir / f"page-{i:0{width}d}.png"))
        (slides_dir / "texte.txt").write_text("\n\n".join(text_parts), encoding="utf-8")
        return len(doc)
    finally:
        doc.close()


def delete_page(slides_dir: Path, page_number: int) -> int:
    """Retire une page (numérotation 1-based) du jeu de slides et retraite le
    reste (source.pdf, page-XX.png, texte.txt) pour que tout reste cohérent
    et correctement renuméroté. Retourne le nombre de pages restantes."""
    import pymupdf

    doc = pymupdf.open(str(slides_dir / "source.pdf"))
    try:
        if not (1 <= page_number <= len(doc)):
            raise ValueError(f"Page {page_number} invalide (le jeu en a {len(doc)}).")
        doc.delete_page(page_number - 1)
        remaining = len(doc)
        pdf_bytes = doc.tobytes() if remaining else None
    finally:
        doc.close()

    if not remaining:
        shutil.rmtree(slides_dir)
        return 0
    return process_pdf(pdf_bytes, slides_dir)
