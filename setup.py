import sys

from cx_Freeze import Executable, setup

# Platform-specific base
if sys.platform == "win32":
    base = "Win32GUI"
elif sys.platform == "darwin":
    base = "MacOSX"
else:
    base = None

build_exe_options = {
    "include_files": [
        "styles.qss",
        ("resources/icons/icon.ico", "icon.ico"),
        "LICENSE",
        "core/",
        "gui/",
        "resources/",
        "license.rtf",
        "icon.png"
    ],
}

# Platform-specific options
options = {"build_exe": build_exe_options}

if sys.platform == "win32":
    options["bdist_msi"] = {
        "upgrade_code": "{E7CDA630-CB74-4A99-BDB4-F09CB777D3F8}",
        "add_to_path": False,
        "initial_target_dir": r"[ProgramFilesFolder]\Gambit Pairing",
        "install_icon": "icon.ico",
        "launch_on_finish": True,
        "license_file": "license.rtf",
    }
elif sys.platform == "darwin":
    options["bdist_mac"] = {
        "bundle_name": "Gambit Pairing",
        "iconfile": "icon.ico",
        "license": "license.rtf",
    }
else:
    options["bdist_rpm"] = {
        "name": "GambitPairing",
        "requires": ["python3"],
        "license": "LICENSE",
        "icon": "icon.png",
        'debug': False
    }
    options["bdist_deb"] = {
        "name": "GambitPairing",
        "requires": ["python3"],
        "license": "LICENSE",
        "icon": "icon.png",
    }

executables = [
    Executable(
        script="main.py",
        base=base,
        icon="icon.ico",
        target_name="GambitPairing.exe" if sys.platform == "win32" else "GambitPairing",
        shortcut_name="Gambit Pairing" if sys.platform == "win32" else None,
        shortcut_dir="DesktopFolder" if sys.platform == "win32" else None
    )
]

setup(
    name="Gambit Pairing" if sys.platform == "win32" else "GambitPairing",
    version="0.5.0",
    description="Gambit Pairing",
    options=options,
    executables=executables
)

