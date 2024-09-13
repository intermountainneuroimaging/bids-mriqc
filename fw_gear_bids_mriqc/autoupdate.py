import sys
from flywheel_bids.flywheel_bids_app_toolkit.autoupdate import main, find_file


def run():
    dockerfile = find_file("Dockerfile")
    manifest = find_file("manifest.json")
    return main(dockerfile_path=dockerfile, json_file_path=manifest)


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
