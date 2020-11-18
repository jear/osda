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
import time
import os
import logging
from time import sleep

from osda.iloredfish import ILORedfish

import osda.config as config
import osda.genksimg as genksimg
import osda.hostcheck as hostcheck
import osda.ospackages as ospackages
import osda.utils1 as utils1

defaultconfig = config.DefaultConfig()


##############################################################################
# Function to validate input json cnofiguration before running threads
# 
# The function checks if the iLO IP address is valid (or)
# if the server is in power Off state
# 
##############################################################################
def getValidationReport(servers):
    json_error_messages = []
    for host in servers:
        ilo_ip = host["iloIPAddr"]
        ilo_user = host["iloUser"]
        ilo_password = host["iloPassword"]
        try:
            ilo_client = ILORedfish(ilo_ip, ilo_user, ilo_password)
            if ilo_client.getPowerState().lower() == "off":
                continue
            error_message = "Found server iLO IP {iloIp} in ON state".format(iloIp=ilo_ip)
        except Exception as err:
            error_message = "Failed to connect iLO IP address {iloIp}".format(iloIp=ilo_ip)

        json_error_messages.append(error_message)

    return json_error_messages


def unDeploy(activities_config, task_id, deploy_data):
    try:
        logging.debug("unDeploy: taskID: " + str(task_id))
        logging.debug(deploy_data)
        if not deploy_data["hosts"]:
            raise Exception("Cannot proceed with deployment. Missing hosts information")
        servers = deploy_data["hosts"]

        threadfunction = unDeploy_th
        subtask_id = 0
        for host in servers:
            logging.debug("unDeploy: host: " + json.dumps(host))
            activities_config.setTaskStatus(task_id, "Running", "");
            activities_config.setSubTaskStatus(task_id, subtask_id, "Initiated", "", 1);
            deploy_bg = threading.Thread(target=threadfunction, args=(activities_config, task_id, subtask_id, host))
            deploy_bg.start()
            subtask_id = subtask_id + 1
    except Exception as err:
        logging.exception(err)
        raise Exception from err


# This is the thread function for undeploying one server
def unDeploy_th(activities_config, task_id, subtask_id, host):

    logging.info("unDeploy_th: {}".format(host))

    ilo_ip = host["iloIPAddr"]
    ilo_user = host["iloUser"]
    ilo_password = host["iloPassword"]

    logging.debug(host)

    try:
        ilo_client = ILORedfish(ilo_ip, ilo_user, ilo_password)

        # host_updated = replaceWithILOData(iloClient, host)
        # delete the Logical RAID
        # logging.debug("Updated host details {}".format(host_updated))

        # Power OFF the server
        ilo_client.ensurePowerState("off")

        activities_config.setSubTaskStatus(task_id, subtask_id, "In-Progress", "", 1)

        # Wait till the power state is OFF
        sleep_time = 5
        counter = 20
        while ilo_client.getPowerState().lower() != "off":
            logging.debug("unDeploy_th: Waiting 5 seconds for power OFF to complete")
            counter = counter - 1
            time.sleep(sleep_time)


        activities_config.setSubTaskStatus(task_id, subtask_id, "Complete", "Un-deployment completed successfully.", 10)


    except Exception as err:
        logging.exception(err)
        activities_config.setSubTaskStatus(task_id, subtask_id, "Error",
                                          "Failed to undeploy server due to errors. " + str(err), -1);
        return ({"result": "Failed to undeploy server due to errors", "error": err})


def deploy(activities_config, task_id, deploy_data):
    try:
        logging.debug("deploy: taskID: " + str(task_id))
        logging.debug(deploy_data)
        if not deploy_data["hosts"]:
            raise Exception("Missing hosts information")
        servers = deploy_data["hosts"]

        #error_failures = getValidationReport(servers)
        #if error_failures:
        #    logging.error("Error Failures : {}".format(len(error_failures)))
        #    message = "Cannot proceed the deployment: {}".format("; ".join(error_failures))
        #    activities_config.setTaskStatus(task_id, "Error", message)
        #    logging.error("Found issues with input configuration: {}".format(message))
        #    return ({"result": "Found issues with input configuration", "error": error_failures})

        activities_config.setTaskStatus(task_id, "Running", "");
        thread_function = deployOsByIlo
        subtask_id = 0
        for host in servers:
            logging.debug("deployByIlo: host: " + json.dumps(host))
            activities_config.setSubTaskStatus(task_id, subtask_id, "Initiated", "", 1);
            deploy_bg = threading.Thread(target=thread_function, args=(activities_config, task_id, subtask_id, host))
            deploy_bg.start()
            subtask_id = subtask_id + 1
    except Exception as err:
        logging.exception(err)
        raise Exception from err


# This is the thread function for deploying OS on one server
def deployOsByIlo(activities_config, task_id, subtask_id, host):
    ilo_ip = host["iloIPAddr"]
    ilo_user = host["iloUser"]
    ilo_password = host["iloPassword"]

    logging.debug(host)

    kickstart_file = ""

    try:
        package = ospackages.getOSPackage(host['osPackage'])
        ilo_client = ILORedfish(ilo_ip, ilo_user, ilo_password)

        # There is no point to proceed if server is powered ON
        #
        # Raise Exception
        if ilo_client.getPowerState().lower() != "off":
            errorMsg = "Found server {ip} in ON state. CANNOT PROCEED DEPLOYMENT OF {ip}".format(ip=ilo_ip)
            activities_config.setSubTaskStatus(task_id, subtask_id, "Error", errorMsg, -1)
            logging.exception("CRITICAL: " + errorMsg)
            raise Exception("CRITICAL: " + errorMsg)

        host_updated = replaceWithILOData(ilo_client, host)
        logging.debug("##########")
        logging.debug(host_updated)

    except Exception as err:
        logging.exception(err)
        activities_config.setSubTaskStatus(task_id, subtask_id, "Error", "Failed to deploy OS due to errors. " + str(err),
                                           -1);
        return ({"result": "Failed to deploy OS due to errors", "error": err})

    activities_config.setSubTaskStatus(task_id, subtask_id, "In-Progress", "", 1)
    logging.info("deployOsByIlo: Now change the boot-order")

    # Change the boot order to set the designated OS drive to top in the list
    try:
        ilo_client.modifyBootOrder(host_updated['osDrive'])
    except Exception as err:
        activities_config.setSubTaskStatus(task_id, subtask_id, "Error", "Failed to modify boot order. " + str(err), -1)
        logging.error("Failed to modify boot order: {}".format(err))
        return ({"result": "Failed to modify boot order", "error": err})

    activities_config.setSubTaskStatus(task_id, subtask_id, "In-Progress", "Boot order modified successfully.", 1)

    ## TEMP CODE remove before finalizing 
    # return

    try:
        logging.info("deployOsByIlo: Generate Kickstart")
        kickstart_file = genksimg.generateKickStart(package['osType'],
                                                    config.WalkmanSettings().get("local_http_root"), host_updated)
    except Exception as err:
        activities_config.setSubTaskStatus(task_id, subtask_id, "Error", "Failed to deploy OS due to errors. "
                                           + str(err), -1)
        logging.error("Failed to deploy OS due to errors: {}".format(err))
        return {"result": "Failed to deploy OS due to errors", "error": err}

    activities_config.setSubTaskStatus(task_id, subtask_id, "In-Progress", "Kickstart image created", 1)

    try:
        logging.info("deployOsByIlo: Mount USB Stick having kickstart")
        ilo_client.mountVirtualMedia(getKSURL(kickstart_file), "USBStick")
    except Exception as err:
        logging.error("Failed to mount the kickstart to iLO Virtual USB: {}".format(err))
        activities_config.setSubTaskStatus(task_id, subtask_id, "Error",
                                          "Failed to mount the kickstart to iLO Virtual USB. " + str(err), -1)
        return {"result": "Failed to mount the kickstart to iLO Virtual USB", "error": err}

    logging.debug("next mount ISO")
    activities_config.setSubTaskStatus(task_id, subtask_id, "In-Progress", "Kickstart image mounted", 1)

    try:
        logging.info("deployOsByIlo: Mount CD ROM")
        ilo_client.mountVirtualMedia(getURLforOSPackage(host_updated['osPackage']), "CD", bootOnNextServerReset=True)
    except Exception as err:
        logging.error("Failed to mount the ISO to iLO Virtual DVD: {}".format(err))
        activities_config.setSubTaskStatus(task_id, subtask_id, "Error",
                                          "Failed to mount the ISO to iLO Virtual DVD. " + str(err), -1)
        return {"result": "Failed to mount the ISO to iLO Virtual DVD", "error": err}

    activities_config.setSubTaskStatus(task_id, subtask_id, "In-Progress",
                                       "Kickstart image and ISO mounted successfully.", 1)

    try:
        # Validation to do reboot is already done
        # Hence, restting the server to boot the OS from mounted ISO
        logging.info("deployOsByIlo: Reset the machine to install OS")
        ilo_client.resetPowerState()
    except Exception as err:
        activities_config.setSubTaskStatus(task_id, subtask_id, "Error", "Server Reboot Failed", -1)
        logging.exception(err)
        return {"retult": "Failed to Reboot", "error": err}

    # In some cases, server reset fails to power on the server
    # Wait for 15 seconds, and power on in case if it fails to power ON
    sleep(15)
    ilo_client.ensurePowerState("on")

    activities_config.setSubTaskStatus(task_id, subtask_id, "In-Progress",
                                       "The OS installation with kickstart initiated.", 1)

    # Wait till the server is booted with installed OS
    # Attempt to connect to the server using the IP addr specified for first network
    host_ip_address = host_updated["networks"][0]["ipAddr"]
    # if hostcheck.isOpen(host_ip_address, package['osType']) == True:
    if hostcheck.isOpen(host_ip_address, package['osType']):
        logging.info(
            "Deployment completed successfully for TaskID {} subTaskID {} with IP Address {}".format(task_id,
                                                                                                     subtask_id,
                                                                                                     host_ip_address))
        activities_config.setSubTaskStatus(task_id, subtask_id, "Complete", "Deployment completed successfully.", 10)
    else:
        logging.error(
            "Deployment failed for TaskID {} subTaskID {} with IP Address {}".format(task_id, subtask_id, host_ip_address))
        activities_config.setSubTaskStatus(task_id, subtask_id, "Error",
                                           "Unable to confirm the completion of the deployment. Server not reachable. "
                                           , -1)

    # Cleanup here

    # Unmount media drives
    ilo_client.umountAllMediaDrives()

    # Delete kickstart file "kickstartFile"
    genksimg.cleanupKickstartFiles(kickstart_file)

    return activities_config.getTaskStatus(task_id)


##############################################################################
### This function queries and gets the hardware specific details like mac-address
### Logical Drive ID based on host data which only has generic identifier 
### For network interfaces, this function gets mac-address for interface that matches with portName in the host details
### For logical drivers, this function finds the driveID for the logical drive number in the host details
#############################################################################
def replaceWithILOData(ilo_client, host):
    logging.debug("replaceWithILOData: host: {}".format(host))

    if "networks" in host or "osDrive" in host:
        ilo_client.normalizeConfig()

    # Process inputs for networks
    if "networks" in host:
        network_ports = getILONetworkConnections(ilo_client)
        logging.debug(network_ports)

        ######################### Process FIRST network details if available ##################

        # portName = "HPE Ethernet 1Gb 4-port 331i Adapter - NIC - NIC.LOM.1.1/1"
        # In the above name, "NIC.LOM.1.1" is structured name of the adapter
        # /1 denotes the port number

        # Check if host['networks'][0] exists
        if len(host['networks']) >= 1:
            logging.debug("Processing second network details")
            mac_address = ""
            # Find MAC address for nic1
            for network_port in network_ports:
                logging.debug(network_port)
                if host['networks'][0]['nic1']['adapterId'] == network_port['adapterId']:
                    if host['networks'][0]['nic1']['portId'] == network_port['portId']:
                        mac_address = network_port['macAddress']
                        break

            if mac_address == "":
                logging.error("Cannot find the specfied network adapter/port for nic1")
                raise Exception("Cannot find the specfied network adapter/port for nic1")

            host['networks'][0]['nic1']['macAddress'] = mac_address

            # Find MAC address for nic2, if defined
            if host['networks'][0].get('nic2'):
                mac_address = ""
                for network_port in network_ports:
                    logging.debug(network_port)
                    if host['networks'][0]['nic2']['adapterId'] == network_port['adapterId']:
                        if host['networks'][0]['nic2']['portId'] == network_port['portId']:
                            mac_address = network_port['macAddress']
                            break
                host['networks'][0]['nic2']['macAddress'] = mac_address

            if mac_address == "":
                logging.error("Cannot find the specfied network adapter/port for nic2")
                raise Exception("Cannot find the specfied network adapter/port for nic2")

        ######################### Process SECOND network details if available ##################

        # Check if host['networks'][1] exists
        if len(host['networks']) >= 2 and len(host['networks'][1]) > 0:
            logging.debug("Processing second network details")

            mac_address = ""
            # Find MAC address for nic1
            for network_port in network_ports:
                logging.debug(network_port)
                if host['networks'][1]['nic1']['adapterId'] == network_port['adapterId']:
                    if host['networks'][1]['nic1']['portId'] == network_port['portId']:
                        mac_address = network_port['macAddress']
                        break

            if mac_address == "":
                logging.error("Cannot find the specfied network adapter/port for nic1")
                raise Exception("Cannot find the specfied network adapter/port for nic1")

            host['networks'][1]['nic1']['macAddress'] = mac_address

            # Find MAC address for nic2, if defined
            if host['networks'][1].get('nic2'):
                mac_address = ""
                for network_port in network_ports:
                    logging.debug(network_port)
                    if host['networks'][1]['nic2']['adapterId'] == network_port['adapterId']:
                        if host['networks'][1]['nic2']['portId'] == network_port['portId']:
                            mac_address = network_port['macAddress']
                            break
                host['networks'][1]['nic2']['macAddress'] = mac_address

            if mac_address == "":
                logging.error("Cannot find the specfied network adapter/port for nic2")
                raise Exception("Cannot find the specfied network adapter/port for nic2")

    ######################################################################################

    # Process inputs for OS drive
    if "osDrive" in host:
        os_logical_drive = host['osDrive'].get('logicalDrive')
        if not os_logical_drive:
            logging.error("Missing storage information, no details of logical drive information")
            raise Exception("Missing storage information, no details of logical drive information")

        # ILO redfish doesnt respond to physical drives
        # in case of unexpected shutdown
        #
        # Verify if it doesnt respond and power on if required
        # iloClient.normalizeConfig()

        ################# OS Drive data ########################################
        if 'logicalDrive' in host['osDrive']:
            os_logical_drive = host['osDrive'].get('logicalDrive')
            if 'operation' in os_logical_drive:
                operation = os_logical_drive.get('operation').upper()
            else:
                logging.exception("Missing the property operation in logicalDrive section of deploy JSON")
                raise Exception("Missing the property [operation] in logicalDrive section of deploy JSON")

        if operation == 'CREATE' or operation == 'DELETE_ALL_AND_CREATE':
            host = createLogicalDrive(host, os_logical_drive, ilo_client)
        elif operation == 'DELETE':
            host = deleteLogicalDrive(host, os_logical_drive, ilo_client)

        elif operation == 'USE_EXISTING':
            logical_drives = getILOStorageDrives(ilo_client)
            logging.info(logical_drives)

            logical_drive_id = ""
            # faultTolerance = ""
            for logicalDrive in logical_drives:
                if logicalDrive['logicalDriveNumber'] == os_logical_drive['logicalDriveNumber']:
                    logical_drive_id = logicalDrive['driveID'].lower()
                    # faultTolerance = logicalDrive['faultTolerance']
                    break

            if logical_drive_id == "":
                logging.error(
                    "The server with iLO IP: " + host['iloIPAddr'] + " is missing required storage configuration.")
                raise Exception(
                    "The server with iLO IP: " + host['iloIPAddr'] + " is missing required storage configuration.")

            host['osDrive']['logicalDrive']['driveID'] = logical_drive_id

            # genksimage function still usage driveID inside osDrive to update kickstart
            # inorder, not to break the existing code, the below one is used
            # During refactoring, this should be removed
            host['osDrive']['driveID'] = logical_drive_id

            # host['osDrive']['logicalDrive']['faultTolerance'] = faultTolerance
            ####### End of block for USE_EXISTING #########################################


        elif 'microSD' in host['osDrive']:
            logging.exception("Support for microSD as OS Drive is not available in this release")
            raise Exception("Support for microSD as OS Drive is not available in this release")

    # Before proceeding to other tasks, make sure, server is off
    ilo_client.ensurePowerState("off")
    sleep(2)

    logging.debug("replaceWithILOData: updated host: {}".format(host))
    return host


##################### LOGICAL DRIVE CREATION #####################
def createLogicalDrive(host, os_logical_drive, ilo_client):
    new_logical_drive = ilo_client.createLogicalDrive(os_logical_drive)
    host['osDrive']['logicalDrive']['logicalDriveNumber'] = new_logical_drive['logicalDriveNumber']
    host['osDrive']['logicalDrive']['driveID'] = new_logical_drive['driveID'].lower()
    # host['osDrive']['logicalDrive']['faultTolerance'] = "RAID 1"

    # genksimage function still usage driveID inside osDrive to update kickstart
    # Inorder, not to break the existing code, the below one is used
    # During refactoring, this should be removed
    host['osDrive']['driveID'] = new_logical_drive['driveID'].lower()

    logging.info("Using created logical RAID with drive number: {}".format(
        host['osDrive']['logicalDrive']['logicalDriveNumber']))
    return host


##################### LOGICAL DRIVE CREATION #####################
def deleteLogicalDrive(host, os_logical_drive, ilo_client):
    logging.debug("deleteLogicalDrive: osLogicalDrive: {}".format(os_logical_drive))

    logical_drives = getILOStorageDrives(ilo_client)
    logging.info(logical_drives)

    logical_drive_id = ""
    for logicalDrive in logical_drives:
        logging.debug("deleteLogicalDrive: logicalDrive: {}".format(logicalDrive))
        if 'logicalDriveNumber' in os_logical_drive:
            if logicalDrive['logicalDriveNumber'] == os_logical_drive['logicalDriveNumber']:
                logical_drive_id = logicalDrive['driveID']
                break
        elif utils1.stringMatch(os_logical_drive['raidLevel'], logicalDrive['faultTolerance']):
            if utils1.matchGB_GiB(logicalDrive['capacityGB'], os_logical_drive['capacity']):
                logical_drive_id = logicalDrive['driveID']
                break

    if logical_drive_id == "":
        logging.error("The server with iLO IP: " + host['iloIPAddr'] + " is missing required storage configuration.")
        return

    host['osDrive']['logicalDrive']['driveID'] = logical_drive_id
    logging.debug("deleteLogicalDrive: deleting logical drive with logicalDriveID: ", logical_drive_id)

    result = ilo_client.deleteLogicalDrive(logical_drive_id)

    return host


'''
# Compares 2 values which are either in units of GB or GiB
def matchGB_GiB(val1, val2):

    # When both input values are in same units
    if int(val1) == int(val2):
        return true

    # If va11 is in GB and val2 is in GiB
    if int(val1) == int(val2 * 1024 * 1024 * 1024 / 1000 / 1000 / 1000 ):
        return true

    # If va12 is in GB and val1 is in GiB
    if int(val2) == int(val1 * 1024 * 1024 * 1024 / 1000 / 1000 / 1000 ):
        return true

    # When no match found 
    return false


def stringMatch(str1, str2):

    if str1.lower().replace(" ", "") == str2.lower().replace(" ", ""):
        return true
    else
        return false
'''


#############################################################################
def getILONetworkConnections_ex(ilo_ip, ilo_user, ilo_password):
    try:
        logging.info(
        "getILONetworkConnections_ex: iloIp: " + ilo_ip + " iloUser: " + ilo_user + " iloPassword: " + ilo_password)
        ilo_client = ILORedfish(ilo_ip, ilo_user, ilo_password)
        return getILONetworkConnections(ilo_client)
    except Exception as err:
        if type(err).__name__ == 'InvalidCredentialsError':
            logging.error('Failed to log in to iLO. Check your username/password.')
        raise err


#############################################################################
def getILONetworkConnections(ilo_client):
    logging.info("iloDeployment: getILONetworkConnections: ")

    conns = []

    logging.debug("before.......")
    conns = ilo_client.getILONWAdapters()

    logging.info("Network connections from iLO: ")
    logging.info(json.dumps(conns))

    output = []
    for conn in conns:
        logging.debug(conn)
        if conn['adapterType'] == "NIC":
            # adapter = conn['structuredName']
            adapter = conn['adapterName'] + " - " + conn['structuredName']
            portnum = 0
            for port in conn['networkPorts']:
                portnum += 1
                #                if port['status'] == "OK":
                output.append(
                    {"adapterId": conn['adapterId'], "portId": portnum, "portName": adapter + "/" + str(portnum),
                     "macAddress": port['macAddress'], "linkStatus": port['linkStatus']})
                # output.append(adapter + " : " + port['macAddress'])

    return output


#############################################################################
def getILOStorageDrives_ex(ilo_ip, ilo_user, ilo_password):
    try:
        ilo_client = ILORedfish(ilo_ip, ilo_user, ilo_password)

        return getILOStorageDrives(ilo_client)
    except Exception as err:
        if type(err).__name__ == 'InvalidCredentialsError':
            logging.error('Failed to log in to iLO. Check your username/password.')
        raise err
#############################################################################
def getILOStorageDrives(iloClient):
    logging.info("getILOStorageDrives: ")

    drives = []

    # iloClient.login()
    drives = iloClient.getILOStorageDrives()

    logging.debug("Storage drives queried from iLO: ")
    logging.debug(json.dumps(drives))

    output = []
    # Look for only logical drives and omit physical drives from the list
    for drive in drives:
        logging.debug(drive)
        if drive['driveType'] == "Logical":
            output.append(drive)

    return output


def getKSURL(ksfilepath):
    logging.info("ilodeployment: getKSURL: ksfilepath: " + ksfilepath)

    basehttpurl = config.WalkmanSettings().get("http_file_server_url")

    # This function assumes the file already present in the local
    # http www directory as specified by 'ISO_http_path'
    # just return the Web URL based on the file path

    return basehttpurl + os.path.basename(ksfilepath)


def getURLforOSPackage(os_package):
    logging.info("ilodeployment: getURLforOSPackage: OSPackage: " + os_package)

    basehttpurl = config.WalkmanSettings().get("http_file_server_url")
    ospackagedata = ospackages.getOSPackage(os_package)
    logging.debug(ospackagedata)

    if ospackagedata != {}:
        return basehttpurl + ospackagedata['ISO_http_path']
    else:
        return ""


if __name__ == '__main__':
    print("ilodeployment main function!")
