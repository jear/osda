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


import os
import tempfile
import uuid
import logging

###################################################################
# 
###################################################################
def createKickstartISO_ESXi67(ISOPath, TargetISOBasePath,hostOSdistro):
    try:
        logging.debug("createKickstartISO_ESXi67: ISOPath: " + str(ISOPath) + " TargetISOBasePath: " + str(TargetISOBasePath))
        
        # Create a temp directory and mount the input ISO to that path
        mountpath = tempfile.TemporaryDirectory()
        logging.debug("createKickstartISO_ESXi67: mountpath: " + str(mountpath))
        cmd = 'mount -o loop ' + ISOPath + ' ' + mountpath.name
        os.system(cmd)

        # make temp dir for copy of ISO contents
        copypath = tempfile.TemporaryDirectory()
        #copypath = "/tmp/test121"
        logging.debug("createKickstartISO_ESXi67: copypath: " + str(copypath))

        # Copy the contents of ISO for adding Kickstart file path to kernel opts
        cmd = 'cp -rpT ' + mountpath.name + '/ ' + copypath.name
        #cmd = 'cp -rpT ' + mountpath.name + ' ' + copypath
        logging.debug(cmd)
        os.system(cmd)
        # What happens if cp fails due to lack of disk space? Need to handle this scenario

        # Unmount the ISO 
        cmd = 'umount ' + mountpath.name
        os.system(cmd)

        # Modify boot.cfg files for both Legacy and EFI with kernel opts specifying 
        # Kickstart file 'ks.cfg' is expected under root directory of mounted virtual floppy
        addKSPath2BootCFG(copypath.name, 'ks=usb')
        #addKSPath2BootCFG(copypath, 'ks=usb')

        newISOfilename = os.path.join(TargetISOBasePath, uuid.uuid4().hex + ".ISO") 
        logging.info("createKickstartISO_ESXi67: newISOfilename: " + str(newISOfilename))

        #genISO(copypath, '/tmp/new_iso.ISO')
        genISO(copypath.name, newISOfilename, hostOSdistro)

        return newISOfilename
    except Exception as err:
            logging.exception(err)
            raise Exception from err

###################################################################
# This function modifies boot.cfg files with Kickstart file URL in kernel opts
###################################################################
def addKSPath2BootCFG(ISOCopyPath, KSFilePath4KernelOpts):
    try:
        logging.debug("addKSPath2BootCFG: ISOCopyPath: " + ISOCopyPath + " KSFilePath4KernelOpts: " + KSFilePath4KernelOpts)

        # Modify Legacy boot boot.cfg with Kickstart path
        bootcfgpath = ISOCopyPath + '/boot.cfg'
        if os.path.exists(bootcfgpath) == True:
            logging.info("Legacy boot config file found in ISO copy....")
            modifyBootCFGFile(bootcfgpath, KSFilePath4KernelOpts)
        else:
            logging.info("Legacy boot config file NOT found in ISO copy....")

        # Modify EFI boot boot.cfg with Kickstart path
        bootcfgpath = ISOCopyPath + '/efi/boot/boot.cfg'
        if os.path.exists(bootcfgpath) == True:
            logging.info("EFI boot config file found in ISO copy....")
            modifyBootCFGFile(bootcfgpath, KSFilePath4KernelOpts)
        else:
            logging.info("EFI boot config file NOT found in ISO copy....")
    except Exception as err:
            logging.exception(err)
            raise Exception from err

def modifyBootCFGFile(bootCFGPath, kernelOption):
    try:
        logging.debug(bootCFGPath)

        #fh, abs_path = tempfile.mkstemp()
        #print("abx_path: " + str(abs_path))
        logging.debug("bootCFGPath: " + str(bootCFGPath))
        newbootfile = bootCFGPath + "1"
        logging.debug("newbootfile: " + str(newbootfile))
        #with os.fdopen(fh, 'w') as newfile:
        with open(newbootfile, 'w+') as newfile:
            with open(bootCFGPath, "r") as orgfile:
                for line in orgfile:
                    if line.startswith('kernelopt='):
                        logging.info("Adding kickstart option: line: " + line )
                        line1 = line.replace('\n', ' ')
                        logging.info("Adding kickstart option: line1: " + line1 )
                        logging.info("Adding kickstart option: kernelOption: " + kernelOption )
                        logging.info("Adding kickstart option: " + line1 + " " + kernelOption)
                        newfile.write(line1 + ' ' + kernelOption + '\n')
                    else:
                        newfile.write(line)
        orgfile.close()
        newfile.close()
        # remove the original file
        os.remove(bootCFGPath)

        # Move the updated file from temp dir to replace the original file
        #os.rename(abs_path, bootCFGPath)
        os.rename(newbootfile, bootCFGPath)
        # change the file permissions to readonly
        cmd = '/usr/bin/chmod 555 ' + newbootfile
        logging.debug(cmd)
        os.system('/usr/bin/chmod 555 ' + bootCFGPath)
    except Exception as err:
            logging.exception(err)
            raise Exception from err


###################################################################
# Generates ISO 9660 image with contents from 'sourcePath'
###################################################################
def genISO(sourcePath, targetISOPath,hostOSdistro):
    try:
        from shutil import which as which
        cmd = ''
        if hostOSdistro in ['centos','rhel']:
            if which('genisoimage'):
                cmd = '/usr/bin/genisoimage -relaxed-filenames -J -R -o %ISOPATH% -b isolinux.bin -c boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot -e efiboot.img -no-emul-boot %CONTENTS_DIR%'
            else:
                raise Exception('genisoimage tool not found. Need to be installed')
        elif hostOSdistro in ['sles']:
            if which('xorriso') and which('mkisofs'):
                cmd = 'xorriso -as mkisofs -relaxed-filenames -J -R -o %ISOPATH% -b isolinux.bin -c boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot -e efiboot.img -no-emul-boot %CONTENTS_DIR%'
            else:
                raise Exception('xorriso or mkisofs not found. Need to be installed')
        else:
            raise Exception('Host OS distro may not be supported')

        cmd1 = cmd.replace('%ISOPATH%', targetISOPath)
        cmd2 = cmd1.replace('%CONTENTS_DIR%', sourcePath)

        logging.debug("genISO: cmd2: " + str(cmd2))

        os.system(cmd2)
    except Exception as err:
            logging.exception(err)
            raise Exception from err


#if __name__ == '__main__':
#
#
#    print('Main 0')
#    createKickstartISO_ESXi67('/root/ISOs/VMware-ESXi-6.7.0-Update1-10302608-HPE-Gen9plus-670.U1.10.3.5.12-Oct2018.iso', '/root/Walkman/kickstarts/esxi67/ksvcf.cfg')