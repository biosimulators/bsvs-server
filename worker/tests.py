import uuid

from datagen.biosimulations_runutils.biosim_pipeline import Simulator

from datagen import batch_generate_omex_outputs

BIOMODEL_IDS = [
    'BIOMD0000000013',
    'BIOMD0000000019',
    'BIOMD0000000043',
    'BIOMD0000000044',
    'BIOMD0000000070',
    'BIOMD0000000117',
    'BIOMD0000000211',
    'BIOMD0000000391',
    'BIOMD0000000399',
    'BIOMD0000000633',
    'BIOMD0000000661',
    'BIOMD0000000691',
    'BIOMD0000000728',
    'BIOMD0000000751',
    'BIOMD0000000831',
    'BIOMD0000000844',
    'BIOMD0000000845',
    'BIOMD0000000893',
    'BIOMD0000000900',
    'BIOMD0000000912',
    'BIOMD0000001024',
]


# def batch_generate_omex_outputs(biomodel_ids: list[str]):
#     simulators = list(sorted(Simulator.__members__.keys()))
#     simulators = simulators[int(len(simulators) / 2):len(simulators)]  # latter half of list
#     # simulators = ['vcell']
#
#     buffer = 10
#     test_biomodel_id = biomodel_ids[0]
#     test_biomodel_output_dir = f'./verification_request/results/{test_biomodel_id}'
#
#     data_generator = TimeCourseDataGenerator()
#     omex_outputs = data_generator.generate_omex_output_data(test_biomodel_id, test_biomodel_output_dir, simulators, buffer, use_instance_dir=True)
#
#     printc(omex_outputs.keys(), "The final output keys")
#
#     outputfile_id = min(str(uuid.uuid4()).split('-'))
#     json_fp = f'./verification_request/output_data/{test_biomodel_id}-outputs-{outputfile_id}.json'
#     data_generator.export_data(omex_outputs, json_fp, verbose=True)


def test_generate_omex_outputs():
    simulators = list(sorted(Simulator.__members__.keys()))
    simulators = simulators[int(len(simulators) / 2):len(simulators)]  # latter half of list
    # simulators = ['vcell']

    buffer = 10
    test_biomodel_id = BIOMODEL_IDS[0]
    test_biomodel_output_dir = f'./verification_request/results/{test_biomodel_id}'
    outputfile_id = min(str(uuid.uuid4()).split('-'))
    json_fp = f'./verification_request/output_data/{test_biomodel_id}-outputs-{outputfile_id}.json'
    return batch_generate_omex_outputs(BIOMODEL_IDS, test_biomodel_output_dir, json_fp, simulators, buffer)


# if __name__ == '__main__':
#     test_generate_omex_outputs()
