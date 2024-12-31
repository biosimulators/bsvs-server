# test parsing and round tripping of HDF5File objects to and from JSON from file hdf5_file.json
#
# Usage:
# python -m tests.test_hdf5_json
# or
# python tests/test_hdf5_json.py
# @@@SNIPEND
import json
import os
from biosim_server.biosim1.models import HDF5File


def test_hdf5_json():
    # Load HDF5File object from JSON file
    filename = os.path.join(os.path.dirname(__file__), 'hdf5_file.json')
    with open(filename, 'r') as file:
        hdf5_file_dict = json.load(file)
        hdf5_file = HDF5File.model_validate(hdf5_file_dict)
        assert hdf5_file is not None

