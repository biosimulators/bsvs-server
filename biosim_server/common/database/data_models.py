from pydantic import BaseModel


class OmexFile(BaseModel):
    file_hash_md5: str
    uploaded_filename: str
    bucket_name: str
    omex_gcs_path: str
    file_size: int

