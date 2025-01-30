from pydantic import BaseModel, field_validator


class OmexFile(BaseModel):
    file_hash_md5: str
    uploaded_filename: str
    bucket_name: str
    omex_gcs_path: str
    file_size: int

    @field_validator('omex_gcs_path')
    def validate_omex_gcs_path(cls, v: str) -> str:
        if v.find("/") == 0:
            raise ValueError("omex_gcs_path must not be an absolute path")
        return v

    @field_validator('uploaded_filename')
    def validate_uploaded_filename(cls, v: str) -> str:
        if v.find("/") >= 0:
            raise ValueError("uploaded_filename must not contain any path separators")
        return v


class DockerContainerInfo(BaseModel):
    url: str
    digest: str


class BiosimulatorVersion(BaseModel):
    id: str
    name: str
    version: str
    image: DockerContainerInfo


