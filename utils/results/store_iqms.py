import json
import logging
import os.path as op
import glob

from utils.fly.dev_helpers import determine_dir_structure

log = logging.getLogger(__name__)


def store_iqms(output_analysis_id_dir):
    """
    MRIQC calculates 56 anatomical features and numerous functional
    features to characterize quality. These features are called Image
    Quality Metrics (IQMs).
    Grab the IQM values from the analysis and add them to metadata.json
    for inclusion on the "Custom Information" tab as a table.
    Args:
        output_analysis_id_dir (filepath): output file structure ending with output > destination_id
    Returns
        nested dict to add to metadata.json
    """

    metadata = {}
    metadata.setdefault("analysis", {}).setdefault("info", {})
    files = _find_files(output_analysis_id_dir, "json")
    if files:
        for analysis in files:
            with open(analysis) as f:
                analysis_to_parse = json.loads(f.read())
                try:
                    metadata["analysis"]["info"][
                        f"{op.basename(analysis)}"
                    ] = _create_nested_metadata(analysis_to_parse)
                except json.decoder.JSONDecodeError:
                    log.info(f"{analysis} was empty")
    return metadata


def _find_files(output_analysis_id_dir, ext):
    """
    Locates analysis output. Assumes naming scheme follows BIDS format.
        output_analysis_id_dir (path): path including the destination id for project
        level analyses; avoids internal call to get the destination id of the container.
    Args:
        output_analysis_id_dir (filepath): Flywheel env, MRIQC output file path
        ext (str) : .json or .csv, depending on the analysis level being summarized.
    Raises:
        IndexError: If no subject-level files are available in the path specified,
        there is no data that can be harvested for metadata. May need to check the
        path or see if the analysis was not completed.
    """
    try:
        files = glob.glob(op.join(output_analysis_id_dir, "**/*" + ext), recursive=True)
        files[0]  # Throw exception if empty list
        list_of_files = "\n  ".join(files)
        log.info(f"Found IQM files:\n  {list_of_files}")
        return files
    except IndexError:
        log.info("Did not find MRIQC output files to harvest.")
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
    toss_keys.extend(["bids_meta", "provenance", "bids_name"])

    add_metadata = {}

    for k, v in analysis_to_parse.items():
        if k not in toss_keys:
            add_metadata[k] = v
    log.debug(f"Passing {len(add_metadata)} IQM items to metadata.")
    return add_metadata
