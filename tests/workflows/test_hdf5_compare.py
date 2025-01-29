from pathlib import Path

from biosim_server.workflows.verify.hdf5_compare import get_results, compare_arrays, compare_datasets

def test_compare_arrays() -> None:
    results_zip: Path = Path(__file__).parent.parent / "fixtures" / "local_data" / "modeldb-206365-outputs.zip"
    results1 = get_results(results_zip_file=results_zip)
    results2 = get_results(results_zip_file=results_zip)

    assert compare_arrays(
        results1["outputs/reports.h5"]["/Fig. 2/B/Bazh_PY_altKCC2_Ko_Cli_min_burst_Ko_Cli_fix_NEW.sedml/plot"],
        results2["outputs/reports.h5"]["/Fig. 2/B/Bazh_PY_altKCC2_Ko_Cli_min_burst_Ko_Cli_fix_NEW.sedml/plot"])

    assert compare_datasets(results1, results2) == (True, 0.0)

    results1["outputs/reports.h5"]["/Fig. 2/B/Bazh_PY_altKCC2_Ko_Cli_min_burst_Ko_Cli_fix_NEW.sedml/plot"][0][0] = 999.0

    assert not compare_arrays(
        results1["outputs/reports.h5"]["/Fig. 2/B/Bazh_PY_altKCC2_Ko_Cli_min_burst_Ko_Cli_fix_NEW.sedml/plot"],
        results2["outputs/reports.h5"]["/Fig. 2/B/Bazh_PY_altKCC2_Ko_Cli_min_burst_Ko_Cli_fix_NEW.sedml/plot"])[0]

    assert compare_datasets(results1, results2) == (False, 99900.0)

    print(results1.keys())
