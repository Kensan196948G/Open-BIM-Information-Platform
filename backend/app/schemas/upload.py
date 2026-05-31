from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    id: str
    container_id: str
    original_filename: str
    storage_key: str
    content_type: str
    file_size_bytes: int
    checksum_sha256: str
    uploaded_by: str
    created_at: str
