import traceback
from enum import Enum, EnumMeta
from typing import *
from pprint import pformat

import numpy as np
import h5py


__all__ = [
    'handle_sbml_exception',
    'printc',
    'visit_datasets',
    'stdout_colors'

]


def stdout_colors():
    # ANSI colors TODO: add more
    class StdoutColors(Enum):
        SKY_BLUE = "\033[38;5;117m"
        LIGHT_PURPLE = "\033[38;5;183m"
        ERROR_RED = "\033[31m"
        CURSOR_YELLOW = "\033[33m"
        MAGENTA = "\033[35m"
        RESET = "\033[0m"
    return StdoutColors


def visit_datasets(
        group: Union[h5py.File, h5py.Group],
        group_path: Optional[str] = None
) -> dict[str, np.ndarray]:
    matching_datasets = {}
    for name, obj in group.items():
        gp = group_path or ""
        full_path = f"{group_path}/{name}" if group_path else name
        if "report" in full_path:
            matching_datasets[full_path] = obj[()]
        else:
            if isinstance(obj, h5py.Group):
                matching_datasets.update(visit_datasets(obj, full_path))
    return matching_datasets


def handle_sbml_exception() -> str:
    tb_str = traceback.format_exc()
    error_message = pformat(f"time-course-simulation-error:\n{tb_str}")
    return error_message


def printc(msg: Any, alert: str = '', error=False):
    StdoutColors = stdout_colors()
    prefix = f"{StdoutColors.CURSOR_YELLOW.value if not error else StdoutColors.ERROR_RED.value}{alert if not error else 'AN ERROR OCCURRED'}:{StdoutColors.RESET.value}"
    message = f"{StdoutColors.SKY_BLUE.value if not error else StdoutColors.ERROR_RED.value}{msg}{StdoutColors.RESET.value}\n"
    content = f"{StdoutColors.MAGENTA.value}>{StdoutColors.RESET.value} "
    if alert:
        content += f"{prefix} {message}"
    else:
        content += f" {message}"
    print(content)


# -- original read report method from bio-check/worker --
# def __read_report_outputs(report_file_path: str, dataset_label: str = None):
# from dataclasses import dataclass
#     @dataclass
#     class BiosimulationsReportOutput:
#         dataset_label: str
#         data: np.ndarray
#
#     @dataclass
#     class BiosimulationsRunOutputData:
#         report_path: str
#         data: List[BiosimulationsReportOutput]
#
#     outputs = []
#     with h5py.File(report_file_path, 'r') as f:
#         k = list(f.keys())
#         group_path = k[0] + '/report'
#         if group_path in f:
#             group = f[group_path]
#             label = dataset_label or 'sedmlDataSetLabels'
#             dataset_labels = group.attrs[label]
#             for label in dataset_labels:
#                 dataset_index = list(dataset_labels).index(label)
#                 data = group[()]
#                 specific_data = data[dataset_index]
#                 output = BiosimulationsReportOutput(dataset_label=label, data=specific_data)
#                 outputs.append(output)
#
#             return BiosimulationsRunOutputData(report_path=report_file_path, data=outputs)
#         else:
#             return {'report_path': report_file_path, 'data': f"Group '{group_path}' not found in the file."}

