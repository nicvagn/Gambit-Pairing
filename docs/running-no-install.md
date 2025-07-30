# Gambit Pairing - run from src tree

Due to being 100% python, you can run Gambit Pairing without installing it.

## how:

- install the dependancies listed in the pyproject.toml table.
file: `Gambit-Pairing/pyproject.toml`
```toml
[project]
name = "gambit-pairing"
version = "0.5.0a0"
dependencies = [***HERE***]
```

run the bash file `Gambit-Pairing/launch.sh`
> this can be done from wsl, or you can install Gentoo

OR

run
```bash
python3 src/gambitpairing
```
