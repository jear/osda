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
import string, re
import subprocess
import json
import tempfile
import uuid
import osda.config as config
import logging
#import ospackages

defaultConfig = config.DefaultConfig()
ksBaseImg = defaultConfig.ksBaseImg

###################################################################
#This function to modify KS file to update hostname, ipaddress..etc
###################################################################
def modifyKSFile(baseKSFile, targetKSFile, OSConfigJSON):
    
    def flat_json(nestedJson):
        out = {}
        
        def flatten(entry, parent=''): 
            if type(entry) is dict: 
                for key,value in entry.items(): 
                    flatten(value, parent + key + '.') 
            # If the Nested key-value 
            # pair is of list type 
            elif type(entry) is list: 
                i = 0
                for item in entry:                 
                    flatten(item, parent + str(i) + '.') 
                    i += 1
            else: 
                out[parent[:-1]] = entry
        
        flatten(nestedJson) 
        return out 
    
    def readOScfg(json, parameter):
        try:
            return json[parameter]
        except:
            return ''

    try:
        if "kickstartFile" in OSConfigJSON and OSConfigJSON['kickstartFile'] != "":
            # If user defined kickstart is present then append the filename to baseKS path
            ksfile_name = os.path.dirname(baseKSFile) + os.sep + OSConfigJSON['kickstartFile']
        else:
            ksfile_name = baseKSFile

        flat_OSConfigJSON = flat_json(OSConfigJSON)

        requiredKsVars = {
            "%HOSTNAME%": readOScfg(flat_OSConfigJSON,'hostName'),
            "%SSH_KEY%": readOScfg(flat_OSConfigJSON, "sshKey"),
            "%HTTP_PROXY%": readOScfg(flat_OSConfigJSON, "httpProxy"),
            "%HTTPS_PROXY%": readOScfg(flat_OSConfigJSON, "httpsProxy"),
            "%NO_PROXY%": readOScfg(flat_OSConfigJSON, "noProxy"),
            "%IPADDR1%": readOScfg(flat_OSConfigJSON, 'networks.0.ipAddr'),
            "%NETMASK1%": readOScfg(flat_OSConfigJSON, 'networks.0.netmask'),
            "%CIDR1%": str(netmaskToCIDR(readOScfg(flat_OSConfigJSON, 'networks.0.netmask'))),
            "%GATEWAY1%": readOScfg(flat_OSConfigJSON,'networks.0.gateway'),
            "%DNS11%": readOScfg(flat_OSConfigJSON, 'networks.0.dns'),
            "%MAC11%": readOScfg(flat_OSConfigJSON, 'networks.0.nic1.macAddress'),
            "%MAC12%": readOScfg(flat_OSConfigJSON, 'networks.0.nic2.macAddress'),
            "%VLANS1%": readOScfg(flat_OSConfigJSON, 'networks.0.vlans'),
            "%IPADDR2%": readOScfg(flat_OSConfigJSON, 'networks.1.ipAddr'),
            "%NETMASK2%": readOScfg(flat_OSConfigJSON, 'networks.1.netmask'),
            "%CIDR2%": str(netmaskToCIDR(readOScfg(flat_OSConfigJSON, 'networks.1.netmask'))),
            "%GATEWAY2%": readOScfg(flat_OSConfigJSON, 'networks.1.gateway'),
            "%DNS21%": readOScfg(flat_OSConfigJSON, 'networks.1.dns'),
            "%MAC21%": readOScfg(flat_OSConfigJSON, 'networks.1.nic1.macAddress'),
            "%MAC22%": readOScfg(flat_OSConfigJSON,'networks.1.nic2.macAddress'),
            "%VLANS2%": readOScfg(flat_OSConfigJSON, 'networks.1.vlans'),
            "%DRIVEID%": readOScfg(flat_OSConfigJSON, 'osDrive.driveID')
        }

        if requiredKsVars["%HTTP_PROXY%"] or requiredKsVars["%HTTPS_PROXY%"]:
            requiredKsVars['%ENABLE_PROXY%'] = 'true'

        # Brute force replace all kickstart variables
        ks_fopen = open(ksfile_name).read()
        for ksVar, OSconfig in requiredKsVars.items():
            ks_fopen = ks_fopen.replace(ksVar, OSconfig)
        
        # Brute force removing unused kickstart variables
        pattern = re.compile('%[a-zA-Z]+[a-zA-f0-9]*%')
        matches = re.findall(pattern, ks_fopen)
        if len(matches) > 0:
            logging.warn('Missing expected input parameters for kickstart variables. Deployment may fail.')
        for ksVar in matches:
            logging.warn(f'Missing input parameter for {ksVar}')
            ks_fopen = ks_fopen.replace(ksVar, '')

        ks_fopenW = open(targetKSFile, 'w')
        ks_fopenW.write(ks_fopen)
        ks_fopenW.close()
    except KeyError as kerr:
        raise Exception(f"Error accessing OSconfig parameter: " + str(kerr))
    except Exception as err:
        raise Exception(str(err))

###################################################################
#This function to create IMG file for USB media
###################################################################

#def createKickstartImage(KSPath):
def createKickstartImage(targetksfile, targetksimagefile, osType):

    # There is an empty Image file that should be modified by adding 
    # new ks.cfg to create image file with ks.cfg

    # KSFile, ext=os.path.splitext(imgFileName)
    tempDir = tempfile.TemporaryDirectory()
    logging.info("Temp directory: " + tempDir.name)

    cmd='cp ' + ksBaseImg + ' ' + targetksimagefile
    os.system(cmd)

    #Modify USB Image IMage for new ks file
    cmd = 'kpartx -av '+ targetksimagefile
    cmd_out =  subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout
    loopDev=str(cmd_out.read().split()[2],'utf-8')

    cmd = 'mount /dev/mapper/' + loopDev + ' ' + tempDir.name
    os.system(cmd)

    # Copy the kickstart file to root of the image mount location
    # The filename of kickstart inside the image should only be ks.cfg
    if "SLES15" == osType.upper():
        logging.debug("generateKickStart: OS is SLES15")
        cmd = 'cp ' + targetksfile + ' ' + tempDir.name + "/autoinst.xml"
    else:
        cmd = 'cp ' + targetksfile + ' ' + tempDir.name + "/ks.cfg"
    os.system(cmd)

    cmd = 'umount ' + tempDir.name 
    os.system(cmd)

    cmd = 'kpartx -d '+ targetksimagefile
    os.system(cmd)
    
    return targetksimagefile


# Returns the http URL for accessing generated image file
#def generateKickStart(baseksfile, targetdir, OSConfigJSON):
def generateKickStart(osType, targetdir, OSConfigJSON):

    logging.debug("generateKickStart: osType: {osType}, targetdir: {target}, " \
                  "osconfigjson: {osCfg}".format(osType=osType, target=targetdir, osCfg=OSConfigJSON));

    # TODO: this function needs implementation
    baseksfile = getBaseKSFile(osType)
    if baseksfile == "":
        logging.exception("Fail to generate kickstart file. Unsupported OS type specified")
        raise Exception("Fail to generate kickstart file. Unsupported OS type specified")

    #outksfile = open(baseksfile, 'r')
    # Generate path for new ks.cfg file

    # Generate temp path for server specific ks.cfg
    #newimagefilename = uuid.uuid4().hex + ".img"
    newfilename = uuid.uuid4().hex 
    targetksfile = os.path.join(targetdir, newfilename + ".cfg")
    targetksimagefile = os.path.join(targetdir, newfilename + ".img")

    # Get OS Type from OSPackage name
    #package = ospackages.getOSPackage(OSConfigJSON['osPackage'])
    #print("generateKickStart: osType: " + package['osType'])

    logging.debug("generateKickStart: targetksFile: {ksFile}, targetksImageFile: {ksImage}, " \
                  .format(ksFile=targetksfile, ksImage=targetksimagefile));

    # Generate customized ks.cfg file based on OSConfigJSON data
    modifyKSFile(baseksfile, targetksfile, OSConfigJSON)

    # Create FAT32 imagefile with the customized ks.cfg in it
    ksimagepath = createKickstartImage(targetksfile, targetksimagefile, osType)

    #outksfile.close()

    return ksimagepath

def getBaseKSFile(osType):
    try:
        ksfiles = None
        with open(defaultConfig.kickstartFile, 'r') as fin:
            ksfiles = json.load(fin)
        if ksfiles:
            for ksfile in ksfiles:
                logging.debug(ksfile)
                if ksfile["osType"] == osType:
                    return ksfile["basekspath"]
            return ""
        else:
            raise Exception(f'Failed to read kickstart files from {defaultConfig.kickstartFile}. Check OSDA installation')
    except Exception as err:
        raise Exception(str(err))

def cleanupKickstartFiles(ksfilepath):

    os.remove(ksfilepath)

    # Remove the file with .cfg extension also
    os.remove(ksfilepath.replace(".img", ".cfg"))


###################################################
# Fucntion to convert netmask to CIDR
#
# Input: Netmask (255.255.255.0)
# Output: CIDR (24)
#
# Note: The output is 24 and is not /24
###################################################
def netmaskToCIDR(netmask):
  if not netmask:
     return "24"

  return(sum([ bin(int(bits)).count("1") for bits in netmask.split(".") ]))


if __name__ == '__main__':
    OSConfigJSON = {}

    baseKSFile = getBaseKSFile("SLES15")
    print("baseKSFile: " + baseKSFile)
    #cleanupKickstartFiles("/var/www/html/4e616a8bdf224eae9f18024c274e7bca.img")


#    generateKickStart("../kickstarts/ksbase/esxi67/ks.cfg", "/root/KSFILES/", osConfigJSON)

    #imgFileT=createKickstartIMG_ESXi67('/root/Walkman/kickstarts/esxi67/ks.cfg')
#    copyToHttp(imgFileT)
