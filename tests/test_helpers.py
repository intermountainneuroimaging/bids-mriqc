from unittest.mock import patch

import pytest
from flywheel_bids.flywheel_bids_app_toolkit.utils.helpers import (
    determine_dir_structure,
)

from fw_gear_bids_mriqc.utils.helpers import extra_post_processing, find_group_tsvs


@pytest.fixture
def analysis_output_dir(tmp_path):
    # Create a temporary directory for the analysis output
    output_dir = tmp_path / "analysis_output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def flywheel_output_dir(tmp_path):
    # Create a temporary directory for the flywheel output
    output_dir = tmp_path / "flywheel_output"
    output_dir.mkdir()
    return output_dir


def test_find_group_tsvs(analysis_output_dir, flywheel_output_dir):
    # Create some dummy tsv files in the analysis output directory
    tsv_files = [
        analysis_output_dir / "file1.tsv",
        analysis_output_dir / "file2.tsv",
        analysis_output_dir / "file3.tsv",
    ]
    for tsv_file in tsv_files:
        tsv_file.touch()

    # Mock the log.info and log.debug functions
    with (
        patch("fw_gear_bids_mriqc.utils.helpers.log.info") as mock_info,
        patch("fw_gear_bids_mriqc.utils.helpers.log.debug") as mock_debug,
    ):
        # Call the find_group_tsvs function
        find_group_tsvs(analysis_output_dir, flywheel_output_dir, destination_id="123")

        # Check that the tsv files are renamed and moved to the
        # flywheel output directory
        expected_dest_files = [
            flywheel_output_dir / "file1_123.tsv",
            flywheel_output_dir / "file2_123.tsv",
            flywheel_output_dir / "file3_123.tsv",
        ]
        for dest_file in expected_dest_files:
            assert dest_file.exists()

        # Check that the log.info function is called with the
        # correct message
        mock_info.assert_called_with(f"Group-level tsv files:\n{list(flywheel_output_dir.glob('*tsv'))}")

        # Check that the log.debug function is not called
        mock_debug.assert_not_called()


def test_find_group_tsvs_no_tsv_files(analysis_output_dir, flywheel_output_dir):
    # Mock the log.info and log.debug functions
    with (
        patch("fw_gear_bids_mriqc.utils.helpers.log.info") as mock_info,
        patch("fw_gear_bids_mriqc.utils.helpers.log.debug") as mock_debug,
    ):
        # Call the find_group_tsvs function when there are
        # no tsv files in the analysis output directory
        find_group_tsvs(analysis_output_dir, flywheel_output_dir, destination_id="123")

        # Check that the log.debug function is called with the
        # correct message
        mock_debug.assert_called_with(
            f"Do you spot tsv files here?\n" f"{determine_dir_structure(flywheel_output_dir)}"
        )

        # Check that the log.info function is not called
        mock_info.assert_not_called()


@pytest.mark.parametrize("analysis_level, expected_calls", [("group", 1), ("subject", 0)])
@patch("fw_gear_bids_mriqc.utils.helpers.store_metadata")
@patch("fw_gear_bids_mriqc.utils.helpers.find_group_tsvs")
def test_extra_post_processing(
    mock_find,
    mock_store,
    analysis_level,
    expected_calls,
    mock_app_context,
    mock_context,
):
    mock_app_context.analysis_level = analysis_level
    extra_post_processing(mock_context, mock_app_context)
    assert mock_find.call_count == expected_calls
    assert mock_store.called_once
