from pydantic import BaseModel

ATTRIBUTE_VALUE_TYPE = int | float | str | bool | list[str] | list[int] | list[float] | list[bool]


class HDF5Attribute(BaseModel):
    key: str
    value: ATTRIBUTE_VALUE_TYPE


class HDF5Dataset(BaseModel):
    name: str
    shape: list[int]
    attributes: list[HDF5Attribute]

    @property
    def sedml_labels(self) -> list[str]:
        for attr in self.attributes:
            if attr.key == "sedmlDataSetLabels":
                if isinstance(attr.value, list) and all(isinstance(v, str) for v in attr.value):
                    return attr.value  # type: ignore
        return []


class HDF5Group(BaseModel):
    name: str
    attributes: list[HDF5Attribute]
    datasets: list[HDF5Dataset]


class HDF5File(BaseModel):
    filename: str
    id: str
    uri: str
    groups: list[HDF5Group]

    @property
    def datasets(self) -> dict[str, HDF5Dataset]:
        dataset_dict: dict[str, HDF5Dataset] = {}
        for group in self.groups:
            for dataset in group.datasets:
                dataset_dict[dataset.name] = dataset
        return dataset_dict


class Hdf5DataValues(BaseModel):
    # simulation_run_id: str
    # dataset_name: str
    shape: list[int]
    values: list[float]


class BiosimSimulationRunApiRequest(BaseModel):
    name: str  # what does this correspond to?
    simulator: str
    simulatorVersion: str
    maxTime: int  # in minutes
    # email: Optional[str] = None
    # cpus: Optional[int] = None
    # memory: Optional[int] = None (in GB)
