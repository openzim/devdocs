# Devdocs scraper

This scraper downloads [devdocs.io](https://devdocs.io/) documentation databases and puts them in ZIM files,
a clean and user friendly format for storing content for offline usage.

[![CodeFactor](https://www.codefactor.io/repository/github/openzim/devdocs/badge)](https://www.codefactor.io/repository/github/openzim/devdocs)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![codecov](https://codecov.io/gh/openzim/devdocs/branch/main/graph/badge.svg)](https://codecov.io/gh/openzim/devdocs)
[![PyPI version shields.io](https://img.shields.io/pypi/v/devdocs2zim.svg)](https://pypi.org/project/devdocs2zim/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/devdocs2zim.svg)](https://pypi.org/project/devdocs2zim)


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
docker run -v my_dir:/output ghcr.io/openzim/devdocs devdocs2zim [--all|--slug=SLUG]
```

**Flags**

* `--all`: Fetch all Devdocs resources, and produce one ZIM per resource.
* `--slug`: Fetch the provided Devdocs resource, producing a single ZIM.
    Slugs are the first path entry in the Devdocs URL. For example, the slug for: `https://devdocs.io/gcc~12/` is `gcc~12`.
* `--title`:  (Optional) Set the title for the ZIM, supports the placeholders listed below.
* `--description`: (Optional) Set the description for the ZIM, supports the placeholders listed below.
* `--devdocs-endpoint`: (Optional) Override the Devdocs URL endpoint.
* `--filename`: (Optional) Set the output file name, supports the placeholders listed below.

**Placeholders**

* `{name}`: Human readable name of the Devdocs resource e.g. `Python 3.12`.
* `{slug}`: Devdocs slug for the resource e.g. `python~3.12`.
* `{license}`: License information about the resource.

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

This project has implemented openZIM's [Python bootstrap, conventions and policies](https://github.com/openzim/_python-bootstrap/docs/Policy.md) **v1.0.2**.
