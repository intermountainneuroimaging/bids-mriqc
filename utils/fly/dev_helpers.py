from os import walk, path
import json
import logging

log = logging.getLogger(__name__)


def determine_dir_structure(search_dir):
    """
    The directory structure during analysis is somewhat obscure.
    If the file path in the code is incorrect, this method will be called to
    help build the debugging message.
    """
    for root, dirs, files in walk(search_dir):
        for f in files:
            print(path.join(root, f))


def store_bids_tree(context, run_label, destination_id):
    """
    Convert the BIDS tree into a readable json.
    """

    metadata = {
        "project": {
            "info": {
                "test": project_label,
                f"{run_label} {destination_id}": "put this here",
            },
            "tags": [run_label, destination_id],
        },
        "subject": {
            "info": {
                "test": run_label,
                f"{run_label} {destination_id}": "put this here",
            },
            "tags": [run_label, destination_id],
        },
        "session": {
            "info": {
                "test": session_label,
                f"{run_label} {destination_id}": "put this here",
            },
            "tags": [run_label, destination_id],
        },
        "analysis": {
            "info": {
                "test": "Hello analysis",
                f"{run_label} {destination_id}": "put this here",
            },
            "files": [
                {
                    "name": "bids_tree.html",
                    "info": {
                        "value1": "foo",
                        "value2": "bar",
                        f"{run_label} {destination_id}": "put this here",
                    },
                    "tags": ["ein", "zwei"],
                }
            ],
            "tags": [run_label, destination_id],
        },
    }
