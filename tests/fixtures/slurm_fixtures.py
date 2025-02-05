from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio

from biosim_server.common.ssh.ssh_service import SSHService
from biosim_server.config import get_settings


@pytest_asyncio.fixture(scope="session")
async def ssh_service() -> AsyncGenerator[SSHService]:
    ssh_service = SSHService(hostname=get_settings().slurm_submit_host,
                             username=get_settings().slurm_submit_user,
                             key_path=Path(get_settings().slurm_submit_key))
    yield ssh_service
    await ssh_service.close()
