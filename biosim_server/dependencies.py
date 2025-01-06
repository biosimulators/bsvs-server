from temporalio.client import Client as TemporalClient

from biosim_server.io.file_service import FileService
from biosim_server.io.file_service_S3 import FileServiceS3
from biosim_server.omex_sim.biosim1.biosim_service import BiosimService
from biosim_server.omex_sim.biosim1.biosim_service_rest import BiosimServiceRest

#------ file service (standalone or pytest) ------

global_file_service: FileService | None = None

def set_file_service(file_service: FileService | None) -> None:
    global global_file_service
    global_file_service = file_service

def get_file_service() -> FileService | None:
    global global_file_service
    return global_file_service

#------- biosim service (standalone or pytest) ------

global_biosim_service: BiosimService | None = None

def set_biosim_service(biosim_service: BiosimService | None) -> None:
    global global_biosim_service
    global_biosim_service = biosim_service

def get_biosim_service() -> BiosimService | None:
    global global_biosim_service
    return global_biosim_service

#------ Temporal workflow client ------

global_temporal_client: TemporalClient | None = None

def set_temporal_client(temporal_client: TemporalClient | None) -> None:
    global global_temporal_client
    global_temporal_client = temporal_client

def get_temporal_client() -> TemporalClient | None:
    global global_temporal_client
    return global_temporal_client

#------ initialized standalone application (standalone) ------

async def init_standalone() -> None:
    set_file_service(FileServiceS3())
    set_biosim_service(BiosimServiceRest())
    set_temporal_client(await TemporalClient.connect("localhost:7233"))

async def shutdown_standalone() -> None:
    file_service = get_file_service()
    if file_service:
        await file_service.close()
    # biosim_service = get_biosim_service()
    # if biosim_service:
    #     await biosim_service.close()
    # temporal_client = get_temporal_client()
    # if temporal_client:
    #     await temporal_client.close()
    set_file_service(None)
    set_biosim_service(None)
    set_temporal_client(None)