from unittest.mock import MagicMock, patch

import pytest

from fw_gear_bids_mriqc.main import customize_bids_command, setup_bids_env


@patch("fw_gear_bids_mriqc.main.set_participant_info_for_command")
@patch("fw_gear_bids_mriqc.main.get_bids_data")
def test_setup_bids_env(
    mock_get_bids_data,
    mock_set_participant_info_for_command,
    mock_context,
    mock_app_context,
):
    participant_info = MagicMock()
    errors = MagicMock()
    mock_get_bids_data.return_value = (participant_info, errors)
    mock_context.gear_dry_run = True
    result = setup_bids_env(mock_context)


    # Assert that the get_bids_data function was called with the correct arguments
    mock_get_bids_data.assert_called_once_with(
        mock_context,
        mock_app_context.bids_app_modalities,
        tree_title=mock_app_context.bids_app_binary + " BIDS Tree",
        skip_download=mock_app_context.gear_dry_run,
    )

    # Assert that the set_participant_info_for_command function was called
    # if the analysis_level is "participant"
    if mock_app_context.analysis_level == "participant":
        mock_set_participant_info_for_command.assert_called_once()

    # Assert that the result is a tuple containing the app_context
    # object and the errors list
    assert isinstance(result, tuple)
    assert result[1] == errors


@pytest.mark.parametrize(
    "command, extra_args, updated_command",
    [
        (
            ["update", "this"],
            {"with": "something"},
            ["update", "this", "--with=something"],
        ),
        (
            ["update", "this"],
            {"with-nothing": True},
            ["update", "this", "--with-nothing"],
        ),
        (
            ["include", "a"],
            {"boolean": True, "no-sub": False},
            ["include", "a", "--boolean"],
        ),
        (["include", "a", "--equals=sign x"], {}, ["include", "a", "--equals sign x"]),
    ],
)
def test_customize_bids_command(command, extra_args, updated_command):
    result_command = customize_bids_command(command, extra_args)
    assert updated_command == result_command
