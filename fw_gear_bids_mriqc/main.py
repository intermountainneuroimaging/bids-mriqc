"""Main methods that can be customized to run setup and run the BIDS App."""

import logging
import os
import shutil
from typing import Dict, List, Tuple
from pathlib import Path

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
from flywheel_gear_toolkit.interfaces.command_line import build_command_list, exec_command
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
    if find_fs_license and hasattr(gear_context, "writable_dir"):
        # explicitly send to writable directory
        install_freesurfer_license(gear_context, gear_context.writable_dir)
    elif find_fs_license:
        log.debug("Writable_dir not set in gear_context. Installing FS license in usual spot.")
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
    if "bidsignore" in gear_context.config_json["inputs"]:
        shutil.copy(
            gear_context.config_json["inputs"]["bidsignore"]["location"]["path"],
            app_context.bids_dir / ".bidsignore",
        )

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


def run_bids_algo(gear_context: GearToolkitContext, app_context: BIDSAppContext, command: List[str]) -> int:
    """Run the algorithm.

    Args:
        app_context (BIDSAppContext): Details about the gear setup and BIDS options
        command (List): BIDS command that has been updated for Flywheel paths and
                        parsed to a comma-separated list

    Returns:
        run_error (int): any error encountered running the app. (0: no error)
    """
    if not Path(app_context.analysis_output_dir).exists():
        # Create output directory
        log.info("Creating output directory %s", app_context.analysis_output_dir)
        Path(app_context.analysis_output_dir).mkdir(parents=True, exist_ok=True)

    # This is what it is all about
    # Turn off logging b/c of log limits and redirect for offline logs
    # Potentially add "> log_file" to the command to hard force the output to log file.
    log_file = Path(app_context.output_dir) / Path(
        app_context.bids_app_binary + "_log.txt"
    )
    # GTK requires str not PosixPath for log_file
    # if log.getEffectiveLevel() == 10:
    # tee may mess up the nipype output entirely.
    #     command.extend(["|", "tee", str(log_file)])
    # else:
    if gear_context.config.get("gear-log-to-file"):
        command.extend([">", str(log_file)])

    stdout, stderr, run_error = exec_command(
        command,
        dry_run=app_context.gear_dry_run,
        environ=os.environ,
        shell=True,
        cont_output=True,
    )
    return run_error