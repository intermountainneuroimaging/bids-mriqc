"""Module to test parser.py"""

import pytest

from fw_gear_bids_mriqc.parser import parse_config


@pytest.mark.parametrize(
    "mock_config_dict, expected_debug, expected_config_options",
    [
        ({}, None, {}),
        ({"debug": "DEBUG"}, "DEBUG", {}),
        ({"debug": "ERROR", "my_opt": "is_boring"}, "ERROR", {"my_opt": "is_boring"}),
        (
            {"my_opt_2": "is_educated", "gear-special": "wd-40"},
            None,
            {"my_opt_2": "is_educated"},
        ),
    ],
)
def test_parse_config(mock_config_dict, expected_debug, expected_config_options, mock_context):
    mock_context.config.items.side_effect = [mock_config_dict.items()]
    mock_context.config.get.side_effect = lambda key: mock_config_dict.get(key)
    debug, config_options = parse_config(mock_context)
    assert debug == expected_debug
    assert config_options == expected_config_options
