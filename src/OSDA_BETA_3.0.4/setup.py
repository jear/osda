#!/usr/bin/env python
from setuptools import setup, find_packages
import sys
import os
from glob import glob
import re

ipAddress = None
if "--ip" not in sys.argv:
    ipAddress = input("\nEnter IP address (to be configured): ")

if not ipAddress:
    index = sys.argv.index('--ip')
    ipAddress = sys.argv[index + 1]
    sys.argv.remove("--ip")
    del sys.argv[index]

with open('etc/config.ini', 'r') as inputFile:
    content = inputFile.read()
    newContent = re.sub('server =.*', 'server = {}'.format(ipAddress), content, flags=re.M)

with open('etc/config.ini', 'w+') as targetFile:
    targetFile.write(newContent)

# Check for python version
if sys.version_info.major < 3:
    print("Python3 is required for this module.. Exiting")

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    requires = fh.read()

# TODO: Need update while using this for Windows
configFiles = "/opt/hpe/osda/etc"
LibFiles  = "/opt/hpe/osda/lib"
BinFiles  = "/opt/hpe/osda/bin"
DataFiles = "/opt/hpe/osda/data"
Logfiles  = "/opt/hpe/osda/log"
PythonExe  = "/opt/hpe/osda/bin/python"

# The default used earlier are still continuing here
#/opt/hpe/osda/data/config
#/opt/hpe/osda/data/activities
#/opt/hpe/osda/data/kickstarts
#/opt/hpe/osda/data/scratch/
#/opt/hpe/osda/data/certs

DataFiles = [
    (configFiles, ['etc/config.ini']),
    (LibFiles, []),
    (BinFiles, ['osda/osda-server']),
    (DataFiles, []),
    (Logfiles, []),
    ('/lib/systemd/system', ['service/osda.service']),
    ('/opt/hpe/osda/data/config', []),
    ('/opt/hpe/osda/data/activities', []),
    ('/opt/hpe/osda/data/kickstarts', []),
    ('/opt/hpe/osda/data/scratch', []),
    ('/opt/hpe/osda/data/certs', []),
]

# Delete ksfiles.json, this file will be generated with new code
if os.path.exists('/opt/hpe/osda/data/config/ksfiles.json'):
   os.remove('/opt/hpe/osda/data/config/ksfiles.json')

# Copy kickstart files
baseKickStartDir = "/opt/hpe/osda/data"
for i in os.walk('kickstarts'):
    destFile = os.path.join(baseKickStartDir, i[0])
    if not i[2]:
       continue
    srcFile = [ os.path.join(i[0], x) for x in i[2] ]
    DataFiles.append((destFile, srcFile))

setup(
    name="osda-server",
    version="0.1",
    packages=find_packages(),
    install_requires=[requires],
    data_files=DataFiles,

    # metadata to display on PyPI
    author="Global Solutions Engineering, HPE",
    author_email="govind.avireddi@hpe.com, jih-tsen.nat.lin@hpe.com, rishikesh.yalla@hpe.com, avinash.jalumuru@hpe.com",
    description="OSDA packages for baremetal deployment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.hpe.com/govind-avireddi/OSDA",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Python Software Foundation License"
    ]
)

if not os.path.exists(PythonExe):
    executable = sys.executable
    os.symlink(executable, PythonExe)
