import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

KV_DRIVER = Literal['file', 's3', 'gcs']
TS_DRIVER = Literal['zarr', 'n5', 'zarr3']

load_dotenv()

ENV_CONFIG_ENV_FILE = "CONFIG_ENV_FILE"
ENV_SECRET_ENV_FILE = "SECRET_ENV_FILE"

if os.getenv(ENV_CONFIG_ENV_FILE) is not None and os.path.exists(str(os.getenv(ENV_CONFIG_ENV_FILE))):
    load_dotenv(os.getenv(ENV_CONFIG_ENV_FILE))

if os.getenv(ENV_SECRET_ENV_FILE) is not None and os.path.exists(str(os.getenv(ENV_SECRET_ENV_FILE))):
    load_dotenv(os.getenv(ENV_SECRET_ENV_FILE))


class Settings(BaseSettings):
    storage_bucket: str = "files.biosimulations.dev"
    storage_endpoint_url: str = "https://storage.googleapis.com"
    storage_region: str = "us-east4"
    storage_tensorstore_driver: TS_DRIVER = "zarr3"
    storage_tensorstore_kvstore_driver: KV_DRIVER = "gcs"

    temporal_service_url: str = "localhost:7233"

    storage_local_cache_dir: str = "./local_cache"

    storage_gcs_credentials_file: str = ""

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "biosimulations"
    mongo_collection_omex_files: str = "omex_files"
    mongo_collection_sim_outputs: str = "sim_outputs"

    simdata_api_base_url: str = "https://simdata.api.biosimulations.org"
    biosimulators_api_base_url: str = "https://api.biosimulators.org"
    biosimulations_api_base_url: str = "https://api.biosimulations.org"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_local_cache_dir() -> Path:
    settings = get_settings()
    local_cache_dir = Path(settings.storage_local_cache_dir)
    local_cache_dir.mkdir(parents=True, exist_ok=True)
    return local_cache_dir

