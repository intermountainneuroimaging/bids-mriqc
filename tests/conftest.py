"""
Set up parameters for testing. Picked up by pytest automatically.
"""

import json
import shutil
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock

import pytest
from flywheel_bids.flywheel_bids_app_toolkit import BIDSAppContext
from flywheel_gear_toolkit import GearToolkitContext
from flywheel_gear_toolkit.utils.zip_tools import unzip_archive


@pytest.fixture
def mock_context(mocker):
    mocker.patch("flywheel_gear_toolkit.GearToolkitContext")
    gtk_context = MagicMock(autospec=True)
    return gtk_context


@pytest.fixture
def extended_gear_context(mock_context, tmp_path):
    """Extend the basic GTK context for the BIDSApp context

    To return the desired side effects for mock_context.config.get.side_effect,
    use `lambda key: (mock_dict}.get(key) in the test method. Implementing the
    lambda function at the test level will allow us to combine this test fixture
    with parametrize and change various values on the fly.
    """
    mock_context.client.return_value.get.side_effect = lambda key: {"destination": "aex"}.get(key)
    mock_context.output_dir = Path(tmp_path) / Path("output_dir")
    mock_context.work_dir = Path(tmp_path) / Path("work_dir")
    mock_context.destination = {
        "id": "output_destination_id",
        "parent": {"type": "project"},
    }
    mock_context.config.get.side_effect_dict = {
        "bids_app_command": "something_bids_related /path/1 " "/path/2 participant --extra_option extra_opt",
        "app-dry-run": True,
        "gear-save-intermediate-output": True,
        "gear-dry-run": False,
        "gear-keep-output": False,
        "random_extra_ui_key": None,
    }
    mock_context.config.get.side_effect = lambda key: mock_context.config.get.side_effect_dict.get(key, None)
    mock_context.get_input.side_effect = lambda key: {
        "api_key": "fake_key",
        "random_extra_ui_key": None,
    }.get(key)
    mock_context.manifest.get.side_effect = lambda key: {
        "custom": {
            "bids-app-binary": "something_bids_related",
            "bids-app-data-types": ["modality1", "modality2"],
        }
    }.get(key)

    return mock_context


@pytest.fixture
def mocked_context_for_project_level(mock_acquisition):
    """Return a mocked GearToolkitContext with a "project" destination parent."""
    mocked_manifest = {
        "name": "test",
        "custom": {"gear-builder": {"image": "foo/bar:v1.0"}},
    }
    mocked_destination_id = "my_fake_proj_dest_id_ZYX987"
    return MagicMock(
        spec=GearToolkitContext,
        manifest=mocked_manifest,
        client={mocked_destination_id: mock_acquisition("project")},
        destination={"id": mocked_destination_id},
    )


FWV0 = Path.cwd()


@pytest.fixture
def mock_app_context(extended_gear_context):
    return BIDSAppContext(extended_gear_context)


@pytest.fixture
def install_gear_results():
    def _method(zip_name, gear_output_dir=None):
        """Un-archive gear results to simulate running inside a real gear.

        This will delete and then install: config.json input/ output/ work/ freesurfer/

        Args:
            zip_name (str): name of zip file that holds simulated gear.
            gear_output_dir (str): where to install the contents of the zipped file
        """

        # location of the zip file:
        gear_tests = Path("/src/tests/data/")
        if not gear_tests.exists():  # fix for running in circleci
            gear_tests = FWV0 / "tests" / "data/"

        # where to install the data
        if not gear_output_dir or not Path(gear_output_dir).exists():
            gear_output_dir = FWV0

        print("\nRemoving previous gear...")

        if Path(gear_output_dir / "config.json").exists():
            Path(gear_output_dir / "config.json").unlink()

        for dir_name in ["input", "output", "work", "freesurfer"]:
            path = Path(gear_output_dir / dir_name)
            if path.exists():
                print(f"shutil.rmtree({str(path)}")
                shutil.rmtree(path)

        print(f'\ninstalling new gear, "{zip_name}"...')
        unzip_archive(gear_tests / zip_name, str(gear_output_dir))

        # The "freesurfer" directory needs to have the standard freesurfer
        # "subjects" directory and "license.txt" file.

    return _method


@pytest.fixture
def search_caplog_contains():
    def _method(caplog, find_me, contains_me=""):
        """Search caplog message for find_me, return true if it contains contains_me"""

        for msg in caplog.messages:
            if find_me in msg:
                if contains_me in msg:
                    return True
        return False

    return _method


@pytest.fixture
def check_for_fw_key():
    def _method(user_json):
        """Check for FW's API key in $HOME/.config/flywheel/user.json.

        Check that there is a $HOME/.config/flywheel/user.json file, and that it
        contains a "key" entry (for FW's API). If not found, the test using this
        fixture is skipped.
        """

        if not user_json.exists():
            TestCase.skipTest("", f"{str(user_json)} file not found.")

        # Check API key is present:
        with open(user_json, "r", encoding="utf8") as f:
            j = json.load(f)
        if "key" not in j or not j["key"]:
            TestCase.skipTest("", f"No API key available in {str(user_json)}")

    return _method
