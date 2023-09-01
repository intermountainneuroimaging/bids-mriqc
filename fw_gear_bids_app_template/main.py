"""Main module."""

import logging
from typing import List, Tuple

from flywheel_bids_app_toolkit import BIDSAppContext
from flywheel_bids_app_toolkit.prep import get_bids_data, set_participant_info
from flywheel_gear_toolkit import GearToolkitContext
from flywheel_gear_toolkit.licenses.freesurfer import install_freesurfer_license
from flywheel_gear_toolkit.utils.file import sanitize_filename


def setup_bids_env(gear_context: GearToolkitContext) -> Tuple[BIDSAppContext, List]:
    """
    Checks pre-requisites to run the BIDS App.
    Pre-requisites include:
        FreeSurfer license, instantiation of the BIDSAppContext, and
         BIDS data downloads.
    Args:
           gear_context: GearToolkitContext object
    Returns:
        app_context (BIDSAppContext): Details about the gear setup and BIDS options
        errors (list): Non-validator errors that occurred while trying
                    to download BIDS data.
    """
    # Check for FreeSurfer license
    install_freesurfer_license(gear_context)

    # BIDSAppContext parses the config and populates the BIDS_app_context
    # with bids_app_context, directories, and performance settings.
    # While mirroring GTK context, this object is specifically for
    # BIDS apps and contains the building blocks for command execution.
    app_context = BIDSAppContext(gear_context)

    tree_title = f"{sanitize_filename(app_context.bids_app_binary)} BIDS Tree"
    participant_info, errors = get_bids_data(
        gear_context,
        app_context.bids_app_modalities,
        tree_title=tree_title,
        dry_run=app_context.gear_dry_run,
    )

    if app_context.analysis_level == "participant":
        app_context = set_participant_info(app_context, participant_info)

    return app_context, errors


def tweak_command(command: List[str], config_options: Dict) -> List[str]:
    """
    Any special adjustments that a given BIDS app may have for the command are completed here.
    See flywheel_bids_app_toolkit.cammonds.clean_generated_command for examples.
    """
    return command
