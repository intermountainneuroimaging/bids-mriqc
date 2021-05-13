import logging
from unittest import mock
from unittest.mock import patch
import json

import pytest

from utils.results.store_iqms import store_iqms, _create_nested_metadata

log = logging.getLogger(__name__)


class TestStoreIQMs:
    @patch("utils.results.store_iqms._create_nested_metadata")
    def test_store_iqms_needs_jsons(self, mock_nested, caplog):
        """
        Make sure the store_iqms fails if no jsons are located.
            Args:
                mock_nested: mock call to parse located jsons; should not occur in this test
                caplog: Capture the log output to make sure the message is present
        """

        for lvl in ["project", "session", "bar"]:
            caplog.clear()
            caplog.set_level(logging.DEBUG)
            mock_hierarchy = {"run_level": lvl}
            store_iqms(mock_hierarchy, "foo_dir")
            assert len(caplog.records) == 2
            assert "Did not find MRIQC output jsons" in caplog.records[0].message
            assert mock_nested.call_count == 0

    @patch("utils.results.store_iqms._find_files")
    @patch("utils.results.store_iqms._create_nested_metadata")
    def test_store_iqms_calls_nested(self, mock_nested, mock_find, caplog):
        """
        If jsons are available, will store_iqms call the _create_nested_metadata?
            Args:
                mock_nested: mock call to parse located jsons; should not occur in this test
                mock_find: mocked list of json files to "parse"
                caplog: Capture the log output to make sure the message is present
        """
        for lvl in ["project", "session", "bar"]:
            mock_nested.call_count = 0
            mock_hierarchy = {"run_level": lvl}
            mock_find.return_value = ["baz.json", "qux.json"]
            with patch(
                "builtins.open", mock.mock_open(read_data='{"a":{"b":{"c":"d"}}}')
            ) as mock_open:
                store_iqms(mock_hierarchy, "foo_dir")
                assert mock_nested.call_count == 2

    def test_create_nested_metadata_parses(
        self, analysis_to_parse={"a": {"b": {"c": ["d", "e"]}}}
    ):
        """
        Does _create_nested_metadata_parse a nested dict correctly?
        Since the incoming data in the real method is given by json.load,
        str input is presumed.
        Args:
            analysis_to_parse (nested_dict): example dict of analysis values
        """
        test_metadata = _create_nested_metadata(analysis_to_parse)
        test_metadata = json.loads(test_metadata)[0]
        # Assert that there are two columns from the dataframe
        assert len(test_metadata.keys()) == 2
        assert len(test_metadata["1"]["b"]["c"]) == 2
