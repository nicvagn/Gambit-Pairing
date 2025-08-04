# installing.md - installing Gambit Pairing with pip

# Installation - pip

1. Install Python 3.8 or higher.
2. Download or clone this repository.
3. if bash is on your $PATH run install.sh
    OR
   >install the pip package defined by the pyproject.toml requirements table
   >from the root dir with pyproject.toml
   >```bash
   >pip install .
   >```

## Usage

- Run the application:
    ```bash
    gambit-pairing
    ```

# installation - pyinstaller executable -- on unixlike system

```bash
./make_executable.sh

cp dist/Gambit-Pairing ~/.local/bin/
```
now Gambit-Pairing should be executable from shell
* if ~/.local/bin is on path
