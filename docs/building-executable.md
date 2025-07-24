# Building Executable

## How to build an exectable with setup.py

### Note:
cx_freeze does not support python 3.13

#### Install python requirements
1. `pip install -r requirements.txt`
2. `pip install cx_freeze`
3. Use the build commands for your operating system

---

## All cx_Freeze build commands supported by this setup.py

### Windows
- Build executable:
  ```
  python setup.py build
  ```
- Build MSI installer:
  ```
  python setup.py bdist_msi
  ```

### macOS
- Build macOS app bundle:
  ```
  python setup.py bdist_mac
  ```

### Linux
- Build RPM package:
  ```
  python setup.py bdist_rpm
  ```
- Build DEB package:
  ```
  python setup.py bdist_deb
  ```

---

> Run these commands on the appropriate operating system for the desired output.
