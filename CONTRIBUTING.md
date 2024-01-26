# Contributing

## Getting started

1. Follow instructions
   to [install poetry](https://python-poetry.org/docs/#installation).
2. Follow instructions to [install pre-commit](https://pre-commit.com/#install)

After cloning the repo:

1. Run `poetry install` to install project and all dependencies
   (see __Dependency management__ below)
2. Run `pre-commit install` to install pre-commit hooks
   (see __Linting and Testing__ below)

(If you need to change your python version:)

```shell
poetry env use <path/to/your/python/executable>
poetry update
```

## Dependency management

This gear uses [`poetry`](https://python-poetry.org/) to manage dependencies,
develop, build and publish.

### Dependencies

Dependencies are listed in the `pyproject.toml` file.

#### Managing dependencies

* Adding: Use `poetry add [--dev] <dep>`
* Removing: Use `poetry remove [--dev] <dep>`
* Updating: Use `poetry update <dep>` or `poetry update` to update all deps.
    * Can also not update development dependencies with `--no-dev`
    * Update dry run: `--gear-dry-run`

#### Using a different version of python

Poetry manages virtual environments and can create a virtual environment
with different versions of python,
however that version must be installed on the machine.

You can configure the python version
by using `poetry env use <path/to/executable>`

#### Helpful poetry config options

See full
options [Here](https://python-poetry.org/docs/configuration/#available-settings).

List current config: `poetry config --list`

* `poetry config virtualenvs.in-project <true|false|None>`:
  create virtual environment inside project directory
* `poetry config virtualenvs.path <path>`: Path to virtual environment directory.

## Linting and Testing

Local linting and testing scripts
are managed through [`pre-commit`](https://pre-commit.com/).  
Pre-commit allows running hooks which can be defined locally, or in other
repositories. Default hooks to run on each commit:

* gearcheck: Specific check for this gear repo template
* poetry_export: Export poetry based dependencies to requirements.txt
* docker-build: Build docker image
* yamllint: Linter for YAML file
* ruff: isort and other linting services
* pytest: Run pytest

These hooks will all run automatically on commit, but can also be run manually
or just be disabled.

More hooks can be enabled upon need. List of available
[hooks](https://gitlab.com/flywheel-io/tools/etc/qa-ci#table-of-contents).

### pre-commit usage

* Run hooks manually:
    * Run on all files: `pre-commit run -a`
    * Run on certain files: `pre-commit run --files test/*`
* Update (e.g. clean and install) hooks: `pre-commit clean && pre-commit install`
* Disable all hooks: `pre-commit uninstall`
* Enable all hooks: `pre-commit install`
* Skip a hook on commit: `SKIP=<hook-name> git commit`
* Skip all hooks on commit: `git commit --no-verify`

## Dockerfile

Use multi-stage builds to isolate Flywheel dependencies from the official BIDS App
image and dependencies.

Export a venv that has all the dependencies for Flywheel to the final stage, which
builds the official BIDS App image.

Depending on the python version of the BIDS App (final stage), you may have to
install an alternate version of python in the stage to accommodate the
Flywheel-specific venv (i.e., `flypy`). The BIDS App Template has an example of how
to accomplish this.

Isolating the dependencies will limit `poetry update` issues to packages used by the
gear, not the BIDS App algorithm as well.

## Gear workflow

The gear generally progresses from one section to the next as defined below:

* Section 1: Set up the Docker container with all the env variables, licenses, and BIDS
  data.
    * Configuration options are parsed and stored in the BIDS App Context object.
      Various parameters needed by the algorithm can be and are populated from there.

* Section 2: Parse the commandline input provided via the config.json under the "
  bids_app_command" field. If the BIDS App has idiosyncrasies in the formatting of
  kwargs or required custom fields in the manifest for the config, then the output from
  the standard `generate_command`method (from `flywheel_bids_app_toolkit`) is amended.
  If possible, design the manifest to highlight inputting the command over breaking out
  the individual args and kwargs, as this strategy will be more flexible and
  maintainable between versions. As a bonus, much of the testing can be handled within
  flywheel_bids_app_toolkit if this strategy is employed.

* Section 3: Handle dry-runs, BIDS download (not validation) errors, and actual
  algorithm runs.
    * After parsing the configuration and ensuring that the algorithm command has been
      cleaned for illegal characters, the MRIQC algorithm will run.

* Section 4: Zip any html, result, or other files so the container can spin down
  gracefully and provide the analysis for review and alternatives use.
    * Output from the algorithm is collected and parsed to populate metadata and report
      in the analyses tab. HTML reports from MRIQC can be downloaded individually or in
      the overall bids_mriqc zip folder.

## A word on post-processing metadata

* Analysis results that are searchable should be placed on the associated file
  under `file.derived.<meaningful_key>`, where "meaningful_key" is an immutable word
  that makes sense for the app (e.g., "IQM" for BIDS MRIQC). Any further nesting should
  name the keys thoughtfully, so that they will also be meaningful, but immutable (i.e.,
  NO filenames as a dynamic identifier).

## Adding a contribution

Every contribution should be
associated with a ticket on the GEAR JIRA board, or be a hotfix.  
You should contribute by creating
a branch titled with either `hotfix-<hotfix_name` or `GEAR-<gear_num>-<description>`.  
For now, other branch names will be accepted,
but soon branch names will be rejected
if they don't follow this pattern.

When contributing, make a Merge Request against the main branch.

### Merge requests

The merge request should contain at least:

1. Your relevant change with the corresponding test.
1. A high level description of your changes and additional information to guide
   the reviewer eyes as deemed appropriate.
1. An as clean as possible git history.
