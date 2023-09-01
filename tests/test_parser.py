"""Module to test parser.py"""

from os import cpu_count as os_cpu_count
from unittest.mock import patch

import pytest
from flywheel_gear_toolkit import GearToolkitContext

import fw_gear_bids_app_template.parser
from fw_gear_bids_app_template.parser import parse_config

@pytest.mark.parametrize(
    "mock_config_opt",
    [None,"[{'k':'v'}]"
        ])
def test_parse_config(mock_config_opt, mocked_context):
    mocked_context.config.get.side_effect = lambda x: mock_config_opt
    debug, config_options = parse_config(mocked_context)
    assert debug == False
    assert config_options == mock_config_opt
