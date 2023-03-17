import json
import logging
import os.path as op
from collections import defaultdict
from pathlib import Path

import flywheel

from utils.fly.dev_helpers import determine_dir_structure

log = logging.getLogger(__name__)


def find_bids_acqs(context):
    """Search acquisitions for BIDS-related acquisitions.
    Returns list of acquisition objects.
    """
    fw = flywheel.Client(context.get_input("api-key")["key"])
    dest_id = context.destination["id"]
    destination = fw.get(dest_id)
    session = fw.get_session(destination.parents["session"])
    bids_acqs = []
    # TODO figure out how to get the right type that iter_find can operate on, not obj
    for acq in session.acquisitions.iter_find():
        for f in acq.files:
            if f.info.get("BIDS"):
                bids_acqs.append(acq)
    return bids_acqs


def find_fw_file(bids_name, acqs: list):
    """
    Args:
        bids_name (str): most of the filename that needs to match the BIDS filename in BIDS.info
        acqs (list): List of fw acquisition objects
    Returns:
        acquisition and file objects matching the original image file on which the
        metrics were completed.

    """
    for acq in acqs:
        for f in acq.files:
            if bids_name in f.info.get("BIDS").get("Filename") and "nii" in f.name:
                return acq, f


def store_iqms(output_analysis_id_dir, context):
    """
    MRIQC calculates 56 anatomical features and numerous functional
    features to characterize quality. These features are called Image
    Quality Metrics (IQMs).
    Grab the IQM values from the analysis and add them to metadata.json
    for inclusion on the "Custom Information" tab as a table.
    Args:
        output_analysis_id_dir (filepath): output file structure ending with output > destination_id
        context (GearToolkitContext): Gear Context for writing metadata to source output_files.
    Returns
        nested dict to add to metadata.json
    """
    # MRIqc output is stored as json
    output_files = _find_output_files(output_analysis_id_dir, "json")
    bids_acqs = find_bids_acqs(context)
    # Create dictionary, in case metadata is not able to be posted directly to
    # the corresponding file. Note: I can't really think of a time that this is
    # the case. `dataset_description` should be found by the search nor needed
    # as an analysis file to update, so the else loop may not be needed.
    metadata_for_upload = defaultdict()
    if output_files:
        for analysis in output_files:
            log.debug(f"Parsing {analysis}")
            with open(analysis) as f:
                try:
                    data_to_parse = json.loads(f.read())
                except json.decoder.JSONDecodeError:
                    log.info(f"{analysis} was empty")
                    continue
            # Find parent and file in Flywheel based on bids name
            #   How to find will depend on destination parent, project, subject or session.
            parent, fw_file = find_fw_file(
                op.splitext(op.basename(analysis))[0], bids_acqs
            )
            if fw_file:
                # B/c of 'info' being a flywheel.models.info_list_output.InfoListOutput,
                # deep_merge in `update_file` doesn't work.
                fw_file.update_info({"IQM": _create_nested_metadata(data_to_parse)})
                log.info(f"Updated {fw_file.name}")
            else:
                # If file wasn't found in Flywheel (mostly only dataset description)
                update_dict = _create_nested_metadata(data_to_parse)
                update_dict["filename"] = op.splitext(op.basename(analysis))[0]
                metadata_for_upload["analysis"]["info"]["IQM"].append(update_dict)

    if metadata_for_upload:
        return metadata_for_upload
    else:
        return None


def _find_output_files(output_analysis_id_dir, ext):
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
        files = [
            f
            for f in Path(output_analysis_id_dir).rglob("**/*" + ext)
            if not op.basename(f).startswith("._")
        ]
        files[0]  # Throw exception if empty list
        list_of_files = "\n  ".join([str(f) for f in files])
        log.info(f"Found IQM files:\n  {list_of_files}")
        return files
    except IndexError:
        log.info("Did not find MRIQC output files to harvest.")
        log.debug(determine_dir_structure(output_analysis_id_dir))


def _create_nested_metadata(data_to_parse):
    """
    Sift through the json files that correspond with different types of scans. Keep the
    fields associated with IQMs for MRIQC. Reorder the fields for export to metadata.json
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
