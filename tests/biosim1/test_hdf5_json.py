# test parsing and round tripping of HDF5File objects to and from JSON from file hdf5_file.json
#
# Usage:
# python -m tests.test_hdf5_json
# or
# python tests/test_hdf5_json.py
# @@@SNIPEND
import json
import os
from pathlib import Path

from biosim_server.omex_sim.biosim1.models import HDF5File


def test_hdf5_json() -> None:
    # Load HDF5File object from JSON file at ../test_data/hdf5_file.json
    test_data_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "test_data"
    filename = test_data_dir / 'hdf5_file.json'
    with open(filename, 'r') as file:
        hdf5_file_dict = json.load(file)
        hdf5_file = HDF5File.model_validate(hdf5_file_dict)
        assert hdf5_file is not None

