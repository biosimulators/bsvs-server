from typing import AsyncGenerator

import pytest_asyncio

from biosim_server.dependencies import get_biosim_service, set_biosim_service
from biosim_server.common.biosim1_client import BiosimServiceRest
from tests.fixtures.biosim_service_mock import BiosimServiceMock


@pytest_asyncio.fixture(scope="session")
async def biosim_service_mock() -> AsyncGenerator[BiosimServiceMock,None]:
    biosim_service = BiosimServiceMock()
    saved_biosim_service = get_biosim_service()
    set_biosim_service(biosim_service)

    yield biosim_service

    await biosim_service.close()
    set_biosim_service(saved_biosim_service)


@pytest_asyncio.fixture(scope="session")
async def biosim_service_rest() -> AsyncGenerator[BiosimServiceRest,None]:
    biosim_service = BiosimServiceRest()
    saved_biosim_service = get_biosim_service()
    set_biosim_service(biosim_service)

    yield biosim_service

    await biosim_service.close()
    set_biosim_service(saved_biosim_service)


