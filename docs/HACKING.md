# HACKING.md

# to build:
- requires on path:
    - bash
    - pip or pip3 (if so replace pip with pip3)
    - python3.8 or newer

    test building with `bash ./build.sh`

# recommendations for developers:
    1. Install in a virtual environment
    IE:
    ```bash
    $ cd your-python-project
    $ python -m venv .venv
    ```

    2. Activate your environment with:
      `source .venv/bin/activate` on Unix/macOS
        or   `.venv\Scripts\activate` on Windows

    3. Install as editable
    ```bash
    $ pip install --editable .
    ```
