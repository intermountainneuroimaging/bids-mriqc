"""Main methods that can be customized to run setup and run the BIDS App."""

import logging
from typing import Dict, List, Tuple

from flywheel_bids.flywheel_bids_app_toolkit import BIDSAppContext
from flywheel_bids.flywheel_bids_app_toolkit.commands import (
    clean_generated_bids_command,
)
from flywheel_bids.flywheel_bids_app_toolkit.prep import (
    get_bids_data,
    set_participant_info_for_command,
)
from flywheel_bids.flywheel_bids_app_toolkit.utils.query_flywheel import (
    copy_bidsignore_file,
)
from flywheel_gear_toolkit import GearToolkitContext
from flywheel_gear_toolkit.interfaces.command_line import build_command_list
from flywheel_gear_toolkit.licenses.freesurfer import install_freesurfer_license
from flywheel_gear_toolkit.utils.file import sanitize_filename

log = logging.getLogger(__name__)


def setup_bids_env(gear_context: GearToolkitContext, app_context: BIDSAppContext, find_fs_license: bool = True) -> List:
    """Checks pre-requisites to run the BIDS App.

    Pre-requisites include:
        FreeSurfer license, instantiation of the BIDSAppContext, and
         BIDS data downloads.

    Args:
           gear_context: GearToolkitContext object
           app_context: BIDSAppContext,
           find_fs_license (boolean): Toggle the methods to hunt down
                and/or copy FreeSurfer license information
    Returns:
        errors (list): Non-validator errors that occurred while trying
                    to download BIDS data.
    """
    # Check for FreeSurfer license, if the algorithm uses it.
    if find_fs_license:
        install_freesurfer_license(gear_context)

    tree_title = f"{sanitize_filename(app_context.bids_app_binary)} BIDS Tree"

    if app_context.post_processing_only or app_context.gear_dry_run:
        skip_download = True
    else:
        skip_download = False

    participant_info, errors = get_bids_data(
        gear_context,
        app_context.bids_app_data_types,
        tree_title=tree_title,
        skip_download=skip_download,
    )

    # Any run through BIDS validator needs a .bidsignore file, if the user
    # wants to skip dirs or files en masse.
    copy_bidsignore_file(app_context.bids_dir, "/flywheel/v0/input")

    if app_context.analysis_level == "participant":
        # Ensure that the "sub-" prefix is appropriately (not) used for the algo command
        set_participant_info_for_command(app_context, participant_info)

    return errors


def customize_bids_command(command: List[str], config_options: Dict) -> List[str]:
    """
    Any special adjustments that a given BIDS app may have for the command are
    completed here.
    See flywheel_bids.flywheel_bids_app_toolkit.commands.clean_generated_bids_command
    for examples.

    Args:
        command (List): Command previously generated from the config.json by
            the GearToolkit, which would run the BIDS App, but will now have
            modifications.
        config_options (Dict): Dict formed from specific fields that were
            added to the manifest for this BIDS App (rather than relying on
            the `bids_app_command` field).
    Returns:
        command (List): The modified BIDS App command that will be sent to
            the algorithm.
    """
    cmd = build_command_list(command, config_options)
    cmd = clean_generated_bids_command(cmd)
    log.info("UPDATED command is: %s", str(cmd))
    return cmd
