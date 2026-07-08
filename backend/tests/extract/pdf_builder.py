"""Build minimal but VALID PDF bytes for tests.

The sandbox has no network to download real ARCOP PDFs, so tests generate real,
spec-valid PDF files (real format, synthetic content) that pdfplumber parses like
any other. Real-ARCOP-format validation happens in Phase 6 with fixtures you drop
into tests/fixtures/pdfs/ on your networked machine.
"""

from __future__ import annotations


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(lines: list[str]) -> bytes:
    """Return valid single-page PDF bytes rendering `lines` as text."""
    stream = "BT\n/F1 12 Tf\n50 750 Td\n14 TL\n"
    for i, line in enumerate(lines):
        stream += ("T*\n" if i else "") + f"({_escape(line)}) Tj\n"
    stream += "ET"

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    header = "%PDF-1.4\n"
    body = ""
    offsets: list[int] = []
    pos = len(header.encode("latin-1"))
    for i, obj in enumerate(objects, start=1):
        chunk = f"{i} 0 obj\n{obj}\nendobj\n"
        offsets.append(pos)
        body += chunk
        pos += len(chunk.encode("latin-1"))

    xref = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n"
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{pos}\n%%EOF"
    )
    return (header + body + xref + trailer).encode("latin-1")
