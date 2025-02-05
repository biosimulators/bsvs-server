import logging
from pathlib import Path

import asyncssh

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SSHService:
    hostname: str
    username: str
    key_path: Path

    def __init__(self, hostname: str, username: str, key_path: Path):
        self.hostname = hostname
        self.username = username
        self.key_path = key_path

    async def run_command(self, command: str) -> str:
        async with asyncssh.connect(host=self.hostname, username=self.username, client_keys=[self.key_path]) as conn:
            try:
                result = await conn.run(command, check=True)
            except asyncssh.ProcessError as exc:
                logger.error(msg=f"failed to send command {command}", exc_info=exc)
                raise exc
            except (OSError, asyncssh.Error) as exc:
                logger.error(msg=f"failed to send command {command}", exc_info=exc)
                raise exc
            else:
                assert isinstance(result.stdout, str)
                return result.stdout

    async def scp_upload(self, local_file: Path, remote_path: Path) -> None:
        async with asyncssh.connect(host=self.hostname, username=self.username, client_keys=[self.key_path]) as conn:
            try:
                await asyncssh.scp(srcpaths=local_file, dstpath=(conn, remote_path))
            except asyncssh.Error as exc:
                logger.error(msg=f"failed to send file {local_file} to {remote_path}", exc_info=exc)
                raise exc

    async def scp_download(self, local_file: Path, remote_path: Path) -> None:
        async with asyncssh.connect(host=self.hostname, username=self.username, client_keys=[self.key_path]) as conn:
            try:
                await asyncssh.scp(srcpaths=(conn, remote_path), dstpath=local_file)
            except asyncssh.Error as exc:
                logger.error(msg=f"failed to retrieve remote file {remote_path} to {local_file}", exc_info=exc)
                raise exc

    async def close(self) -> None:
        pass  # nothing to do here because we don't yet keep the connection around.
