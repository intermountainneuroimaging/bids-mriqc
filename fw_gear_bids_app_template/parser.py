"""Parser module to parse gear config.json."""
import logging
from typing import Dict, Tuple

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
    for key in gear_context.config.keys():
        if not key.startswith("gear-") and key not in [
            "debug",
            "bids_app_command",
            "mem_mb",
            "n_cpus",
        ]:
            config_options[key] = gear_context.config.get(key)

    return debug, config_options
