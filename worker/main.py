import os
import asyncio
import logging

from dotenv import load_dotenv

from shared.database import MongoDbConnector
from shared.data_model import DEV_ENV_PATH
from shared.log_config import setup_logging

from worker.job import Supervisor


# set up dev env if possible
load_dotenv(DEV_ENV_PATH)

# logging
logger = logging.getLogger("biochecknet.worker.main.log")
setup_logging(logger)

# sleep params
DELAY_TIMER = 20
MAX_RETRIES = 30

# creds params
MONGO_URI = os.getenv("MONGO_URI")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
DB_NAME = "service_requests"

# shared db_connector
db_connector = MongoDbConnector(connection_uri=MONGO_URI, database_id=DB_NAME)
supervisor = Supervisor(db_connector=db_connector)


# async def main(max_retries=MAX_RETRIES):
#     n_retries = 0
#     await supervisor.run_job_check()


async def main(max_retries=MAX_RETRIES):
    n_retries = 0

    while True:
        # no job has come in a while
        if n_retries == MAX_RETRIES:
            await asyncio.sleep(10)  # TODO: adjust this for client polling as needed
        await supervisor.check_jobs()
        await asyncio.sleep(5)
        n_retries += 1


if __name__ == "__main__":
    asyncio.run(main())
