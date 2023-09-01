#!/usr/bin/env python
"""The run script."""
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import List, Tuple, Union

from flywheel_bids_app_toolkit import BIDSAppContext

# This design with the main interfaces separated from a gear module (with main and
# parser) allows the gear module to be publishable, so it can then be imported in
# another project, which enables chaining multiple gears together.
from flywheel_bids_app_toolkit.commands import generate_command, run_bids_algo

from flywheel_bids_app_toolkit.prep import get_fw_details
from flywheel_bids_app_toolkit.report import package_output, save_metadata

from flywheel_gear_toolkit import GearToolkitContext


from fw_gear_bids_app_template.main import setup_bids_env, tweak_command
from fw_gear_bids_app_template.parser import parse_config
from fw_gear_bids_app_template.utils.dry_run import pretend_it_ran

log = logging.getLogger(__name__)

# pylint: disable=too-many-locals,too-many-statements
def main(gear_context: GearToolkitContext) -> None:
    """Parses config and runs."""
    warnings = []
    destination, gear_builder_info, container = get_fw_details(gear_context)
    # Setup FreeSurfer, BIDSAppContext, and download BIDS data
    app_context, errors = setup_bids_env(gear_context)
    debug, config_options = parse_config(gear_context)
    command = generate_command(app_context)

    if config_options:
        # Use tweak_command to modify the BIDS app command if there are
        # specific ways that this BIDS app is called.
        command = tweak_command(command)

    if len(errors) > 0:
        e_code = 1
        log.info(
            f"{app_context.bids_app_binary} was NOT run because of previous errors."
        )

    elif app_context.gear_dry_run:
        e_code = 0
        pretend_it_ran(app_context)
        save_metadata(
            gear_context,
            app_context.analysis_output_dir / app_context.bids_app_binary,
            app_context.bids_app_binary,
            {"dry-run": "true"},
        )
        e = "gear-dry-run is set: Command was NOT run."
        log.warning(e)
        warnings.append(e)

    else:
        try:
            # Pass the args, kwargs to fw_gear_qsiprep.main.run function to execute
            # the main functionality of the gear.
            e_code = run_bids_algo(app_context, command)

        except RuntimeError as exc:
            e_code = 1
            errors.append(str(exc))
            log.critical(exc)
            log.exception("Unable to execute command.")

        else:
            # We want to save the metadata only if the run was successful.
            # We want to save partial outputs in the event of the app crashing, because
            # the partial outputs can help pinpoint what the exact problem was. So we
            # have `post_run` further down.
            save_metadata(
                gear_context,
                app_context.analysis_output_dir / app_context.bids_app_binary,
                app_context.bids_app_binary,
            )

    # Clean up, move all results to the output directory.
    # post_run should be run regardless of dry-run or exit code.
    # It will be run even in the event of an error, so that the partial results are
    # available for debugging.
    package_output(
        app_context,
        gear_name=gear_context.manifest["name"],
        errors=errors,
        warnings=warnings,
    )

    log.info("%s Gear is done.  Returning %s", container, e_code)

    # Exit the python script (and thus the container) with the exit
    # code returned by fw_gear_bids_app_template.main.run function.
    sys.exit(e_code)


# pylint: enable=too-many-locals,too-many-statements


# Only execute if file is run as main, not when imported by another module
if __name__ == "__main__":  # pragma: no cover
    # Get access to gear config, inputs, and sdk client if enabled.
    with GearToolkitContext() as gear_context:
        # Initialize logging, set logging level based on `debug` configuration
        # key in gear config.
        gear_context.init_logging()

        # Pass the gear context into main function defined above.
        main(gear_context)
