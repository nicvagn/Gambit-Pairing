# Building Executable

## steps to get windows executable
### I am told:
"Something I forgot to mention is that cx freeze will not work with anything newer than python 3.12"

1. install python requirements
`pip install -r requirements.txt`
2. to get windows executable
python setup.py build

> for an installer:
`python setup.py bdist_msi`

> this is 2nd hand information. But should get you started.
