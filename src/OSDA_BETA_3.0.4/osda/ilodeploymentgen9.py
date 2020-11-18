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


import json
import threading
import os
import logging

from osda.iloredfishgen9 import ILORedfish

import osda.config as config
import osda.genksimg as genksimg
import osda.hostcheck as hostcheck
import osda.ospackages as ospackages

#data = open("testData.json").read()
#data = json.loads(data)
#hostData = data
defaultconfig = config.DefaultConfig()

#ksBaseEsxi = defaultconfig.ksBaseEsxi
#ksBaseRhel = defaultconfig.ksBaseRhel
#osPackageConfig = config.OSPackage()


def deploy(activitiesConfig, taskID, deployData):

    logging.debug("deploy: taskID: " + str(taskID))
    servers = deployData["hosts"]
    threadfunction = deployOsByIlo
    subtaskID = 0
    for host in servers:
        logging.debug("deployByIlo: host: " + json.dumps(host))
        activitiesConfig.setTaskStatus(taskID, "Running", "");
        activitiesConfig.setSubTaskStatus(taskID, subtaskID, "Initiated", "", 1);
        deploy_bg = threading.Thread(target=threadfunction, args=(activitiesConfig, taskID, subtaskID,  host))
        deploy_bg.start()
        #deployOsByIlo(activitiesConfig, taskID, subtaskID,  host)
        subtaskID = subtaskID + 1

# This is the thread function for deploying OS on one server
def deployOsByIlo(activitiesConfig, taskID, subtaskID, host):
    iloIp =  host["iloIPAddr"]
    iloUser = host["iloUser"]
    iloPassword = host["iloPassword"]
    #OSConfigJSON = host


    logging.debug(host)
    packageName = host['osPackage']
    logging.debug("deployOsByIlo: host['osPackage']: " + packageName)
    logging.debug("##############1##########")

    kickstartFile = ""
    logging.debug("##############2##########")

    try:
        package = ospackages.getOSPackage(host['osPackage'])
        #package = osPackageConfig.getOSPackage(packageName)
        logging.debug("##############3##########")
        iloClient = ILORedfish(iloIp,  iloUser, iloPassword)
        logging.debug(host)

        # There is no point to proceed if server is powered ON
        #
        # Raise Exception
        if iloClient.getPowerState().lower() == "on":
            logging.exception("CRITICAL: Found server {ip} in ON state. CANNOT PROCEED DEPLOYMENT OF {ip}".format(ip=iloIp))
            raise Exception("CRITICAL: Found server {ip} in ON state. CANNOT PROCEED DEPLOYMENT OF {ip}".format(ip=iloIp))

        host_updated = replaceWithILOData(iloClient, host)
        logging.debug("##########")
        logging.debug(host_updated)

    except Exception as err:
        logging.exception(err)
        activitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", "Failed to deploy OS due to errors. " + str(err), -1 );
        return({"result": "Failed to deploy OS due to errors", "error": err})

    activitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "", 1);
    logging.info("deployOsByIlo: Now change the boot-order") 

    # Change the boot order to set the designated OS drive to top in the list
    #try:
    #    iloClient.modifyBootOrder(host_updated['osDrive'])
    #except Exception as err:
    #    activitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", "Failed to modify boot order. " + str(err), -1 );
    #    logging.error("Failed to modify boot order: {}".format(err))
    #    return({"result": "Failed to modify boot order", "error": err})

    activitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "Boot order modified successfully.", 1);
    ## TEMP CODE remove before finalizing 
    # return

    try:
        logging.info("deployOsByIlo: Generate Kickstart") 
        kickstartFile = genksimg.generateKickStart(package['osType'], config.WalkmanSettings().get("local_http_root"), host_updated)
    except Exception as err:
        activitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", "Failed to deploy OS due to errors. " + str(err), -1 );
        logging.error("Failed to deploy OS due to errors: {}".format(err))
        return({"result": "Failed to deploy OS due to errors", "error": err})

    activitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "Kickstart image created", 1);

    try:
        #iloClient.mountVirtualMedia("http://" + str(defaultconfig.htmlWebIP) +"/" + kickstartFile.split('/')[-1], "USBStick")
        logging.info("deployOsByIlo: Mount USB Stick having kickstart") 
        iloClient.mountVirtualMedia( getKSURL(kickstartFile), "USBStick")
    except Exception as err:
        logging.error("Failed to mount the kickstart to iLO Virtual USB: {}".format(err))
        activitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", "Failed to mount the kickstart to iLO Virtual USB. " + str(err), -1 );
        return({"result": "Failed to mount the kickstart to iLO Virtual USB", "error": err})

    logging.debug("next mount ISO")
    activitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "Kickstart image mounted", 1);

    try:
        logging.info("deployOsByIlo: Mount CD ROM") 
        iloClient.mountVirtualMedia(getURLforOSPackage(host_updated['osPackage']), "CD", bootOnNextServerReset=True)
    except Exception as err:
        logging.error("Failed to mount the ISO to iLO Virtual DVD: {}".format(err))
        activitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", "Failed to mount the ISO to iLO Virtual DVD. " + str(err), -1 );
        return({"result": "Failed to mount the ISO to iLO Virtual DVD", "error": err})

    activitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "Kickstart image and ISO mounted successfully.", 1);

    try:
        #iloClient.rebootServer()
        # Validation to do reboot is already done
        # Hence, restting the server to boot the OS from mounted ISO
        logging.info("deployOsByIlo: Reset the machine to install OS") 
        iloClient.resetPowerState()
    except Exception as err:
        activitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", "Server Reboot Failed", -1);
        logging.exception(err)
        return ({"retult": "Failed to Reboot", "error": err})

    activitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "The OS installation with kickstart initiated.", 1);

    hostIpAddress = host_updated["networks"][0]["ipAddr"]
    if hostcheck.isOpen(hostIpAddress, package['osType']) == True:
        logging.info("Deployment completed successfully for TaskID {} subTaskID {} with IP Address {}".format(taskID, subtaskID, hostIpAddress))
        activitiesConfig.setSubTaskStatus(taskID, subtaskID, "Complete", "Deployment completed successfully.", 10);
    else:
        logging.error("Deployment failed for TaskID {} subTaskID {} with IP Address {}".format(taskID, subtaskID, hostIpAddress))
        activitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", "Unable to confirm the completion of the deployment. Server not reachable. ", -1);

    # Cleanup here

    # Unmount media drives
    iloClient.umountAllMediaDrives()

    # Delete kickstart file "kickstartFile"
    genksimg.cleanupKickstartFiles(kickstartFile)


    return activitiesConfig.getTaskStatus(taskID)   


##############################################################################
### This function queries and gets the hardware specific details like mac-address
### Logical Drive ID based on host data which only has generic identifier 
### For network interfaces, this function gets mac-address for interface that matches with portName in the host details
### For logical drivers, this function finds the driveID for the logical drive number in the host details
#############################################################################
def replaceWithILOData(iloClient, host):

    logging.debug("replaceWithILOData: host: ", host)

    #iloIp =  host["iloIPAddr"]
    #iloUser = host["iloUser"]
    #iloPassword = host["iloPassword"]

    #iloClient = ILORedfish(iloIp, iloUser, iloPassword)
    #iloClient.login()
    #networkPorts = getILONetworkConnections_ex(iloIp, iloUser, iloPassword)
    networkPorts = getILONetworkConnections(iloClient)
    logging.debug(networkPorts)

    # portName = "HPE Ethernet 1Gb 4-port 331i Adapter - NIC - NIC.LOM.1.1/1"
    # In the above name, "NIC.LOM.1.1" is structured name of the adapter
    # /1 denotes the port number
    macAddress = ""
    for networkPort in networkPorts:
        logging.debug("######@@@@@@######")
        logging.debug(networkPort)
        if host['networks'][0]['nic1']['adapterId'] == networkPort['adapterId']:
            if host['networks'][0]['nic1']['portId'] == networkPort['portId']:
                macAddress = networkPort['macAddress']
                break

    if macAddress == "":
        logging.error("Cannot find the specfied network adapter/port for nic1")
        raise Exception("Cannot find the specfied network adapter/port for nic1")

    host['networks'][0]['nic1']['macAddress'] = macAddress

    osLogicalDrive = host['osDrive'].get('logicalDrive')
    if not osLogicalDrive:
        logging.error("Missing storage information, no details of logical drive information")
        raise Exception("Missing storage information, no details of logical drive information")

    ################# OS Drive data ########################################
    if 'logicalDrive' in host['osDrive']:
        osLogicalDrive = host['osDrive'].get('logicalDrive')
        if 'operation' in osLogicalDrive:
            operation = osLogicalDrive.get('operation').upper()
        else:
            logging.exception("Missing the property operation in logicalDrive section of deploy JSON")
            raise Exception("Missing the property [operation] in logicalDrive section of deploy JSON")

        if operation == 'USE_EXISTING':
            logicalDrives = getILOStorageDrives(iloClient)
            #logicalDrives = getILOStorageDrives(iloIp, iloUser, iloPassword)
            logging.info(logicalDrives)

            logicalDriveID = ""
            #faultTolerance = ""
            for logicalDrive in logicalDrives:
                if logicalDrive['logicalDriveNumber'] == osLogicalDrive['logicalDriveNumber']:
                    logicalDriveID = logicalDrive['driveID'].lower()
                    #faultTolerance = logicalDrive['faultTolerance']
                    break

            if logicalDriveID == "":
                logging.error("The server with iLO IP: " + host['iloIPAddr'] + " is missing required storage configuration.")
                raise Exception("The server with iLO IP: " + host['iloIPAddr'] + " is missing required storage configuration.")

            host['osDrive']['logicalDrive']['driveID'] = logicalDriveID

            # genksimage function still usage driveID inside osDrive to update kickstart
            # inorder, not to break the existing code, the below one is used
            # During refactoring, this should be removed
            host['osDrive']['driveID'] = logicalDriveID

            #host['osDrive']['logicalDrive']['faultTolerance'] = faultTolerance
        ####### End of block for USE_EXISTING #########################################

        # Before proceeding to other tasks, make sure, server is off
        iloClient.ensurePowerState("off")

    elif 'microSD' in host['osDrive']:
        logging.exception("Support for microSD as OS Drive is not available in this release")
        raise Exception("Support for microSD as OS Drive is not available in this release")


    return host


#############################################################################
def getILONetworkConnections_ex(iloIp, iloUser, iloPassword):
    logging.info("getILONetworkConnections_ex: iloIp: " + iloIp + " iloUser: " + iloUser + " iloPassword: " + iloPassword)

    iloClient = ILORedfish(iloIp, iloUser, iloPassword)
    #iloClient.login()

    return getILONetworkConnections(iloClient)

#############################################################################
def getILONetworkConnections(iloClient):
    logging.info("iloDeployment: getILONetworkConnections: " )

    #iloClient = ILORedfish(iloip,  ilouser, ilopassword)

    conns = []


    #iloClient.login()
    logging.debug("before.......")
    conns = iloClient.getILONWAdapters()

    logging.info("Network connections from iLO: ")
    logging.info(json.dumps(conns))

    output = []
    for conn in conns:
        logging.debug(conn)
        if conn['adapterType'] == "NIC":
            portnum = 0
            for port in conn['networkPorts']:
                portnum += 1
                output.append({"adapterId": conn['adapterId'], "portId": portnum, "portName": port["structuredName"],  "macAddress": port['macAddress'], "linkStatus": port['linkStatus']})

    return output


#############################################################################
def getILOStorageDrives_ex(iloIp, iloUser, iloPassword):

    iloClient = ILORedfish(iloIp, iloUser, iloPassword)

    return getILOStorageDrives(iloClient)

#############################################################################
def getILOStorageDrives(iloClient):
    logging.info("getILOStorageDrives: ")

    #iloClient = ILORedfish(iloip,  ilouser, ilopassword)

    drives = []


    #iloClient.login()
    drives = iloClient.getILOStorageDrives()

    logging.debug("Storage drives queried from iLO: ")
    logging.debug(json.dumps(drives))

    output = []
    # Look for only logical drives and omit physical drives from the list
    for drive in drives:
        logging.debug(drive)
        if drive['driveType'] == "Logical":
            #output.append(drive['driveName'] + " : " + drive['faultTolerance'] + " : " + drive['mediaType'] + " : " + str(drive['capacityGB']))
            output.append(drive)
#        else:
#            output.append(drive['location'] + " : " + drive['mediaType'] + " : " + str(drive['capacityGB']))

    return output
    #return drives



def getKSURL(ksfilepath):

    logging.info("ilodeployment: getKSURL: ksfilepath: " + ksfilepath)

    basehttpurl = config.WalkmanSettings().get("http_file_server_url")

    # This function assumes the file already present in the local
    # http www directory as specified by 'ISO_http_path'
    # just return the Web URL based on the file path

    return basehttpurl + os.path.basename(ksfilepath)

def getURLforOSPackage(OSPackage):

    logging.info("ilodeployment: getURLforOSPackage: OSPackage: " + OSPackage)

    basehttpurl = config.WalkmanSettings().get("http_file_server_url")
    ospackagedata = ospackages.getOSPackage(OSPackage)
    logging.debug(ospackagedata)

    if ospackagedata != {}:
        return basehttpurl +  ospackagedata['ISO_http_path']
    else:
        return ""


if __name__ == '__main__':
    print("sdsds")
