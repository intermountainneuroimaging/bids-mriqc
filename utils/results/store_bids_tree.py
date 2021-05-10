import json
import logging

log = logging.getLogger(__name__)

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