from motor.motor_asyncio import AsyncIOMotorClient

from biosim_server.biosim1.biosim_service import BiosimService
from biosim_server.biosim1.biosim_service_rest import BiosimServiceRest
from biosim_server.database.database_service import DatabaseService
from biosim_server.database.database_service_mongo import DatabaseServiceMongo
from biosim_server.io.file_service import FileService
from biosim_server.io.file_service_S3 import FileServiceS3

#------ database service (standalone or pytest) ------

MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DATABASE_NAME = "mydatabase"
MONGODB_VERIFICATION_COLLECTION_NAME = "verification"

global_database_service: DatabaseService | None = None

def set_database_service(db_service: DatabaseService | None):
    global global_database_service
    global_database_service = db_service

def get_database_service() -> DatabaseService | None:
    global global_database_service
    return global_database_service

#------ file service (standalone or pytest) ------

global_file_service: FileService | None = None

def set_file_service(file_service: FileService | None):
    global global_file_service
    global_file_service = file_service

def get_file_service() -> FileService | None:
    global global_file_service
    return global_file_service

#------- biosim service (standalone or pytest) ------

global_biosim_service: BiosimService | None = None

def set_biosim_service(biosim_service: BiosimService | None):
    global global_biosim_service
    global_biosim_service = biosim_service

def get_biosim_service() -> BiosimService | None:
    global global_biosim_service
    return global_biosim_service


#------ initialized standalone application (standalone) ------

def init_standalone():
    set_database_service(DatabaseServiceMongo(
        db_client=AsyncIOMotorClient(MONGODB_URL),
        db_name=MONGODB_DATABASE_NAME,
        verification_col_name=MONGODB_VERIFICATION_COLLECTION_NAME)
    )
    set_file_service(FileServiceS3())
    set_biosim_service(BiosimServiceRest())