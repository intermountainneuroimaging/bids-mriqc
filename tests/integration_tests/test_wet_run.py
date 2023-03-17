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


def test_wet_run_fails(
    capfd,
    install_gear,
    print_captured,
    search_stderr_contains,
):
    user_json = Path("/home/bidsapp/.config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    install_gear("wet_run.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:
        print("client is ", gtk_context.client)
        status = run.main(gtk_context)

    captured = capfd.readouterr()
    print_captured(captured)

    assert search_stderr_contains(
        captured,
        "Empty file",
        "sub-TOME3024_ses-Session1_task-REST_dir-AP_run-2_bold.nii.gz",
    )
    assert status == 1
    assert Path("/flywheel/v0/output/.metadata.json").exists()
    assert search_stderr_contains(captured, "CRITICAL", "command has failed")
