import json
import logging
import os.path as op
from collections import defaultdict
from pathlib import Path

import flywheel
from flywheel_bids.flywheel_bids_app_toolkit import BIDSAppContext
from flywheel_bids.flywheel_bids_app_toolkit.utils.helpers import (
    determine_dir_structure,
)
from flywheel_bids.flywheel_bids_app_toolkit.utils.query_flywheel import find_associated_bids_acqs
from flywheel_gear_toolkit import GearToolkitContext

log = logging.getLogger(__name__)


def filter_fw_files(bids_name, acqs: list):
    """
    Args:
        bids_name (str): most of the filename that needs
                to match the BIDS filename in BIDS.info
        acqs (list): List of fw acquisition objects
    Returns:
        acquisition and file objects matching the original
                image file on which the metrics were completed.

    """
    for acq in acqs:
        for f in acq.files:
            if f.info.get("BIDS"):
                if bids_name in f.info.get("BIDS").get("Filename") and "nii" in f.name:
                    return acq, f


def store_iqms(gear_context: GearToolkitContext, bids_app_context: BIDSAppContext) -> dict:
    """MRIQC calculates 56 anatomical features and numerous functional
    features to characterize quality. These features are called Image
    Quality Metrics (IQMs).
    This method will grab the IQM values from the analysis and add them
    to metadata.json for inclusion on the "Custom Information" tab as a table.

    Args:
        gear_context (GearToolkitContext): Gear gear_context for writing
                    metadata to source output_files.
        bids_app_context (BIDSAppContext): information specific to this
                    BIDS app and gear run

    """
    log.debug("Searching for IQMS to update metadata.")
    json_files = _find_output_files(bids_app_context.analysis_output_dir, "json")
    metadata_to_upload = defaultdict(dict)

    if json_files:
        for json_file in json_files:
            log.debug(f"Parsing {json_file}")
            json_data = _parse_json_file(json_file)

            bids_acquisitions = find_associated_bids_acqs(gear_context)
            try:
                fw_parent, fw_file = filter_fw_files(Path(json_file).stem, bids_acquisitions)
                if fw_file:
                    _update_fw_file(fw_file, json_data)
                else:
                    _add_metadata_to_upload(metadata_to_upload, json_file, json_data)
            except TypeError:
                log.info(
                    f"find_fw_file did not return any matching, " f"analyzed acquisitions for {Path(json_file).stem}"
                )

    if metadata_to_upload:
        _upload_metrics(bids_app_context, metadata_to_upload)


def _add_metadata_to_upload(metadata_to_upload: dict, json_file: str, json_data: dict):
    metadata_dict = _create_nested_metadata(json_data)
    metadata_dict["filename"] = Path(json_file).stem
    metadata_to_upload["analysis"]["info"]["derived"]["IQM"].append(metadata_dict)


def _create_nested_metadata(data_to_parse):
    """
    Sift through the json files that correspond with different types of scans. Keep the
    fields associated with IQMs for MRIQC. Reorder the fields for export to
    metadata.json
    Args:
        data_to_parse (dict): converted from original analyses' output json summaries
    Returns:
        add_metadata (dict): dictionary to append to metadata under the analysis >
        info > sorting_classifier (filename) entry
    """

    toss_keys = [k for k in data_to_parse.keys() if k.startswith("__")]
    toss_keys.extend(["bids_meta", "provenance"])

    add_metadata = {}

    for k, v in data_to_parse.items():
        if k not in toss_keys:
            add_metadata[k] = v
    # Should be roughly 68 metrics. See https://mriqc.readthedocs.io/en/latest/measures.html
    log.debug(f"Passing {len(add_metadata)} IQM items to metadata.")
    return add_metadata


def _find_output_files(analysis_output_dir, ext):
    """
    Locates analysis output. Assumes naming scheme follows BIDS format.
        analysis_output_dir (path): path including the destination id for project
        level analyses; avoids internal call to get the destination id of the container.
    Args:
        analysis_output_dir (filepath): fw env, MRIQC output file path
        ext (str) : .json or .csv, depending on the analysis level being summarized.
    Raises:
        IndexError: If no subject-level files are available in the path specified,
        there is no data that can be harvested for metadata. May need to check the
        path or see if the analysis was not completed.
    """
    try:
        files = [
            f
            for f in Path(analysis_output_dir).rglob("**/*" + ext)
            if not op.basename(f).startswith("._") and not op.basename(f).startswith("dataset")
        ]
        if len(files) > 0:  # Throw exception if empty list
            list_of_files = "\n  ".join([str(f) for f in files])
            log.info(f"Found IQM files:\n  {list_of_files}")
            return files
        else:
            log.info("Did not find MRIQC output files to harvest.")
            log.debug(determine_dir_structure(analysis_output_dir))
    except Exception as e:
        log.error(e)


def _parse_json_file(json_file: str) -> dict:
    """Extract the MRIQC metadata from the json."""
    with open(json_file) as f:
        try:
            json_data = json.loads(f.read())
        except json.decoder.JSONDecodeError:
            log.info(f"{json_file} was empty")
            return {}
    return json_data


def _update_fw_file(fw_file: flywheel.FileEntry, json_data: dict):
    """Add the metadata to the system"""
    fw_file.update_info({"derived": {"IQM": _create_nested_metadata(json_data)}})
    log.info(f"Updated {fw_file.name}")


def _upload_metrics(app_context, metadata_to_upload):
    """Push MRIQC metrics an output JSON."""
    # Save the .metadata.json
    with open(f"{app_context.output_dir}/.metadata.json", "w") as fff:
        json.dump(metadata_to_upload, fff)
    log.debug(f"Metadata = \n{metadata_to_upload}")
    log.info(f"Wrote {app_context.output_dir}/.metadata.json")
