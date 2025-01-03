import pytest  # noqa: F401
import pytest_asyncio  # noqa: F401

# Import all fixtures from the fixtures modules
from tests.fixtures.database_fixtures import (  # noqa: F401
    database_service,
    mongodb_container,
    mongo_test_client,
    mongo_test_database,
    verification_collection,
    verification_id,
    verification_run_example
)
from tests.fixtures.s3_fixtures import (  # noqa: F401
    file_service_s3,
    file_service_local
)
from tests.fixtures.temporal_fixtures import (  # noqa: F401
    temporal_env,
    temporal_client,
    temporal_verify_worker
)


# Add the --workflow-environment option
def pytest_addoption(parser):
    parser.addoption(
        "--workflow-environment",
        action="store",
        default="local",
        help="Specify the workflow environment"
    )

# If you need to redefine or extend any fixtures, you can do so here.
