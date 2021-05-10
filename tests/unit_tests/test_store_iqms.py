import logging
import os.path as op
from glob import glob
from unittest import MagicMock

from utils.results.store_iqms import store_iqms

log = logging.getLogger(__name__)

def test_store_iqms_needs_hierarchy(caplog, install_gear):
    """Make sure the globbed file path to the jsons is correct."""

    caplog.set_level(logging.DEBUG)
    install_gear("wet_run.zip")

    subj_path = glob(op.join("data", "gear_tests", "wet_run", "output", "*", "sub*"))[0]
    destination_id = subj_path.split("/")[-2]
    gear_context = MagicMock("flywheel_gear_toolkit.GearToolkitContext")

    store_iqms(gear_context,destination_id)

    assert len(caplog.records) == 1
    assert "Missing info for metadata. Checked here" in caplog.records[0].message
