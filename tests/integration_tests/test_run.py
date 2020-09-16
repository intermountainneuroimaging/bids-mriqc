#!/usr/bin/env python3
"""
"""

import json
import logging
import os
import shutil
from pathlib import Path
from pprint import pprint
from unittest import TestCase

import flywheel_gear_toolkit
from flywheel_gear_toolkit.utils.zip_tools import unzip_archive

import run


def install_gear(zip_name):
    """unarchive initial gear to simulate running inside a real gear.

    This will delete and then install: config.json input/ output/ work/

    Args:
        zip_name (str): name of zip file that holds simulated gear.
    """

    gear_tests = "/src/tests/data/gear_tests/"
    gear = "/flywheel/v0/"
    os.chdir(gear)  # Make sure we're in the right place (gear works in "work/" dir)

    print("\nRemoving previous gear...")

    if Path(gear + "config.json").exists():
        Path(gear + "config.json").unlink()

    for dir_name in ["input", "output", "work"]:
        path = Path(gear + dir_name)
        if path.exists():
            shutil.rmtree(path)

    print(f'\ninstalling new gear, "{zip_name}"...')
    unzip_archive(gear_tests + zip_name, gear)


def print_caplog(caplog):

    print("\nmessages")
    for ii, msg in enumerate(caplog.messages):
        print(f"{ii:2d} {msg}")
    print("\nrecords")
    for ii, rec in enumerate(caplog.records):
        print(f"{ii:2d} {rec}")


def print_captured(captured):

    print("\nout")
    for ii, msg in enumerate(captured.out.split("\n")):
        print(f"{ii:2d} {msg}")
    print("\nerr")
    for ii, msg in enumerate(captured.err.split("\n")):
        print(f"{ii:2d} {msg}")


def search_caplog(caplog, find_me):
    """Search caplog message for find_me, return message"""

    for msg in caplog.messages:
        if find_me in msg:
            return msg
    return ""


def search_caplog_contains(caplog, find_me, contains_me):
    """Search caplog message for find_me, return true if it contains contains_me"""

    for msg in caplog.messages:
        if find_me in msg:
            print(f"Found '{find_me}' in '{msg}'")
            if contains_me in msg:
                print(f"Found '{contains_me}' in '{msg}'")
                return True
    return False


#
#  Tests
#


def test_dry_run_works(caplog):

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    print(str(user_json))
    assert 0
    # if not user_json.exists():
    #    TestCase.skipTest("", f"No API key available in {str(user_json)}")

    caplog.set_level(logging.DEBUG)

    install_gear("dry_run.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        print_caplog(caplog)
        print(excinfo)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 0
        assert search_caplog(caplog, "Warning: gear-dry-run is set")
        assert 0


def test_dry_run_works(caplog):

    user_json = Path(Path("/root/.config/flywheel/user.json"))
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    caplog.set_level(logging.DEBUG)

    install_gear("dry_run.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        status = run.main(gtk_context)

        print_caplog(caplog)

        assert Path("/flywheel/v0/work/bids/.bidsignore").exists()
        assert "No BIDS errors detected." in caplog.messages[32]
        assert "Zipping work directory" in caplog.messages[50]
        assert "file:   ./bids/dataset_description.json" in caplog.messages[53]
        assert "folder: ./reportlets/somecmd/sub-TOME3024/anat" in caplog.messages[55]
        assert "Could not find file" in caplog.messages[57]
        assert "gear-dry-run is set" in caplog.messages[59]
        assert status == 0


def test_wet_run_works(caplog):

    user_json = Path(Path("/root/.config/flywheel/user.json"))
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    caplog.set_level(logging.DEBUG)

    install_gear("wet_run.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        status = run.main(gtk_context)

        print_caplog(caplog)

        assert "sub-TOME3024_ses-Session2_acq-MPR_T1w.nii.gz" in caplog.messages[30]
        assert "Not running BIDS validation" in caplog.messages[38]
        assert "now I generate an error" in caplog.messages[44]
