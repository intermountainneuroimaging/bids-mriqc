"""Run this instead of running actual command."""

import logging
from pathlib import Path
from typing import List, Union

from flywheel_bids.flywheel_bids_app_toolkit import BIDSAppContext
from flywheel_bids.flywheel_bids_app_toolkit.commands import run_bids_algo
from flywheel_bids.flywheel_bids_app_toolkit.utils.helpers import make_dirs_and_files

log = logging.getLogger(__name__)


def pretend_it_ran(app_context: BIDSAppContext, command: List[str]) -> None:
    """Make some output like the command would have done only fake.

    Args:
        app_context (BIDSAppContext): information specific to this
                    BIDS app and gear run
        command (list): BIDS App command list to pass to subprocess
    """
    # 1) Call run.
    #    Because app_context.gear_dry_run is True, run.exec_command will log the call,
    #    but will not run.
    run_bids_algo(app_context, command)

    # 2) Recreate the expected output:
    path = Path("work")

    log.info("Creating fake output in %s", str(path))

    files = [
        path / "somedir" / "d3.js",
        path / "reportlets" / "somecmd" / "sub-TOME3024" / "anat" / "sub-TOME3024_desc-about_T1w.html",
    ]

    make_dirs_and_files(files)

    # Output directory
    path = Path("output") / Path(app_context.destination_id)

    log.info("Creating fake output in %s", str(path))

    files = [
        path / "somedir" / "logs" / "CITATION.md",
        path / "somedir" / "sub-TOME3024" / "anat" / "sub-TOME3024_acq-MPR_from-orig_to-T1w_mode-image_xfm.txt",
        path / "freesurfer" / "fsaverage" / "mri" / "subcort.prob.log",
    ]

    make_dirs_and_files(files)

    html = """<html>
    <head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>sub-TOME3024</title>
    </head>
    <body>
    <h1>sub-TOME3024</h1>
    <p>This is a test html file.&nbsp; How do you love it?<br>
    </p>
    </body>
    </html>"""

    ff = path / "somedir" / "sub-TOME3024.html"
    with open(ff, "w", encoding="utf8") as fp:
        fp.write(html)
    log.debug("Creating: %s", str(ff))
