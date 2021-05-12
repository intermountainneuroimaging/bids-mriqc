import json
import logging
import os 
from glob import glob

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
        log.info(f'Parsing {jsons} for metadata')
        for json_file in jsons:
            with open(json_file) as f:
                analysis_to_parse = json.load(f)
                metadata["analysis"]["info"][
                    f"{os.path.basename(json_file)}"
                ] = _create_nested_metadata(analysis_to_parse)
    return metadata

def _find_files(hierarchy, output_analysis_id_dir):
    if hierarchy['run_level'] == 'project':
        path_to_jsons = os.path.join(
            output_analysis_id_dir,
            'sub*',
            'ses*',
            "*/*.json"
        )
    else:
        path_to_jsons = os.path.join(output_analysis_id_dir, '*.json')
    jsons = glob(path_to_jsons)
    try:
        # Throw IndexError for no files
        jsons[0]
    except IndexError:
        log.info('Did not find MRIQC output jsons to harvest.')
        log.debug(f"Missing info for metadata. Checked here: \n {path_to_jsons}")

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
    return add_metadata
