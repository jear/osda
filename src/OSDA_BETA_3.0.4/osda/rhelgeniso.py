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

ksBaseImage = "/opt/hpe/osda/data/kickstarts/ks_base.img"
###################################################################
# 
###################################################################
def createKickstartISO_RHEL76(ISOPath, targetPath, hostOSdistro):
    try:
        logging.info("createKickstartISO_RHEL76: ISOPath: " + str(ISOPath) + " TargetISOBasePath: " + str(targetPath))
        
        # Create a temp directory and mount the input ISO to that path
        mountPath =  "/tmp/" + str(uuid.uuid1())
        copyPath = "/tmp/" + str(uuid.uuid1())
        os.mkdir(mountPath)
        os.mkdir(copyPath)
        logging.debug("createKickstartISO_RHEL76: mountpath: " + str(mountPath))
        cmd = 'mount -o loop ' + ISOPath + ' ' + str(mountPath)
        os.system(cmd)
        logging.debug("createKickstartISO_RHEL76: copypath: " + str(copyPath))
        cmd = 'cp -rpT ' + mountPath  + " " + copyPath
        os.system(cmd)
        cmd = 'umount ' + str(mountPath)
        os.system(cmd)
        os.rmdir(str(mountPath))
        cmd = 'kpartx -av '+ ksBaseImage
        cmd_out =  subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout
        loopDev = str(cmd_out.read().split()[2],'utf-8')
        cmd = 'blkid /dev/mapper/' + loopDev     
        cmd_out =  subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout
        label = str(cmd_out.read().split()[2],'utf-8').split('=')[1].replace('"',"")

        # Modify boot.cfg files for both Legacy and EFI with kernel opts specifying 
        # Kickstart file 'ks.cfg' is expected under root directory of mounted virtual floppy
        #ks=hd:UUID=3A12-D3C6:/ks.cfg
        kernelOption = "ks=hd:UUID=" + label + ":/ks.cfg"
        addKSPath2BootCFG(copyPath, kernelOption)

        # newISOfilename = os.path.join(TargetISOBasePath, uuid.uuid4().hex) 
        #print("createKickstartISO_RHEL76: newISOfilename: " + str(newISOfilename))
        #newISOfilename = targetPath + "/RHEL7.iso"
        newISOfilename = os.path.join(targetPath, uuid.uuid4().hex + ".ISO")
        genISO(copyPath, newISOfilename, hostOSdistro)

        return newISOfilename
    except Exception as err:
            logging.exception(err)
            raise Exception from err
        
###################################################################
# This function modifies boot.cfg files with Kickstart file URL in kernel opts
###################################################################
def addKSPath2BootCFG(ISOCopyPath, KSFilePath4KernelOpts):

    logging.info("addKSPath2BootCFG: ISOCopyPath: " + ISOCopyPath + " KSFilePath4KernelOpts: " + KSFilePath4KernelOpts)

    # Modify Legacy boot boot.cfg with Kickstart path
    bootcfgpath = ISOCopyPath + '/isolinux/isolinux.cfg'
    if os.path.exists(bootcfgpath) == True:
        logging.info("Legacy boot config file found in ISO copy....")
        modifyBootCFGFile(bootcfgpath, KSFilePath4KernelOpts, "Legacy")
    else:
        logging.info("Legacy boot config file NOT found in ISO copy....")

    # Modify EFI boot boot.cfg with Kickstart path
    bootcfgpath = ISOCopyPath + '/EFI/BOOT/grub.cfg'
    if os.path.exists(bootcfgpath) == True:
        logging.info("EFI boot config file found in ISO copy....")
        modifyBootCFGFile(bootcfgpath, KSFilePath4KernelOpts, "EFI")
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
        #with os.fdopen(fh, 'w') as newfile:
        with open(newbootfile, 'w+') as newfile:
            with open(bootCFGPath, "r") as orgfile:
                for line in orgfile:
                    if "hd:LABEL" in  line:
                        global osLabel
                        osLabel = line.strip().split("hd:LABEL")[1].split()[0].replace('=','')
                        line = line.replace(osLabel, "redhat")
                    if bootMode == "Legacy":
                        if line.startswith('  append') and line.strip('\n').endswith('quiet'):
                            logging.info("Adding kickstart option: kernelOption: " + kernelOption )
                            newfile.write(line.strip('\n') + ' ' + kernelOption + '\n')
                        else:
                            newfile.write(line)
                    if bootMode == "EFI":
                        if  line.strip('\n').endswith('quiet'):
                            logging.info("Adding kickstart option: kernelOption: " + kernelOption )
                            newfile.write(line.strip('\n') + ' ' + kernelOption + '\n')
                        else:
                            if "Test this media" in line:
                                break
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
        logging.info(cmd)
        os.system('/usr/bin/chmod 555 ' + bootCFGPath)
    except Exception as err:
            logging.exception(err)
            raise Exception from err


###################################################################
# Generates ISO 9660 image with contents from 'sourcePath'
###################################################################
def genISO(sourcePath, targetISOPath, hostOSdistro):
    try:
        from shutil import which as which
        cmd = ''
        if hostOSdistro in ['centos','rhel']:
            if which('genisoimage'):
                cmd =  'genisoimage -U -r -v -T -J -joliet-long -V "redhat" -volset "redhat"  -A "redhat"  -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot -e images/efiboot.img -no-emul-boot -o %ISOPATH%   %CONTENTS_DIR%'
            else:
                raise Exception('genisoimage tool not found. Need to be installed')
        elif hostOSdistro in ['sles']:
            if which('xorriso') and which('mkisofs'):
                cmd = 'xorriso -as mkisofs -U -r -v -T -J -joliet-long -V "redhat" -volset "redhat"  -A "redhat"  -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot -e images/efiboot.img -no-emul-boot -o %ISOPATH%   %CONTENTS_DIR%'
            else:
                raise Exception('xorriso or mkisofs not found. Need to be installed')
        else:
            raise Exception('Host OS distro may not be supported')

        cmd1 = cmd.replace('%ISOPATH%', targetISOPath)
        cmd2 = cmd1.replace('%CONTENTS_DIR%', sourcePath)
        logging.info (cmd2)
        import time 
        time.sleep(10)
        logging.info("genISO: cmd2: " + str(cmd2))

        os.system(cmd2)
    except Exception as err:
            logging.exception(err)
            raise Exception from err


if __name__ == '__main__':
#
#
    print('Main 0')
    #createKickstartISO_RHEL76('/root/MadhuR/RHEL-7.6-20181010.0-Server-x86_64-dvd1.iso', "/home/MadhuR")
    createKickstartISO_RHEL76('/tmp/CentOS-7-x86_64-Minimal-1810.iso', "/home/MadhuR")


