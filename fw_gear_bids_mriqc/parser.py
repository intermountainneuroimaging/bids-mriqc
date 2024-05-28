"""Parser module to parse gear config.json."""

import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, Tuple

from flywheel_bids.flywheel_bids_app_toolkit import BIDSAppContext
from flywheel_bids.flywheel_bids_app_toolkit.compression import unzip_archive_files
from flywheel_gear_toolkit import GearToolkitContext


log = logging.getLogger(__name__)


# This function mainly parses gear_context's config.json file and returns relevant
# inputs and options.
def parse_config(
    gear_context: GearToolkitContext,
) -> Tuple[bool, Dict]:
    """Search config for extra settings not used by BIDSAppContext.

    Args:
        gear_context (GearToolkitContext):

    Returns:
        debug (bool): Level of gear verbosity
        config_options (Dict): other config options explicitly called out
                in the manifest, not encapsulated by the bids_app_command
                field. The bids_app_command field is intended to handle the
                majority of the use cases to run the BIDS app.
    """

    debug = gear_context.config.get("debug")
    config_options = {}
    for key, val in gear_context.config.items():
        if (
            not key.startswith("gear-")
            and key
            not in [
                "debug",
                "bids_app_command",
            ]
            and val
        ):
            config_options[key] = gear_context.config.get(key)

    return debug, config_options


def parse_input_files(gear_context: GearToolkitContext, app_context: BIDSAppContext):
    """Fetch the input files from the manifest and return the filepaths.

    Grab the manifest blob for inputs. Refine to only file inputs and create a
    key-value pair entry in the input_files dictionary. Best practice design will be
    to use the kwarg in the BIDS App command as the input file label (key).
    """
    inputs = gear_context.manifest.get("inputs")
    input_files = defaultdict()
    if inputs:
        for i in [k for k in inputs.keys() if k not in ["archived_runs"]]:
            if inputs[i]["base"] == "file" and gear_context.get_input_path(i):
                input_files[i] = gear_context.get_input_path(i)

    return input_files
