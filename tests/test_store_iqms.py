import json
import logging
from collections import defaultdict
from unittest.mock import MagicMock, patch

import pytest
from flywheel_gear_toolkit.testing import make_acquisition, make_session

from fw_gear_bids_mriqc.utils.store_iqms import (
    _add_metadata_to_upload,
    _create_nested_metadata,
    _parse_json_file,
    _update_fw_file,
    store_iqms,
)

log = logging.getLogger(__name__)


@pytest.fixture
def json_data():
    return {
        "feature1": 1,
        "feature2": 2,
    }


@pytest.fixture
def json_file(tmp_path, json_data):
    file_path = tmp_path / "test.json"
    with open(file_path, "w") as f:
        json.dump(json_data, f)
    return str(file_path)


def mock_acqs(n_acqs, mock_context, n_files=3, labels=["dummy_acq"]):
    """Populate img mock acquisition based off the mock context and capable of receiving
    new return values for testing.
    Note: this doesn't work as a fixture in conftest, so it lives here."""
    acq_list = []
    if n_acqs != len(labels):
        labels = n_acqs * labels[0]
    for n in range(n_acqs):
        acq = make_acquisition(labels[n], n_files=n_files)
        acq.files[n].modality = "colored_pencil"
        for i, img in enumerate(acq.files):
            img.type = "NIfTI"
            img.name = f"new_file_{str(i)}"
            img.parents = {"session": 109}
        acq_list.append(acq)
    mock_context.acquisitions.iter_find.return_value = acq_list
    return mock_context, acq_list


def mock_sess(n_ses, mock_context, n_acqs=3):
    """Populate n_ses mock sessions based off the mock context for testing.
    Note: this doesn't work as a fixture in conftest, so it lives here."""
    sess_list = []
    for n in range(n_ses):
        ses = make_session(f"morning_{str(n)}", n_acqs=n_acqs)
        sess_list.append(ses)
    mock_context.sessions.iter_find.return_value = sess_list
    return mock_context, sess_list


class TestStoreIQMs:
    @patch("fw_gear_bids_mriqc.utils.store_iqms.find_associated_bids_acqs")
    @patch("fw_gear_bids_mriqc.utils.store_iqms._create_nested_metadata")
    def test_store_iqms_needs_jsons(
        self, mock_nested, mock_find_bids, mock_context, mock_app_context, caplog
    ):
        """
        Make sure the store_iqms fails if no jsons are located.
            Args:
                mock_nested: mock call to parse located jsons;
                        should not occur in this test
                caplog: Capture the log output to make sure
                        the message is present
        """
        n_acqs = 2
        caplog.clear()
        caplog.set_level(logging.DEBUG)
        mock_find_bids.return_value = mock_acqs(n_acqs, mock_context)
        store_iqms(mock_context, mock_app_context)
        assert "Did not find MRIQC output" in caplog.records[1].message
        assert mock_nested.call_count == 0

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
        assert len(test_metadata.keys()) == 1
        assert len(test_metadata["a"]["b"]["c"]) == 2


@patch("fw_gear_bids_mriqc.utils.store_iqms.filter_fw_files")
@patch("fw_gear_bids_mriqc.utils.store_iqms._add_metadata_to_upload")
@patch("fw_gear_bids_mriqc.utils.store_iqms._update_fw_file")
@patch("fw_gear_bids_mriqc.utils.store_iqms._parse_json_file")
@patch("fw_gear_bids_mriqc.utils.store_iqms.find_associated_bids_acqs")
@patch("fw_gear_bids_mriqc.utils.store_iqms._find_output_files")
def test_store_iqms_with_json_files(
    mock_find,
    mock_find_bids,
    mock_parse,
    mock_update_fw_file,
    mock_add_metadata_to_upload,
    mock_filter_fw_files,
    mock_context,
    mock_app_context,
    json_file,
    json_data,
):
    mock_find.return_value = [json_file]
    mock_find_bids.return_value = []
    mock_parse.return_value = json_data
    mock_filter_fw_files.return_value = ["parent", "fw_file"]

    result = store_iqms(mock_context, mock_app_context)

    assert result is None
    assert mock_update_fw_file.called
    assert not mock_add_metadata_to_upload.called


# Defunct test b/c mocking session.acquisitions.iter_find() is
# proving to be a bear.

# @patch("fw_gear_bids_mriqc.utils.store_iqms.flywheel.Client")
# def test_find_associated_bids_acqs(mock_client, mock_context):
#     # Create a mock session object
#     session_mock = Mock()
#
#     # Create mock acquisitions with and without BIDS files
#     acq1_mock = Mock()
#     acq1_mock.files = [Mock(info={"BIDS": True})]
#     acq2_mock = Mock()
#     acq2_mock.files = [Mock(info={"BIDS": False})]
#
#     # Set up the mock objects
#     mock_client.get_session.return_value = session_mock
#     session_mock.acquisitions.iter_find.return_value = [acq1_mock, acq2_mock]
#
#
#     # Call the function with the mock objects
#     result = find_associated_bids_acqs(mock_context)
#
#     # Assert that the function returns the correct result
#     assert result == [acq1_mock]
#
#     # Assert that the mock objects were called with the correct arguments
#     session_mock.acquisitions.iter_find.assert_called_with()


def test_parse_json_file(json_file, json_data):
    result = _parse_json_file(json_file)
    assert result == json_data


def test_update_fw_file():
    fw_file = MagicMock()
    json_data = {"feature1": 1, "feature2": 2}

    _update_fw_file(fw_file, json_data)

    fw_file.update_info.assert_called_once_with({"derived": {"IQM": json_data}})


def test_add_metadata_to_upload():
    metadata_to_upload = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )
    json_file = "test.json"
    json_data = {"feature1": 1, "feature2": 2}

    _add_metadata_to_upload(metadata_to_upload, json_file, json_data)

    assert metadata_to_upload["analysis"]["info"]["derived"]["IQM"] == [
        {"feature1": 1, "feature2": 2, "filename": "test"}
    ]
