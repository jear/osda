# -*- coding: utf-8 -*-
###
# Copyright 2020 Hewlett Packard Enterprise
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
###

import subprocess
import copy
import os
import tempfile
import uuid
import logging
import stat
import contextlib

ksBaseImage = "/opt/hpe/osda/data/kickstarts/ks_base.img"

###################################################################
# Linux pushd functionality
###################################################################
@contextlib.contextmanager
def pushd(new_dir):
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(previous_dir)

###################################################################
# Modify ISO with Autoyast Configuration
###################################################################
def createAutoYastISO(ISOPath, targetPath,hostOSdistro):
    try:
        logging.info("createAutoYastISO: ISOPath: " + str(ISOPath) + " TargetISOBasePath: " + str(targetPath))
        
        # Create a temp directory and mount the input ISO to that path
        mountPath =  "/tmp/" + str(uuid.uuid1())
        copyPath = "/tmp/" + str(uuid.uuid1())
        os.mkdir(mountPath)
        os.mkdir(copyPath)
        logging.debug("createAutoYastISO: mountpath: " + str(mountPath))
        cmd = 'mount -o loop ' + ISOPath + ' ' + str(mountPath)
        os.system(cmd)
        logging.debug("createAutoYastISO: copypath: " + str(copyPath))
        cmd = 'cp -rpT ' + mountPath  + " " + copyPath
        os.system(cmd)
        cmd = 'umount ' + str(mountPath)
        os.system(cmd)
        os.rmdir(str(mountPath))

        # Path of autoyast file 'autoinst.yml' in mounted virtual floppy
        kernelOption = "autoyast=usb:///autoinst.xml"
        addKSPath2BootCFG(copyPath, kernelOption)

        newISOfilename = os.path.join(targetPath, uuid.uuid4().hex + ".iso")
        genISO(copyPath, newISOfilename, hostOSdistro)

        return newISOfilename
    except Exception as err:
        logging.exception(err)
        raise Exception from err
        
###################################################################
# This function modifies boot.cfg files with Kickstart file URL in kernel opts
###################################################################
def addKSPath2BootCFG(ISOCopyPath, autoyastKernelOptions):

    logging.info("addKSPath2BootCFG: ISOCopyPath: " + ISOCopyPath + " autoyastKernelOptions: " + autoyastKernelOptions)

    # Modify Legacy boot boot.cfg with Kickstart path
    bootcfgpath = ISOCopyPath + '/boot/x86_64/loader/isolinux.cfg'
    if os.path.exists(bootcfgpath) == True:
        logging.info("Legacy boot config file found in ISO copy....")
        modifyBootCFGFile(bootcfgpath, autoyastKernelOptions, "Legacy")
    else:
        logging.info("Legacy boot config file NOT found in ISO copy....")

    # Modify EFI boot boot.cfg with Kickstart path
    bootcfgpath = ISOCopyPath + '/EFI/BOOT/grub.cfg'
    if os.path.exists(bootcfgpath) == True:
        logging.info("EFI boot config file found in ISO copy....")
        modifyBootCFGFile(bootcfgpath, autoyastKernelOptions, "EFI")
    else:
        logging.info("EFI boot config file NOT found in ISO copy....")

def modifyBootCFGFile(bootCFGPath, kernelOption, bootMode):
    try:
        logging.debug(bootCFGPath)

        #fh, abs_path = tempfile.mkstemp()
        #print("abx_path: " + str(abs_path))
        logging.debug("bootCFGPath: " + str(bootCFGPath))
        newbootfile = bootCFGPath + "1"
        logging.debug("newbootfile: " + str(newbootfile))
        #with os.fdopen(fh, 'w') as newFile:
        skipLine = False
        with open(newbootfile, 'w+') as newFile:
            with open(bootCFGPath, "r") as orgfile:
                for line in orgfile:
                    if bootMode == "Legacy":
                        if line.find("append ") > 0:
                            newFile.write("{} {}\n".format(line.strip('\n'), kernelOption))
                        elif line.startswith("default"):
                            newFile.write("default linux\n")
                        else:
                            newFile.write(line)
                    
                    if bootMode == "EFI":
                        if line.find("linuxefi") > 0:
                            newFile.write("{} {}\n".format(line.strip('\n'), kernelOption))
                        elif line.find("timeout") > 0:
                            lhsIndex = line.index('=') + 1
                            if not lhsIndex or lhsIndex <= 1:
                                newFile.write(line)
                            else:
                                newFile.write("{}{}\n".format(line[0:lhsIndex], 5))
                        else:
                            newFile.write(line)

        # remove the original file
        os.remove(bootCFGPath)

        # Move the updated file from temp dir to replace the original file
        os.rename(newbootfile, bootCFGPath)

        # change the file permissions to readonly
        os.chmod(bootCFGPath, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except Exception as err:
            logging.exception(err)
            raise Exception from err


###################################################################
# Generates ISO 9660 image with contents from 'sourcePath'
###################################################################
def genISO(sourcePath, targetISOPath,hostOSdistro):
    try:
        from shutil import which as found
        cmd = ''
        if hostOSdistro.strip() in ['centos','rhel']:
            if found('genisoimage'):
                cmd =  'genisoimage -relaxed-filenames -J -R -o %ISOPATH% -b boot/x86_64/loader/isolinux.bin -c boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot -e boot/x86_64/efi -no-emul-boot %CONTENTS_DIR%'
            else:
                raise Exception('genisoimage tool not found. Need to be installed')
        elif hostOSdistro.strip() in ['sles']:
            if found('xorriso') and found('mkisofs'):
                cmd = 'xorriso -as mkisofs -relaxed-filenames -J -R -o %ISOPATH% -b boot/x86_64/loader/isolinux.bin -c boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot -e boot/x86_64/efi -no-emul-boot %CONTENTS_DIR%'
            else:
                raise Exception('xorriso or mkisofs not found. Need to be installed')
        else:
            raise Exception('Host OS distro may not be supported')    
        cmd = cmd.replace('%ISOPATH%', targetISOPath)
        cmd = cmd.replace('%CONTENTS_DIR%', sourcePath)
        logging.info (cmd)
        logging.info("genISO: cmd: " + str(cmd))
        with pushd(sourcePath):
            os.system(cmd)
    except Exception as err:
            logging.exception(err)
            raise Exception from err


if __name__ == '__main__':
    print('Main 0')
    createAutoYastISO('/root/SLE-15-SP1-Installer-DVD-x86_64-GM-DVD1.iso', '/tmp')


