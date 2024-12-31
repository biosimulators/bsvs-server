from abc import abstractmethod, ABC
from datetime import datetime
from enum import Enum
from typing import Dict

import numpy as np
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from archive.shared.data_model import DatabaseCollections, JobStatus, SimulatorSpec


class DatabaseConnector(ABC):
    """Abstract class that is both serializable and interacts with the database (of any type). """

    @staticmethod
    def timestamp() -> datetime:
        return datetime.utcnow()

    @abstractmethod
    def pending_jobs(self):
        pass

    @abstractmethod
    def completed_jobs(self):
        pass

    @abstractmethod
    async def read(self, *args, **kwargs):
        pass

    @abstractmethod
    async def write(self, collection_name: DatabaseCollections,
                    job_id: str,
                    timestamp: datetime,
                    status: JobStatus,
                    results: dict[str,np.ndarray],
                    source: str,
                    requested_simulators: list[SimulatorSpec]):
        pass



class MongoDbConnector(DatabaseConnector):
    def __init__(self, connection_uri: str, database_id: str, connector_id: str):
        self.database_id = database_id
        self.client = self._get_client(connection_uri)
        self.db = self._get_database(self.database_id)

    def _get_client(self, *args):
        return MongoClient(args[0])

    def _get_database(self, db_id: str) -> Database:
        return self.client.get_database(db_id)

    def _get_jobs_from_collection(self, coll_name: str):
        return [job for job in self.db[coll_name].find()]

    def pending_jobs(self):
        return self._get_jobs_from_collection("pending_jobs")

    def completed_jobs(self):
        return self._get_jobs_from_collection("completed_jobs")

    @property
    def data(self):
        return self._get_data()

    def _get_data(self):
        return {coll_name: [v for v in self.db[coll_name].find()] for coll_name in self.db.list_collection_names()}

    async def read(self, collection_name: DatabaseCollections | str, **kwargs):
        """Args:
            collection_name: str
            kwargs: (as in mongodb query)
        """
        coll_name = self._parse_enum_input(collection_name)
        coll = self.get_collection(coll_name)
        result = coll.find_one(kwargs.copy())
        return result

    async def write(self, collection_name: DatabaseCollections,
                    job_id: str,
                    timestamp: datetime,
                    status: JobStatus,
                    results: dict[str,np.ndarray],
                    source: str,
                    requested_simulators: list[SimulatorSpec]
                    ):
        coll_name = collection_name.value

        coll = self.get_collection(coll_name)

        result = coll.insert_one(kwargs.copy())
        return kwargs

    def get_collection(self, collection_name: str) -> Collection:
        try:
            return self.db[collection_name]
        except:
            return None

    async def insert_job_async(self, collection_name: str, **kwargs) -> Dict[str, Any]:
        return self.insert_job(collection_name, **kwargs)

    def insert_job(self, collection_name: str, **kwargs) -> Dict[str, Any]:
        coll = self.get_collection(collection_name)
        job_doc = kwargs.copy()
        print("Inserting job...")
        coll.insert_one(job_doc)
        print(f"Job successfully inserted: {self.db.pending_jobs.find_one(kwargs)}.")
        return kwargs

    async def update_job_status(self, collection_name: str, job_id: str, status: str | JobStatus):
        job_status = self._parse_enum_input(status)
        return self.db[collection_name].update_one({'job_id': job_id, }, {'$set': {'status': job_status}})

    def _parse_enum_input(self, _input: Any) -> str:
        return _input.value if isinstance(_input, Enum) else _input
