import io
import csv
import docx
import pymupdf
import openpyxl
from typing import Tuple
from learnwords.utils.logger import logger


class FileParser:
    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> str:
        """Extract plain text from various file formats: TXT, DOCX, PDF, CSV, XLSX."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""

        if ext == "txt":
            return FileParser._extract_from_txt(file_bytes)
        elif ext == "pdf":
            return FileParser._extract_from_pdf(file_bytes)
        elif ext in ["docx", "doc"]:
            return FileParser._extract_from_docx(file_bytes)
        elif ext == "csv":
            return FileParser._extract_from_csv(file_bytes)
        elif ext in ["xlsx", "xls"]:
            return FileParser._extract_from_xlsx(file_bytes)
        else:
            # Fallback to UTF-8 decoding
            return FileParser._extract_from_txt(file_bytes)

    @staticmethod
    def _extract_from_txt(file_bytes: bytes) -> str:
        for enc in ["utf-8", "utf-8-sig", "windows-1251", "cp1252", "latin-1"]:
            try:
                return file_bytes.decode(enc)
            except UnicodeDecodeError:
                continue
        return file_bytes.decode("utf-8", errors="ignore")

    @staticmethod
    def _extract_from_pdf(file_bytes: bytes) -> str:
        text_parts = []
        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text_parts.append(page.get_text("text"))
            doc.close()
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
        return "\n".join(text_parts)

    @staticmethod
    def _extract_from_docx(file_bytes: bytes) -> str:
        text_parts = []
        try:
            stream = io.BytesIO(file_bytes)
            doc = docx.Document(stream)
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if len(cells) >= 2:
                        text_parts.append(f"{cells[0]} — {cells[1]}")
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
        return "\n".join(text_parts)

    @staticmethod
    def _extract_from_csv(file_bytes: bytes) -> str:
        raw_text = FileParser._extract_from_txt(file_bytes)
        lines = []
        reader = csv.reader(io.StringIO(raw_text))
        for row in reader:
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                lines.append(f"{row[0].strip()} — {row[1].strip()}")
            elif len(row) == 1 and row[0].strip():
                lines.append(row[0].strip())
        return "\n".join(lines)

    @staticmethod
    def _extract_from_xlsx(file_bytes: bytes) -> str:
        text_parts = []
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    non_empty = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                    if len(non_empty) >= 2:
                        text_parts.append(f"{non_empty[0]} — {non_empty[1]}")
                    elif len(non_empty) == 1:
                        text_parts.append(non_empty[0])
            wb.close()
        except Exception as e:
            logger.error(f"Error extracting text from XLSX: {e}")
        return "\n".join(text_parts)
