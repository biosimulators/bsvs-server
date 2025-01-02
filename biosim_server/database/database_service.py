from abc import abstractmethod, ABC

from biosim_server.database.models import VerificationRun


class DatabaseService(ABC):
    @abstractmethod
    async def insert_verification_run(self, verification_run: VerificationRun) -> None:
        pass

    @abstractmethod
    async def get_verification_run(self, job_id: str) -> VerificationRun:
        pass

    @abstractmethod
    async def delete_verification_run(self, job_id: str) -> None:
        pass

