#!/usr/bin/env python
"""The run script."""

import logging
import os
import sys
import shutil
import tempfile
#
from flywheel_bids.flywheel_bids_app_toolkit import BIDSAppContext

# This design with the main interfaces separated from a gear module (with main and
# parser) allows the gear module to be publishable, so it can then be imported in
# another project, which enables chaining multiple gears together.
from flywheel_bids.flywheel_bids_app_toolkit.commands import generate_bids_command
from flywheel_bids.flywheel_bids_app_toolkit.hpc_utils import check_and_link_dirs, remove_tmp_dir
from flywheel_bids.flywheel_bids_app_toolkit.report import package_output, save_metadata
from flywheel_bids.flywheel_bids_app_toolkit.utils.helpers import check_bids_dir
from flywheel_bids.flywheel_bids_app_toolkit.utils.query_flywheel import get_fw_details
from flywheel_gear_toolkit import GearToolkitContext

from fw_gear_bids_mriqc.main import customize_bids_command, setup_bids_env, run_bids_algo
from fw_gear_bids_mriqc.parser import parse_config, parse_input_files
from fw_gear_bids_mriqc.utils.dry_run import pretend_it_ran
from fw_gear_bids_mriqc.utils.helpers import analyze_participants, extra_post_processing, validate_setup
from fw_gear_bids_mriqc.utils.singularity import run_in_tmp_dir

log = logging.getLogger(__name__)

os.chdir('/flywheel/v0')

def main(gear_context: GearToolkitContext) -> None:
    """Main orchestrating method.

    Section 1: Set up the Docker gear_name_and_version with all the env variables,
    licenses, and BIDS data.

    Section 2: Parse the commandline input provided via the config.json
    under the "bids_app_command" field. If the BIDS App has idiosyncrasies
    in the formatting of kwargs or required custom fields in the manifest
    for the config, then the output from the standard `generate_command`
    method (from `flywheel_bids_app_toolkit`) is amended. If possible,
    design the manifest to highlight inputting the command over breaking
    out the individual args and kwargs, as this strategy will be more flexible
    and maintainable between versions. As a bonus, much of the testing can be
    handled within flywheel_bids_app_toolkit if this strategy is employed.

    Section 3: Handle dry-runs, BIDS download (not validation) errors, and
    actual algorithm runs.

    Section 4: Zip the html, result, and other files so the gear_name_and_version can
    spin down gracefully and provide the analysis for review and future use.
    """

    # BIDSAppContext parses the config and populates the BIDS_app_context
    # with bids_app_context, directories, and performance settings.
    # While mirroring GTK context, this object is specifically for
    # BIDS apps and contains the building blocks for command execution.
    app_context = BIDSAppContext(gear_context)

    validate_setup(gear_context, app_context)

    # Make sure that all the BIDS app directories are writable (for HPC)
    # check_and_link_dirs also checks/updates FreeSurfer before setup_bids_env
    check_and_link_dirs(gear_context)

    # Section 1: Set up
    # Collect information related specifically to Flywheel
    destination, gear_builder_info, gear_name_and_version = get_fw_details(gear_context)

    # BIDSAppContext, and download BIDS data, skip freesufer - not required for mriqc
    errors = setup_bids_env(gear_context, app_context, find_fs_license = False)
    debug, config_options = parse_config(gear_context)
    # If archived runs or other configuration files are allowed in the input tab of
    # the UI, consider using the following method to make the filepaths available to
    # match with kwargs in the bids_app_command
    input_files = parse_input_files(gear_context, app_context)

    if input_files and config_options:
        # Replace any of the common keys with the Flywheel filepaths from
        # get_input_path() (from `parser.parse_input_files`)
        config_options.update(input_files)
    elif input_files:
        # Use all the magic of `build_command_list` on the input file entries anyway
        config_options = input_files

    # Section 2: Parse command line
    if app_context.post_processing_only:
        e_code = 0
        if destination.parent.type == "project":
            # Unzipped, previous project results may have the
            # dataset_description and BIDS dir buried one level.
            check_bids_dir(app_context)
        else:
            app_context.analysis_output_dir = app_context.bids_dir
    else:
        command = generate_bids_command(app_context)

        if config_options:
            # Use customize_bids_command to modify the BIDS app command if there are
            # specific ways that this BIDS app is called.
            command = customize_bids_command(command, config_options)

        # Section 3
        if len(errors) > 0:
            e_code = 1
            log.info(f"{app_context.bids_app_binary} was NOT run because of previous errors.")

        elif app_context.gear_dry_run:
            e_code = 0
            pretend_it_ran(app_context, command)
            save_metadata(
                gear_context,
                app_context.analysis_output_dir / app_context.bids_app_binary,
                app_context.bids_app_binary,
                {"dry-run": "true"},
            )
            e = "gear-dry-run is set: Command was NOT run."
            log.warning(e)

        else:
            try:
                # Pass the args, kwargs to fw_gear_qsiprep.main.run function to execute
                # the main functionality of the gear.

                # Start with running all participants, if at the group level
                if destination.parent.type == "project":
                    e_code = analyze_participants(app_context, command)
                    # Due to the bug, specify the modalities to summarize
                    # and pass the modified command to run_bids_algo
                    log.warning(
                        "MRIQC 23.1.0 has a bug #1128 in dwi group level processing.\n"
                        "Please wait for the next official release to fix "
                        "DWI summaries."
                    )
                    command.extend(["-m", "T1w T2w bold"])

                # matplotlib workaround for multiple runs on same hpc node
                if 'MPLCONFIGDIR' not in os.environ or os.environ['MPLCONFIGDIR'].startswith('/home'):
                    os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp(prefix='MPLCONFIGDIR-', dir=app_context.work_dir)

                os.environ['SINGULARITYENV_TEMPLATEFLOW_HOME'] = tempfile.mkdtemp(prefix='TEMPLATEFLOW-', dir=app_context.work_dir)
                os.environ['TEMPLATEFLOW_HOME'] = os.environ['SINGULARITYENV_TEMPLATEFLOW_HOME']

                # Run either the 'participant' or 'group' version of the command
                # as originally specified by the command.
                # This will run the group summaries, if 'group', or the participant
                # analysis, if 'participant'
                e_code = run_bids_algo(gear_context, app_context, command)

            except RuntimeError as exc:
                e_code = 1
                errors.append(str(exc))
                log.critical(exc)
                log.exception("Unable to execute command.")

    if e_code == 0:
        # Section 4
        # Clean up, move all results to the output directory.
        # post_run should be run regardless of dry-run or exit code.
        # It will be run even in the event of an error, so that the partial results are
        # available for debugging.
        extra_post_processing(gear_context, app_context)

        package_output(app_context, gear_name=gear_context.manifest["name"], errors=errors)

    log.info("%s Gear is done.  Returning %s", gear_name_and_version, e_code)

    return e_code


# Only execute if file is run as main, not when imported by another module
if __name__ == "__main__":  # pragma: no cover

    # move the singularity check inside one level where the centext is available to check which directory should be made /tmp
    with GearToolkitContext() as gear_context:
        scratch_dir = run_in_tmp_dir(gear_context.config["gear-writable-dir"])

    # Get access to gear config, inputs, and sdk client if enabled.
    with GearToolkitContext() as gear_context:
        # Initialize logging, set logging level based on `debug` configuration
        # key in gear config.
        gear_context.init_logging()

        # Pass the gear context into main function defined above.
        return_code = main(gear_context)

        # clean up (might be necessary when running in a shared computing environment)
        if scratch_dir:
            log.debug("Removing scratch directory")
            for thing in scratch_dir.glob("*"):
                if thing.is_symlink():
                    thing.unlink()  # don't remove anything links point to
                    log.debug("unlinked %s", thing.name)
            shutil.rmtree(scratch_dir)
            log.debug("Removed %s", scratch_dir)

        # Exit the python script (and thus the gear_name_and_version) with the exit
        # code returned by fw_gear_bids_mriqc.main.run function.
        sys.exit(return_code)
