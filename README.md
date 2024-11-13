# Devdocs scraper

This scraper downloads [devdocs.io](https://devdocs.io/) documentation databases and puts them in ZIM files,
a clean and user friendly format for storing content for offline usage.

[![CodeFactor](https://www.codefactor.io/repository/github/openzim/devdocs/badge)](https://www.codefactor.io/repository/github/openzim/devdocs)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![codecov](https://codecov.io/gh/openzim/devdocs/branch/main/graph/badge.svg)](https://codecov.io/gh/openzim/devdocs)
[![PyPI version shields.io](https://img.shields.io/pypi/v/devdocs2zim.svg)](https://pypi.org/project/devdocs2zim/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/devdocs2zim.svg)](https://pypi.org/project/devdocs2zim)
[![Docker](https://ghcr-badge.egpl.dev/openzim/devdocs/latest_tag?label=docker)](https://ghcr.io/openzim/devdocs)


## Installation

There are three main ways to install and use `devdocs2zim` from most recommended to least:

<details>
<summary>Install using a pre-built container</summary>


1. Download the image using `docker`:

    ```sh
    docker pull ghcr.io/openzim/devdocs
    ```

</details>
<details>
<summary>Build your own container</summary>

1. Clone the repository locally:

    ```sh
    git clone https://github.com/openzim/devdocs.git && cd devdocs
    ```

1. Build the image:

    ```sh
    docker build -t ghcr.io/openzim/devdocs .
    ```

</details>
<details>
<summary>Run the software locally using Hatch</summary>

1. Clone the repository locally:

    ```sh
    git clone https://github.com/openzim/devdocs.git && cd devdocs
    ```

1. Install [Hatch](https://hatch.pypa.io/):

    ```sh
    pip3 install hatch
    ```

1. Start a hatch shell to install software and dependencies in an isolated virtual environment.

    ```sh
    hatch shell
    ```

1. Run the `devdocs2zim` command:

    ```sh
    devdocs2zim --help
    ```

</details>

## Usage

> [!WARNING]
> This project is still a work in progress and isn't ready for use yet, the commands below are examples only.


```sh
# Usage
docker run -v my_dir:/output ghcr.io/openzim/devdocs devdocs2zim [--all|--slug=SLUG|--first=N]

# Fetch all documents
docker run -v my_dir:/output ghcr.io/openzim/devdocs devdocs2zim --all

# Fetch all documents except Ansible
docker run -v my_dir:/output ghcr.io/openzim/devdocs devdocs2zim --all --skip-slug-regex "^ansible.*"

# Fetch Vue related documents
docker run -v my_dir:/output ghcr.io/openzim/devdocs devdocs2zim --slug vue~3 --slug vue_router~4

# Fetch the docs for the two most recent versions of each software
docker run -v my_dir:/output ghcr.io/openzim/devdocs devdocs2zim --first=2
```


**One of the following flags is required:**

* `--all`: Fetch all Devdocs resources, and produce one ZIM per resource.
* `--slug SLUG`: Fetch the provided Devdocs resource. Slugs are the first path entry in the Devdocs URL.
    For example, the slug for: `https://devdocs.io/gcc~12/` is `gcc~12`. Use --slug several times to add multiple.
* `--first N`: Fetch the first number of items per slug as shown in the DevDocs UI.


**Optional Flags:**

*  `--skip-slug-regex REGEX`: Skips slugs matching the given regular expression.
*  `--output OUTPUT_FOLDER`: Output folder for ZIMs. Default: /output
*  `--creator CREATOR`: Name of content creator. Default: 'DevDocs'
*  `--publisher PUBLISHER`: Custom publisher name. Default: 'openZIM'
*  `--name-format FORMAT`: Custom name format for individual ZIMs.
    Default: 'devdocs_{slug_without_version}_{version}'
*  `--title-format FORMAT`: Custom title format for individual ZIMs.
    Value will be truncated to 30 chars. Default: '{full_name} Documentation'
*  `--description-format FORMAT`: Custom description format for individual ZIMs.
    Value will be truncated to 80 chars. Default: '{full_name} Documentation'
*  `--long-description-format FORMAT`: Custom long description format for your ZIM.
    Value will be truncated to 4000 chars.Default: '{full_name} documentation by DevDocs'
*  `--tag TAG`: Add tag to the ZIM. Use --tag several times to add multiple.
    Formatting is supported. Default: ['devdocs', '{slug_without_version}']
*  `--logo-format FORMAT`: URL/path for the ZIM logo in PNG, JPG, or SVG format.
    Formatting placeholders are supported. If unset, a DevDocs logo will be used.

**Formatting Placeholders**

The following formatting placeholders are supported:

* `{name}`: Human readable name of the resource e.g. `Python`.
* `{full_name}`: Name with optional version for the resource e.g. `Python 3.12`.
* `{slug}`: Devdocs slug for the resource e.g. `python~3.12`.
* `{clean_slug}`: Slug with non alphanumeric/period characters replaced with `-` e.g. `python-3.12`.
* `{slug_without_version}`: Devdocs slug for the resource without the version e.g. `python`.
* `{version}`: Shortened version displayed in devdocs, if any e.g. `3.12`.
* `{release}`: Specific release of the software the documentation is for, if any e.g. `3.12.1`.
* `{attribution}`: License and attribution information about the resource.
* `{home_link}`: Link to the project's home page, if any: e.g. `https://python.org`.
* `{code_link}`: Link to the project's source, if any: e.g. `https://github.com/python/cpython`.
* `{period}`: The current date in `YYYY-MM` format e.g. `2024-02`.

## Developing

Use the commands below to set up the project once:

```sh
# Install hatch if it isn't installed already.
❯ pip install hatch

# Local install (in default env) / re-sync packages
❯ hatch run pip list

# Set-up pre-commit
❯ pre-commit install
```

The following commands can be used to build and test the scraper:

```sh
# Show scripts
❯ hatch env show

# linting, testing, coverage, checking
❯ hatch run lint:all
❯ hatch run lint:fixall

# run tests on all matrixed' envs
❯ hatch run test:run

# run tests in a single matrixed' env
❯ hatch env run -e test -i py=3.12 coverage

# run static type checks
❯ hatch env run check:all

# building packages
❯ hatch build
```


### Contributing

This project adheres to openZIM's [Contribution Guidelines](https://github.com/openzim/overview/wiki/Contributing).

This project has implemented openZIM's [Python bootstrap, conventions and policies](https://github.com/openzim/_python-bootstrap/docs/Policy.md) **v1.0.3**.
