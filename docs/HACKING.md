# HACKING.md

# to build:

- requires on path:

  - bash
  - pip or pip3 (if so replace pip with pip3)
  - python3.8 or newer
  - all runtime dependencies

  test building with `python3 -m build .`
# dependencies
    can be installed with sh script: `ensure-all-dependancies.sh`
    will parse the pyproject.toml and install with pip

# recommendations for developers:

    1. Install in a virtual environment
    IE:
    ```bash
    $ cd Gambit-Pairing
    $ python -m venv .venv
    ```

    2. Activate your environment with:
      `source .venv/bin/activate` on Unix/macOS
        or   `.venv\Scripts\activate` on Windows

    3. Install as editable
    ```bash
    $ pip install --editable .
    ```
    >A helper script in the git root called "install_editable_pip.sh" should automate this.

# Then

load the tournament defined in /test_data/tournaments/test_32_players***
