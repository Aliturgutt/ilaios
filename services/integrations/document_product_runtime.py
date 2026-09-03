"""Bounded Creative/Document finished-product runtime for PDF, DOCX, XLSX, and CSV outputs."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import asdict
from xml.sax.saxutils import escape

from services.artifact_outputs import GovernedArtifactOutputStore

CAPABILITY_ID = "ilaios.capability.creative-document"


def _safe_pdf_text(value: str) -> str:
    value = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return re.sub(r"[^\x20-\x7e]", "?", value)


def build_pdf(title: str, body: str) -> bytes:
    lines = [title, "", *body.splitlines()]
    commands = ["BT", "/F1 12 Tf", "72 760 Td"]
    first = True
    for line in lines[:45]:
        if not first:
            commands.append("0 -16 Td")
        commands.append(f"({_safe_pdf_text(line[:110])}) Tj")
        first = False
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{index} 0 obj\n".encode("ascii"))
        result.extend(obj)
        result.extend(b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    result.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(result)


def build_docx(title: str, body: str) -> bytes:
    paragraphs = [title, *body.splitlines()]
    document_xml = "".join(
        f"<w:p><w:r><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"
        for text in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{document_xml}<w:sectPr/></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def _safe_csv_cell(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def build_csv(title: str, body: str) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([_safe_csv_cell(title)])
    for line in body.splitlines():
        writer.writerow([_safe_csv_cell(line)])
    return buffer.getvalue().encode("utf-8")


def build_xlsx(title: str, body: str) -> bytes:
    rows = [title, *body.splitlines()]
    worksheet_rows = "".join(
        f'<row r="{index}"><c r="A{index}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c></row>'
        for index, text in enumerate(rows, 1)
    )
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{worksheet_rows}</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Document" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    workbook_relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_relationships)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return buffer.getvalue()


class DocumentProductRuntime:
    """Render and persist one governed PDF+DOCX+XLSX+CSV finished-product bundle."""

    def __init__(self, outputs: GovernedArtifactOutputStore) -> None:
        self._outputs = outputs

    def create(
        self,
        *,
        artifact_id: str,
        version_id: str,
        tenant_id: str,
        project_id: str,
        job_id: str,
        title: str,
        body: str,
    ) -> dict[str, object]:
        if not title.strip() or not body.strip():
            raise ValueError("document title and body are required")
        pdf = self._outputs.put(
            artifact_id=f"{artifact_id}.pdf",
            version_id=version_id,
            tenant_id=tenant_id,
            project_id=project_id,
            job_id=job_id,
            artifact_type="document.pdf",
            mime_type="application/pdf",
            content=build_pdf(title, body),
        )
        docx = self._outputs.put(
            artifact_id=f"{artifact_id}.docx",
            version_id=version_id,
            tenant_id=tenant_id,
            project_id=project_id,
            job_id=job_id,
            artifact_type="document.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=build_docx(title, body),
        )
        xlsx = self._outputs.put(
            artifact_id=f"{artifact_id}.xlsx",
            version_id=version_id,
            tenant_id=tenant_id,
            project_id=project_id,
            job_id=job_id,
            artifact_type="document.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=build_xlsx(title, body),
        )
        csv_output = self._outputs.put(
            artifact_id=f"{artifact_id}.csv",
            version_id=version_id,
            tenant_id=tenant_id,
            project_id=project_id,
            job_id=job_id,
            artifact_type="document.csv",
            mime_type="text/csv; charset=utf-8",
            content=build_csv(title, body),
        )
        return {
            "capability_id": CAPABILITY_ID,
            "status": "ACCEPTED",
            "artifacts": [asdict(pdf), asdict(docx), asdict(xlsx), asdict(csv_output)],
        }
