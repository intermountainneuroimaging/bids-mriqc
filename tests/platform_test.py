import argparse
import logging
import sys
from pathlib import Path
from typing import Union

import flywheel
from flywheel_bids.flywheel_bids_app_toolkit.utils.autoupdate_platform_test import (
    get_api,
    parse_job_state,
    poll_job_state,
)

log = logging.getLogger(__name__)

# NOTE: --dry-run, --boilerplate_only, and --boilerplate-only could all be helpful in running a quick test. Specify which kwarg is available for this algorithm
QUICK_RUN = "--dry-run"
# NOTE: Update the project on a test instance that has data the test can run on
DESTINATION = "bids-apps/BIDS_multi_session/sub-TOME3024"


def main(fw: flywheel.Client, gear_name: str, fw_destination: Union[Path, str] = "") -> int:
    """
    Run a platform test for gear update changes.

    Args:
        fw (flwheel.Client): details to communicate with the platform
        gear_name (str): Flywheel name for the gear, not the algorithm
        destination (Path, str): Flywheel container that has appropriate
                    data on which to test the gear.

    Returns:
        Status of the test
    """
    all_gears = fw.gears()
    gear = next(gear for gear in all_gears if gear.gear.name == gear_name)

    if gear:
        # Prepare configuration
        algo = gear.gear.get("custom").get("bids-app-binary")
        if QUICK_RUN:
            cmd = f"{algo} bids_dir output_dir participant {QUICK_RUN} --no-sub"
        else:
            cmd = f"{algo} bids_dir output_dir participant --no-sub"

        config = {
            "bids_app_command": cmd,
            # Add other configuration settings as needed
        }
        destination = fw.lookup(fw_destination)

        analysis_label = f"{gear.gear.name} update to {gear.gear.version} platform test"

        job_id = gear.run(analysis_label=analysis_label, config=config, destination=destination)

        log.info("Version: %s\nAnalysis ID: %s", gear.gear.version, job_id)
        poll_job_state(fw, job_id)
        return parse_job_state(fw.get_job(job_id).state)
    else:
        log.error("Could not find gear: %s", gear_name)
        return 1


if __name__ == "__main__":
    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Run platform test for a specific gear")
    parser.add_argument("gear_name", type=str, help="Name of the gear to test")

    args = parser.parse_args()

    fw = flywheel.Client(get_api())

    job_status = main(fw, args.gear_name, fw_destination=DESTINATION)
    sys.exit(job_status)
