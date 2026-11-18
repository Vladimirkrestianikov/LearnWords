from typing import Tuple
from learnwords.config.settings import settings

ALLOWED_EXTENSIONS = {"txt", "pdf", "docx", "csv", "xlsx"}


def validate_file_upload(filename: str, file_size_bytes: int) -> Tuple[bool, str]:
    """Validate uploaded document format and size limit."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        return False, f"Размер файла превышает лимит {settings.MAX_UPLOAD_SIZE_MB} МБ."

    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return False, f"Неподдерживаемый формат файла: .{ext}. Разрешены: {allowed}."

    return True, "OK"

