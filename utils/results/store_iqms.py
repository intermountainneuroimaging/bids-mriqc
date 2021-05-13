import json
import logging
import os 
from glob import glob

from utils.fly.dev_helpers import determine_dir_structure

log = logging.getLogger(__name__)

def store_iqms(hierarchy, output_analysis_id_dir):
    """
    MRIQC calculates 56 anatomical features and numerous functional
    features to characterize quality. These features are called Image
    Quality Metrics (IQMs).
    Grab the IQM values from the analysis and add them to metadata.json
    for inclusion on the "Custom Information" tab as a table.
    Args:
        hierarchy (dict): Information about the type of analysis and labels.
        output_analysis_id_dir (filepath): output file structure ending with output > destination_id
    Returns
        nested dict to add to metadata.json
    """

    metadata = {}
    metadata.setdefault("analysis", {}).setdefault("info", {})
    jsons = _find_files(hierarchy, output_analysis_id_dir)
    if jsons:
        for json_file in jsons:
            with open(json_file) as f:
                try:
                    analysis_to_parse = json.loads(f.read())
                    metadata["analysis"]["info"][
                        f"{os.path.basename(json_file)}"
                    ] = _create_nested_metadata(analysis_to_parse)
                except json.decoder.JSONDecodeError:
                    log.info(f'{json_file} was empty')
    return metadata

def _find_files(hierarchy, output_analysis_id_dir):
    """
    Locates analysis output. Assumes naming scheme follows BIDS format.
        hierarchy (dict): from get_run_level_and_hierarchy ultimately. Dictionary
        describes aspects of the analysis, including project, participant, or session
        level used here to differentiate where to look for jsons.
        output_analysis_id_dir (path): path including the destination id for project
        level analyses; avoids internal call to get the destination id of the container.
    Raises:
        IndexError: If no subject-level jsons are available in the path specified,
        there is no data that can be harvested for metadata. May need to check the
        path or see if the analysis was not completed.
    """
    if hierarchy['run_level'] == 'project':
        #Functional 5.13.21
        path_to_jsons = os.path.join(
            output_analysis_id_dir,
            'sub*',
            'ses*',
            "*/sub*.json"
        )
    else:
        path_to_jsons = os.path.join(output_analysis_id_dir, 'sub*.json')
    jsons = glob(path_to_jsons, recursive=True)
    try:
        jsons[0]
        list_of_files='\n  '.join(jsons)
        log.info(f"Found:\n  {list_of_files}")
        return jsons
    except IndexError:
        log.info('Did not find MRIQC output jsons to harvest.')
        log.debug(f"Missing info for metadata. Checked here: \n {path_to_jsons}")
        log.debug(determine_dir_structure(output_analysis_id_dir))

def _create_nested_metadata(analysis_to_parse):
    """
    Sift through the json files that correspond with different types of scans. Keep the
    fields associated with IQMs for MRIQC. Reorder the fields for export to metadata.json
    Args:
        analysis_to_parse (dict): converted from original analyses' output json summaries
    Returns:
        add_metadata (nested dict): dictionary to append to metadata under the analysis >
        info > sorting_classifier (filename) entry
    """

    toss_keys = [k for k in analysis_to_parse.keys() if k.startswith("__")]
    toss_keys.extend(["bids_meta", "provenance"])

    add_metadata = {}

    for k, v in analysis_to_parse.items():
        if k not in toss_keys:
            labels = k.split("_")
            if len(labels) == 3:
                add_metadata.setdefault(labels[0], {}).setdefault(labels[1], {})[
                    labels[2]
                ] = v
            elif len(labels) == 2:
                add_metadata.setdefault(labels[0], {})[labels[1]] = v
            else:
                add_metadata[labels[0]] = v
    log.debug(f'Passing {len(add_metadata)} IQM items to metadata.')
    return add_metadata
