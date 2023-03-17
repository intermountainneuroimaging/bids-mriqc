#!/opt/conda/bin/python
"""Run the gear: set up for and call command-line command."""

import glob
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path

import flywheel_gear_toolkit
import psutil
from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)
from flywheel_gear_toolkit.utils.zip_tools import zip_output

from utils.bids.download_run_level import download_bids_for_runlevel
from utils.bids.run_level import get_run_level_and_hierarchy
from utils.dry_run import pretend_it_ran
from utils.fly.dev_helpers import determine_dir_structure
from utils.fly.make_file_name_safe import make_file_name_safe
from utils.results.store_iqms import store_iqms
from utils.results.zip_htmls import zip_htmls
from utils.results.zip_intermediate import (
    zip_all_intermediate_output,
    zip_intermediate_selected,
)
from utils.singularity import run_in_tmp_dir
# from utils.singularity import (
#     check_for_singularity,
#     log_singularity_details,
#     unlink_gear_mounts,
# )

log = logging.getLogger(__name__)

testing = False

GEAR = "bids-mriqc"
REPO = "flywheel-apps"
CONTAINER = f"{REPO}/{GEAR}]"

# The BIDS App command to run, e.g. "mriqc"
BIDS_APP = "mriqc"

# when downloading BIDS Limit download to specific folders? e.g. ['anat','func','fmap']
DOWNLOAD_MODALITIES = ["anat", "func"]  # empty list is no limit

# Whether or not to include src data (e.g. dicoms) when downloading BIDS
DOWNLOAD_SOURCE = False

# Constants that do not need to be changed
ENVIRONMENT_FILE = "/flywheel/v0/gear_environ.json"


def set_performance_config(config):
    """Set run-time performance config params to pass to BIDS App.

    Set --n_cpus (number of threads) and --mem_gb (maximum memory to use).
    Use the given number unless it is too big.  Use the max available if zero.

    The user may want to set these number to less than the maximum if using a
    shared compute resource.

    Args:
        config (GearToolkitContext.config): run-time options from config.json

    Results:
        sets config["n_cpus"] which will become part of the command line command
        sets config["mem_gb"] which will become part of the command line command
    """

    os_cpu_count = os.cpu_count()
    log.info("os.cpu_count() = %d", os_cpu_count)
    n_cpus = config.get("n_cpus")
    if n_cpus:
        if n_cpus > os_cpu_count:
            log.warning("n_cpus > number available, using max %d", os_cpu_count)
            config["n_cpus"] = os_cpu_count
        else:
            log.info("n_cpus using %d from config", n_cpus)
    else:  # Default is to use all cpus available
        config["n_cpus"] = os_cpu_count  # zoom zoom
        log.info("using n_cpus = %d (maximum available)", os_cpu_count)

    psutil_mem_gb = int(psutil.virtual_memory().available / (1024**3))
    log.info("psutil.virtual_memory().available= {:5.2f} GiB".format(psutil_mem_gb))
    mem_gb = config.get("mem_gb")
    if mem_gb:
        if mem_gb > psutil_mem_gb:
            log.warning("mem_gb > number available, using max %d", psutil_mem_gb)
            config["mem_gb"] = psutil_mem_gb
        else:
            log.info("mem_gb using %d from config", mem_gb)
    else:  # Default is to use all cpus available
        config["mem_gb"] = psutil_mem_gb
        log.info("using mem_gb = %d (maximum available)", psutil_mem_gb)


def get_and_log_environment():
    """Grab and log environment for to use when executing command line.

    The shell environment is saved into a file at an appropriate place in the Dockerfile.
    """
    try:
        with open(ENVIRONMENT_FILE, "r") as f:
            environ = json.load(f)

            # Add environment to log if debugging
            kv = ""
            for k, v in environ.items():
                kv += k + "=" + v + " "
            log.debug("Environment: " + kv)

        return environ
    except FileNotFoundError:
        st = os.stat(os.path.dirname(ENVIRONMENT_FILE))
        log.debug(
            f"{ENVIRONMENT_FILE} not found.\nPermissions for dir are {st.st_mode}"
        )


def generate_command(
    config,
    work_dir,
    output_analysis_id_dir,
    errors,
    warnings,
    analysis_level="participant",
):
    """Build the main command line command to run.

    Args:
        config (GearToolkitContext.config): run-time options from config.json
        work_dir (path): scratch directory where non-saved files can be put
        output_analysis_id_dir (path): directory where output will be saved
        analysis_level (str): toggle between participant- or group-level
        analysis, with participant being the default

    Returns:
        cmd (list of str): command to execute
    """

    # start with the command itself:
    cmd = [BIDS_APP]

    # 3 positional args: bids path, output dir, 'participant'
    # This should be done here in case there are nargs='*' arguments
    # These follow the BIDS Apps definition (https://github.com/BIDS-Apps)
    cmd.append(str(work_dir / "bids"))
    cmd.append(str(output_analysis_id_dir))
    cmd.append(analysis_level)

    # get parameters to pass to the command by skipping gear config parameters
    # (which start with "gear-").
    skip_pattern = re.compile("gear-|lsf-|slurm-|singularity-")

    command_parameters = {}
    log_to_file = False
    for key, val in config.items():
        # these arguments are passed directly to the command as is
        if key == "bids_app_args":
            bids_app_args = val.split(" ")
            for baa in bids_app_args:
                cmd.append(baa)

        elif not skip_pattern.match(key):
            command_parameters[key] = val

    # Validate the command parameter dictionary - make sure everything is
    # ready to run so errors will appear before launching the actual gear
    # code.  Add descriptions of problems to errors & warnings lists.
    # print("command_parameters:", json.dumps(command_parameters, indent=4))

    cmd = build_command_list(cmd, command_parameters)

    for ii, cc in enumerate(cmd):
        if cc.startswith("--verbose"):
            # handle a 'count' argparse argument where manifest gives
            # enumerated possibilities like v, vv, or vvv
            # e.g. replace "--verbose=vvv' with '-vvv'
            cmd[ii] = "-" + cc.split("=")[1]

    log.info("command is: %s", str(cmd))

    return cmd


def main(gtk_context):
    """
    Complete the MRIQC analysis and create results overview.
    Args:
        gtk_context : the gear context
    Returns:
        exit code
    """

    FWV0 = Path.cwd()
    log.info("Running gear in %s", FWV0)

    # Keep a list of errors and warning to print all in one place at end of log
    # Any errors will prevent the command from running and will cause exit(1)
    errors = []
    warnings = []

    output_dir = gtk_context.output_dir
    log.info("output_dir is %s", output_dir)
    work_dir = gtk_context.work_dir
    log.info("work_dir is %s", work_dir)

    # run-time configuration options from the gear's context.json
    config = gtk_context.config
    dry_run = config.get("gear-dry-run")

    # Given the destination container, figure out if running at the project,
    # subject, or session level.
    destination_id = gtk_context.destination["id"]
    hierarchy = get_run_level_and_hierarchy(gtk_context.client, destination_id)

    # This is the label of the project, subject or session and is used
    # as part of the name of the output files.
    run_label = make_file_name_safe(hierarchy["run_label"])

    # Output will be put into a directory named as the destination id.
    # This allows the raw output to be deleted so that a zipped archive
    # can be returned.
    output_analysis_id_dir = gtk_context.output_dir / destination_id

    # set # threads and max memory to use
    set_performance_config(config)

    environ = get_and_log_environment()
    if gtk_context.config["gear-writable-dir"] in str(gtk_context.output_dir):
        log.debug(type(environ))
        log.debug(environ["HOME"])
        environ["HOME"] = gtk_context.config["gear-writable-dir"] + "/bidsapp"

    command = generate_command(
        config, gtk_context.work_dir, output_analysis_id_dir, errors, warnings
    )

    # This is used as part of the name of output files
    command_name = make_file_name_safe(command[0])

    # Download BIDS Formatted data
    if len(errors) == 0:
        # Create HTML file that shows BIDS "Tree" like output
        tree = True
        tree_title = f"{command_name} BIDS Tree"

        error_code = download_bids_for_runlevel(
            gtk_context,
            hierarchy,
            tree=tree,
            tree_title=tree_title,
            src_data=DOWNLOAD_SOURCE,
            folders=DOWNLOAD_MODALITIES,
            dry_run=dry_run,
            do_validate_bids=config.get("gear-run-bids-validation"),
        )
        if error_code > 0 and not config.get("gear-ignore-bids-errors"):
            errors.append(f"BIDS Error(s) detected.  Did not run {CONTAINER}")

    else:
        log.info("Did not download BIDS because of previous errors")
        print(errors)

    # Don't run if there were errors or if this is a dry run
    return_code = 0

    if len(errors) > 0:
        return_code = 1
        log.info("Command was NOT run because of previous errors.")

    try:
        if dry_run:
            ok_to_run = False
            return_code = 0
            e = "gear-dry-run is set: Command was NOT run."
            log.warning(e)
            warnings.append(e)
            pretend_it_ran(gtk_context)
            metadata_to_upload = {
                "analysis": {
                    "info": {
                        "dry_run": {"How dry I am": "Say to Mister Temperance...."}
                    }
                }
            }

        else:
            # Create output directory
            log.info("Creating output directory %s", output_analysis_id_dir)
            if not Path(output_analysis_id_dir).exists():
                Path(output_analysis_id_dir).mkdir()

            # This is what it is all about
            exec_command(
                command,
                environ=environ,
                dry_run=dry_run,
                shell=True,
                cont_output=True,
            )

            # Harvest first level jsons into group level analysis
            if hierarchy["run_level"] == "project":
                command = generate_command(
                    config,
                    gtk_context.work_dir,
                    output_analysis_id_dir,
                    errors,
                    warnings,
                    analysis_level="group",
                )

                command_name = make_file_name_safe(command[0])
                try:
                    exec_command(
                        command,
                        environ=environ,
                        dry_run=dry_run,
                        shell=True,
                        cont_output=True,
                    )
                except Exception as e:
                    # Bare, extra exception from mriqc/cli/run.py line 113
                    print(e)

                # Copy the resulting tsv summaries to the enclosing output directory
                # where the other, zipped output will live.
                tsvs = glob.glob(os.path.join(output_analysis_id_dir, "*tsv"))
                for tsv in tsvs:
                    name_no_tsv = os.path.splitext(os.path.basename(tsv))[0]
                    dest_tsv = os.path.join(
                        context.output_dir,
                        name_no_tsv + "_" + context.destination["id"] + ".tsv",
                    )
                    shutil.copy(tsv, dest_tsv)
                if os.path.exists(os.path.join(context.output_dir, "*tsv")):
                    log.info(
                        f"Group-level tsv files:\n{glob.glob(os.path.join(context.output_dir,'*tsv'))}"
                    )
                else:
                    log.debug(
                        f"Do you spot tsv files here?\n{determine_dir_structure(context.output_dir)}"
                    )

    except RuntimeError as exc:
        return_code = 1
        errors.append(exc)
        log.critical(exc)
        log.exception("Unable to execute command.")

    finally:
        if dry_run and not testing:
            log.info("Just dry run: no additional data.")
        else:
            try:
                metadata_to_upload = store_iqms(output_analysis_id_dir, gtk_context)
            except TypeError as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                mod_name = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                log.error(exc_type, mod_name, exc_tb.tb_lineno)
                log.info("No IQMs found to add to metadata.")

        # Cleanup, move all results to the output directory

        # zip entire output/<analysis_id> folder into
        #  <gear_name>_<project|subject|session label>_<analysis.id>.zip
        try:
            zip_file_name = (
                gtk_context.manifest["name"] + f"_{run_label}_{destination_id}.zip"
            )
        except KeyError:
            zip_file_name = f"_{run_label}_{destination_id}.zip"

        zip_output(
            str(gtk_context.output_dir),
            destination_id,
            zip_file_name,
            dry_run=False,
            exclude_files=None,
        )

        # zip any .html files in output/<analysis_id>/
        zip_htmls(gtk_context, output_analysis_id_dir)

        # possibly save ALL intermediate output
        if config.get("gear-save-intermediate-output"):
            zip_all_intermediate_output(gtk_context, run_label)

        # possibly save intermediate files and folders
        zip_intermediate_selected(gtk_context, run_label)

        # clean up: remove output that was zipped
        if Path(output_analysis_id_dir).exists():
            if not config.get("gear-keep-output"):
                log.debug('removing output directory "%s"', str(output_analysis_id_dir))
                shutil.rmtree(output_analysis_id_dir)

            else:
                log.info(
                    'NOT removing output directory "%s"', str(output_analysis_id_dir)
                )

        else:
            log.info("Output directory does not exist so it cannot be removed")

        # Report errors and warnings at the end of the log so they can be easily seen.
        if len(warnings) > 0:
            msg = "Previous warnings:\n"
            for warn in warnings:
                msg += "  Warning: " + str(warn) + "\n"
            log.info(msg)

        if len(errors) > 0:
            msg = "Previous errors:\n"
            for err in errors:
                if str(type(err)).split("'")[1] == "str":
                    # show string
                    msg += "  Error msg: " + str(err) + "\n"
                else:  # show type (of error) and error message
                    err_type = str(type(err)).split("'")[1]
                    msg += f"  {err_type}: {str(err)}\n"
            log.info(msg)
            return_code = 1

        # Though metadata is directly updated on the file for most files,
        # keep for one off files with metadata that should be uploaded.
        if metadata_to_upload in locals():
            if ("analysis" in metadata_to_upload) and (
                len(metadata_to_upload["analysis"]["info"]) > 0
            ):
                with open(f"{gtk_context.output_dir}/.metadata.json", "w") as fff:
                    json.dump(metadata_to_upload, fff)
                log.info(f"Wrote {gtk_context.output_dir}/.metadata.json")
            else:
                log.info("No data available to save in .metadata.json.")
            log.debug(".metadata.json: %s", json.dumps(metadata_to_upload, indent=4))
        # if use_singularity:
        #     try:
        #         unlink_gear_mounts()
        #     except FileNotFoundError:
        #         pass # That was the entire point of unlinking

    log.info("%s Gear is done.  Returning %s", CONTAINER, return_code)

    return return_code


if __name__ == "__main__":
    # Decide which env is available. This is the old way. Kept here just in case
    # use_singularity = check_for_singularity()
    # To test within a Singularity container, use "(config_path='/flywheel/v0/config.json')" for context.

    #move the singularity check inside one level where the centext is available to check which directory should be made /tmp
    with flywheel_gear_toolkit.GearToolkitContext() as context:
        scratch_dir = run_in_tmp_dir(context.config["gear-writable-dir"])

    # Has to be instantiated twice here, since parent directories might have
    # changed
    with flywheel_gear_toolkit.GearToolkitContext() as context:
        # Setup basic logging and log the configuration for this job
        context.init_logging(context.config["gear-log-level"].lower())
        context.log_config()

        # log.info(f"Using Singularity: {use_singularity}")
        # if use_singularity:
        #     log_singularity_details()

        # Run the gear
        # sys.exit(main(context, use_singularity))
        return_code = main(context)
    # clean up (might be necessary when running in a shared computing environment)
    if scratch_dir:
        log.debug("Removing scratch directory")
        for thing in scratch_dir.glob("*"):
            if thing.is_symlink():
                thing.unlink()  # don't remove anything links point to
                log.debug("unlinked %s", thing.name)
        shutil.rmtree(scratch_dir)
        log.debug("Removed %s", scratch_dir)

    sys.exit(return_code)