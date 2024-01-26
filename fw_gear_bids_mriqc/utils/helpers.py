"""Small methods specific to this BIDS app gear"""

import logging
import sys
from pathlib import Path
from typing import List, Union

from flywheel_bids.flywheel_bids_app_toolkit import BIDSAppContext
from flywheel_bids.flywheel_bids_app_toolkit.commands import (
    run_bids_algo,
)
from flywheel_bids.flywheel_bids_app_toolkit.utils.helpers import (
    determine_dir_structure,
)

from fw_gear_bids_mriqc.utils.store_iqms import store_iqms

log = logging.getLogger(__name__)


def find_group_tsvs(
    analysis_output_dir: Union[Path, str],
    flywheel_output_dir: Union[Path, str],
    destination_id: str = None,
) -> None:
    """
    Locate the summary files that MRIQC produces.

    Copy the resulting tsv summaries to the enclosing output directory
    where the other, zipped output will live.

    Args:
        analysis_output_dir: location of the BIDS algorithm output
        flywheel_output_dir: location to be zipped
        destination_id: Flywheel identification code for the container

    """

    tsvs = list(Path(analysis_output_dir).glob("*tsv"))
    for tsv in tsvs:
        name_no_tsv = Path(tsv).stem
        dest_tsv = Path(flywheel_output_dir).joinpath(
            name_no_tsv + "_" + destination_id + ".tsv"
        )
        Path(tsv).rename(dest_tsv)
    if list(Path(flywheel_output_dir).glob("*tsv")):
        log.info(
            f"Group-level tsv files:\n{list(Path(flywheel_output_dir).glob('*tsv'))}"
        )
    else:
        log.debug(
            f"Do you spot tsv files here?\n"
            f"{determine_dir_structure(flywheel_output_dir)}"
        )


def analyze_participants(app_context: BIDSAppContext, command: List) -> int:
    """Ensure participants have been analyzed with mriqc

    Current behavior follows legacy bids-mriqc gear style of running the
    mriqc command with 'participant' rather than 'group' and then running
    the 'group' command.

    Future behavior should check for "IQM" as metadata on acquisitions
    and pull that metadata into the proper JSON file.

    Args:
        app_context (BIDSAppContext): information specific to this
                    BIDS app and gear run
        command (list): BIDS App command list to pass to subprocess
    """

    # Run participant-level analyses
    participant_command = ["participant" if arg == "group" else arg for arg in command]
    try:
        log.info("NEED TO RUN PARTICIPANT LEVEL FIRST. ATTEMPTING...")
        e_code = run_bids_algo(app_context, participant_command)
    except Exception as e:
        log.error(f"While running {command} encountered:\n{e}")
        e_code = 1
    return e_code


def store_metadata(gear_context, app_context):
    if app_context.gear_dry_run:
        log.info("Just dry run: no additional data.\n" "Skipping store_iqms method.")
        return {
            "analysis": {
                "info": {
                    "derived": {
                        "dry_run": {"How dry I am": "Say to Mister Temperance...."}
                    }
                }
            }
        }
    else:
        try:
            return store_iqms(gear_context, app_context)
        except TypeError:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            mod_name = Path(exc_tb.tb_frame.f_code.co_filename).name
            log.error(exc_type, mod_name, exc_tb.tb_lineno)
            log.info("No IQMs found to add to metadata.")


def extra_post_processing(gear_context, app_context) -> None:
    """Collect IQMs and update the appropriate metadata fields"""

    if app_context.analysis_level == "group":
        find_group_tsvs(
            app_context.analysis_output_dir,
            app_context.output_dir,
            gear_context.destination["id"],
        )

    store_metadata(gear_context, app_context)
