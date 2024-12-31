__all__ = [
    'SEDMLReportDataSet',
    'SimulatorReportData',
    'ReportDataSetPath',
    'SBMLSpeciesMapping',
]


class SEDMLReportDataSet(dict):
    pass


class SimulatorReportData(dict):
    pass


class ReportDataSetPath(str):
    pass


class SBMLSpeciesMapping(dict):
    pass


STATUS_SCHEMA = {
    "$run_id(str)": {
        "status": "str",
        "out_dir": "PathLike[str]",
        "simulator": "Simulator"
    }
}

