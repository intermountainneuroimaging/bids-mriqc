"""Parser module to parse gear config.json."""
from typing import Tuple

from flywheel_gear_toolkit import GearToolkitContext


# This function mainly parses gear_context's config.json file and returns relevant
# inputs and options.
def parse_config(
    gear_context: GearToolkitContext,
) -> Tuple[str, str]:
    """[Summary]

    Returns:
        [type]: [description]
    """

    debug = gear_context.config.get("debug")
    with open(
        gear_context.get_input_path("{{text-input}}"), "r", encoding="utf8"
    ) as text_file:
        text = " ".join(text_file.readlines())

    return debug, text
