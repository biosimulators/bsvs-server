import pytest

from biosim_server.common.database.data_models import OmexFile
from biosim_server.common.database.database_service_mongo import DatabaseServiceMongo


@pytest.mark.asyncio
async def test_database_service(database_service_mongo: DatabaseServiceMongo) -> None:
    omex_file = OmexFile(file_hash_md5="1234", bucket_name="test_bucket", uploaded_filename="test.omex", omex_gcs_path="/path/to/omex", file_size=100000)
    await database_service_mongo.insert_omex_file(omex_file=omex_file)
    assert await database_service_mongo.get_omex_file(file_hash_md5=omex_file.file_hash_md5) == omex_file