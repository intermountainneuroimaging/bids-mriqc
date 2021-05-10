import json
import logging
import os.path as op
from glob import glob
from utils.bids.run_level import get_run_level_and_hierarchy

log = logging.getLogger(__name__)


def store_iqms(context, destination_id):
    """
    MRIQC calculates 56 anatomical features and numerous functional
    features to characterize quality. These features are called Image
    Quality Metrics (IQMs).
    Grab the IQM values from the analysis and add them to .metadata.json
    for inclusion on the "Custom Information" tab as a table.
    Args:
        context (Geartoolkit context): Flywheel gear context
        destination_id (id): analysis container within Flywheel
    Returns
        nested dict to convert to .metadata.json
    """

    hierarchy = get_run_level_and_hierarchy(context.client, destination_id)
    metadata = {}
    metadata.setdefault("analysis", {}).setdefault("info", {})
    path_to_jsons = op.join(
        context.output_dir,
        destination_id,
        hierarchy["subject_label"],
        hierarchy["session_label"],
        "*/*.json",
    )
    jsons = glob(path_to_jsons)
    if jsons:
        for json_file in jsons:
            with open(json_file) as f:
                analysis_to_parse = json.load(f)
                metadata["analysis"]["info"][
                    f"{op.basename(json_file)}"
                ] = _create_nested_metadata(analysis_to_parse)
        return metadata
    else:
        log.debug(f"Missing info for metadata. Checked here: \n {path_to_jsons}")


def _create_nested_metadata(analysis_to_parse):
    """

    Args:

    """
    toss_keys = [k for k in analysis_to_parse.keys() if k.startswith("__")]
    toss_keys.extend(["bids_meta", "provenance"])

    add_metadata = {}

    for k, v in analysis_to_parse.items():
        if k not in toss_keys:
            try:
                labels = k.split("_")
                if len(labels) == 3:
                    add_metadata.setdefault(labels[0], {}).setdefault(labels[1], {})[
                        labels[2]
                    ] = v
                elif len(labels) == 2:
                    add_metadata.setdefault(labels[0], {})[labels[1]] = v
                else:
                    add_metadata[labels[0]] = v
            except Exception as e:
                print(e)
    return add_metadata
