# -*- coding: utf-8 -*-
###
# (C) Copyright (2012-2017) Hewlett Packard Enterprise Development LP
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

from pprint import pprint
from hpeOneView.oneview_client import OneViewClient
from hpeOneView.exceptions import HPEOneViewException
#from hpOneView.oneview_client import OneViewClient
#from hpOneView.exceptions import HPOneViewException

import json
import threading
import random
import socket
import logging

import os
import uuid
import re
import time
import datetime

import osda.config as config
import osda.ospackages as ospackages
import osda.genksimg  as genksimg
import osda.hostcheck as hostcheck

from osda.ilo_client import  iLoClient

TEMP_DIR='/opt/hpe/osda/data/scratch/'

# You can use username/password or sessionID for authentication.
# Be sure to inform a valid and active sessionID.
osActivitiesConfig = config.Activities()

walkman_settings = {}
ksfiles_settings = {}
#ospackages_settings = []
ov_appliances = []


def init():
    try:
        logging.debug("synergydeployment:init: ")

        fin = open('/opt/hpe/osda/data/config/ovappliances.json', 'r')
        global ov_appliances
        ov_appliances = json.load(fin)
        fin.close()

        fin = open('/opt/hpe/osda/data/config/ksfiles.json', 'r')
        global ksfiles_settings
        ksfiles_settings = json.load(fin)
        #print(ksfiles_settings)
        fin.close()
    except Exception as err:
            logging.exception(err)
            raise Exception from err

def getURLforOSPackage(OSPackage):
    try:
        basehttpurl = config.WalkmanSettings().get("http_file_server_url")

        ospackagedata = ospackages.getOSPackage(OSPackage)

        if ospackagedata != {}:
            return basehttpurl + ospackagedata['ISO_http_path']
        else:
            return ""
    except Exception as err:
            logging.exception(err)
            raise Exception from err

def getKSURL(ksfilepath):
    try:
        basehttpurl = config.WalkmanSettings().get("http_file_server_url")

        # This function assumes the file already present in the local
        # http www directory as specified by 'ISO_http_path'
        # just return the Web URL based on the file path

        return basehttpurl + os.path.basename(ksfilepath)
    except Exception as err:
            logging.exception(err)
            raise Exception from err

def getBaseKSFilePath(osPackage):
    try:
        osPackageData = ospackages.getOSPackage(osPackage)
        osType = osPackageData['osType']

        global ksfiles_settings

        kspath = ""
        for ksdata in ksfiles_settings:
            if ksdata['osType'] == osType:
                kspath = ksdata['basekspath']
                break

        return kspath
    except Exception as err:
            logging.exception(err)
            raise Exception from err

# Returns the number of OV appliances added to OSDA
def getOVCount():
    return len(ov_appliances)


def deploy(taskID, deployData):
    try:
        logging.debug("deploy: taskID: " + str(taskID))
        logging.debug(json.dumps(deployData))
        if not deployData["hosts"]:
            raise Exception("Missing hosts information")
        createServerProfile = deployData.get('createServerProfile')
        logging.debug(createServerProfile)
        logging.debug(type(createServerProfile))
        
        # Default value is True
        if createServerProfile == None:
            createServerProfile = True


        hosts = deployData['hosts']
        hostsCount = len(hosts)

        logging.info("deploy: required hosts: " + str(hostsCount))

        threadfunction = deployByOneView_Th
        subtaskID = 0
        if createServerProfile == True:
            OVName = deployData['oneviewDetails']['ovName']
            ovconfig = getOVConfig(OVName)
            oneview_client = oneviewConnect(ovconfig)
            OVSPTName = deployData['oneviewDetails'].get('ovSPT')
            serversList = getServerHardwaresForSPT(oneview_client, OVSPTName)
            serversCount = len(serversList)

            logging.info("deploy: available  hosts: " + str(serversCount))

            if serversCount < hostsCount: 
                logging.exception("deploy: cannot proceed as sufficient number of servers not available")
                errMsg = "Cannot proceed with deployment due to insufficient server hardware to support the deployment. Required: " + str(hostsCount) + " Available: " + str(serversCount)
                osActivitiesConfig.setTaskStatus(taskID, "Error", errMsg);
                return
            else:
                logging.info("deploy: sufficient servers available for deployment")
                osActivitiesConfig.setTaskStatus(taskID, "Initiated", "");

                for host in hosts:
                    logging.debug("deploy: host: " + json.dumps(host))
                    serverHW = serversList[subtaskID] if createServerProfile == True else None
                    osActivitiesConfig.setTaskStatus(taskID, "Running", "");
                    #osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "Initiated", "");
                    osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "Initiated", "", 1);
                    deploy_bg = threading.Thread(target=threadfunction, args=(taskID, subtaskID, deployData, createServerProfile, serverHW))
                    deploy_bg.start()
                    subtaskID = subtaskID + 1
        elif createServerProfile == False:
            logging.info("deploy: Deploying using user specified names from existing server profiles")
            osActivitiesConfig.setTaskStatus(taskID, "Initiated", "");

            for host in hosts:
                logging.debug("deploy: host: " + json.dumps(host))
                osActivitiesConfig.setTaskStatus(taskID, "Running", "");
                #osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "Initiated", "");
                osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "Initiated", "", 1);
                deploy_bg = threading.Thread(target=threadfunction, args=(taskID, subtaskID, deployData, createServerProfile, None))
                deploy_bg.start()
                subtaskID = subtaskID + 1

    except Exception as err:
            logging.exception(err)
            raise Exception from err


# Thread function for deployment using OneView 
def deployByOneView_Th(taskID, subtaskID, deployData, createServerProfile, serverHW):

    logging.debug("deployByOneView_Th: taskID: " + str(taskID) + " subtaskID: " + str(subtaskID))
    #print(deployData)
    
    osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "", 1)

    OVName = deployData['oneviewDetails']['ovName']
    # SPT is optional if createServerProfile set to False
    OVSPTName = deployData['oneviewDetails'].get('ovSPT')
    host = deployData['hosts'][subtaskID]
    OVServerProfileName = host['serverProfile']
    OSPackage = host['osPackage']

    logging.debug("deployByOneView_Th: OSConfigJSON: ")
    logging.debug(json.dumps(host))

    ovconfig = getOVConfig(OVName)

    try:
        retSP = deployWithOV(taskID, subtaskID, ovconfig, OVServerProfileName, serverHW, OVSPTName, OSPackage, host, createServerProfile)
    except Exception as e:
        osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", "Failed to delpoy the host due to errors. " + str(e), -1)
        logging.exception("Failed to deploy the host due to errors. " + str(e))

    return taskID

# Register new OneView instance and store OneView details along with credentials
# in ovappliances.json. Any future interaction with OneView looks up ovappliances.json for 
# connection details
# the input should have the following details included
# Name: - user specified name for OneView instance. Should be unique
# IP/FQDN: - IP or FQDN for OneView
# Username: - Username that this appliance should use for interacting with OneView
# Password(optional): - password if specified will be stored in plain text
#
# This function should connect to OV using the input details and save the OV certs
# Add new entry into ovappliances.json after successful connection with OV
def registerOV(ovdetails):
    logging.info("registerOV: start: adding oneview instance with alias: " )
    logging.info(ovdetails['alias'])
    global ov_appliances

    for item in ov_appliances:
        logging.debug(item)
        if item['alias'] == ovdetails['alias']:
           logging.exception(" Exit with error as another oneview exists with same alias ")
           raise Exception( "Another oneview exists with same alias")

    ov_cert_path = genOVCert(ovdetails)
    ovdetails['ov_cert_path'] = ov_cert_path
    ov_appliances.append(ovdetails)

    fout = open('/opt/hpe/osda/data/config/ovappliances.json', 'w')
    json.dump(ov_appliances, fout, indent=2)
    #json.dump(ovdetails, fout)
    fout.close()
    
    logging.debug("ov_appliances")
    logging.debug(ov_appliances)
    return ovdetails

def genOVCert(ovdetails):

    global walkman_settings
    cert_dir = config.WalkmanSettings().get("ov_certs_path")


    oneview_config = {
                        "ip": "",
                        "api_version": 1200,
                        "ssl_certificate": "",
                        "credentials": {},
                     }

    oneview_creds = {
                        "userName": "",
                        "authLoginDomain": "",
                        "password": "",
                        "sessionID": ""
                    }


    oneview_config['ip'] = ovdetails['ipaddr']
    oneview_creds['userName'] = ovdetails['username']
    oneview_creds['password'] = ovdetails['password']
    oneview_config['credentials'] = oneview_creds

    cert_path = os.path.join(cert_dir, ovdetails['alias'] + ".crt")
    logging.info("cert_path")
    logging.info(cert_path)
    #oneview_config['ssl_certificate'] = cert_path

    try:
        oneview_client = OneViewClient(oneview_config)
    except HPEOneViewException as e:
        # Sometimes the exception message has stacktrace. So if msg length too long then truncate at first occurance or '.'
        if len(e.msg) > 80:
            logging.exception(e.msg.split('.', 1)[0] + '.')
            raise Exception(e.msg.split('.', 1)[0] + '.')
        else:
            logging.exception(e.msg)
            raise Exception(e.msg)

    # Need better code here to handle errors in cert import from OV
    cmd = "openssl s_client -showcerts -host " + ovdetails['ipaddr'] + " -port 443 2>/dev/null </dev/null | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > " + cert_path

    os.system(cmd)
    return cert_path

def getRegisteredOVs():

    global ov_appliances
    return ov_appliances

def oneviewConnect(ovconfig):
    try:
        return OneViewClient(ovconfig)
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def getOVAppliance(ovalias):
    global ov_appliances

    for ovdetails in ov_appliances:
        logging.debug(ovdetails)
        if ovdetails['alias'] == ovalias:
            logging.debug("OV Config is: ")
            return ovdetails

def deleteOVAppliance(ovalias):
    '''
    Delete OV appliance in ov_appliances by alias
    Remove cert referenced by ov_cert_path
    '''
    logging.debug('deleteOVAppliance')
    logging.debug(f'Alias: {ovalias}')
    global ov_appliances
    try:
        index = None
        for i, entry in enumerate(ov_appliances):
            logging.debug(f'OV entry: {entry}')
            if entry['alias'] == ovalias:
                index = i
                break
        if index == None:
            logging.error(f'{ovalias} not found')
            raise Exception(f'OV alias {ovalias} not found in OV appliances list')
        else:
            certPath = ov_appliances[index]['ov_cert_path']
            logging.debug(f'Delete {certPath}')
            os.remove(certPath)
            logging.debug(f'Delete OV appliance alias {ovalias}')
            del ov_appliances[index]
            index = None
            ovConfigJson = '/opt/hpe/osda/data/config/ovappliances.json'
            with open(ovConfigJson, 'w') as f:
                f.write(json.dumps(ov_appliances,indent=2))
            return 'Success'
    except Exception as err:
        raise Exception(str(err))

def getOVConfig(ovalias):
    try:
        global ov_appliances

        for ovdetails in ov_appliances:
            logging.debug(ovdetails)
            if ovdetails['alias'] == ovalias:
                logging.info("OV Config is: ")
                logging.info(ovdetails)

                oneview_config = {
                            "ip": ovdetails['ipaddr'],
                            "api_version": 1200,
                            "ssl_certificate": ovdetails['ov_cert_path'],
                            "credentials": {
                                "userName": ovdetails['username'],
                                "authLoginDomain": "",
                                "password": ovdetails['password'],
                                "sessionID": ""
                                }
                            }

                logging.debug("oneview_config:   ")
                logging.debug(oneview_config)
                return oneview_config

        return {}
    except Exception as err:
            logging.exception(err)
            raise Exception from err

def getSPTs(ovalias):
    try:
        logging.debug("ovalias: " + ovalias)

        ovconfig = getOVConfig(ovalias)
        oneview_client = oneviewConnect(ovconfig)

        logging.info("\nGet list of all server profile templates")
        all_templates = oneview_client.server_profile_templates.get_all()
        spts = []
        for template in all_templates:
            logging.debug('  %s' % template['name'])
            spts.append(template['name'])

        return spts
    except Exception as err:
            logging.exception(err)
            raise Exception from err

#############################################################################
#############################################################################
def getOVSPTNetworkConnections(ovname, sptname):
    try:
        logging.info("getOVSPTNetworkConnections: sptname: " + sptname)
        logging.info("getOVSPTNetworkConnections: ovname: " + ovname)
        conns = []

        ovconfig = getOVConfig(ovname)
        oneview_client = oneviewConnect(ovconfig)

        # Get the server profile templat by name
        sptemplate = oneview_client.server_profile_templates.get_by_name(sptname)
        sptdata = sptemplate.data
        logging.debug(str(sptdata))
        logging.debug(json.dumps(sptdata))
        logging.debug(sptdata['connectionSettings'])

        if(sptdata['connectionSettings']['manageConnections']):
            logging.debug(sptdata['connectionSettings']['connections'])
            logging.debug("##########################################")
            for connection in sptdata['connectionSettings']['connections']:
                #print(connection)

                if(connection['functionType'] != "Ethernet"): break

                #print("network: " + str(json.dumps(network)))
                conn = { "connectionName": connection['name'], "portId": connection['portId']}
                conns.append(conn)

        logging.debug(conns)
        return conns
    except Exception as err:
                logging.exception(err)
                raise Exception from err


#############################################################################
#############################################################################
def getOVSPTStorageDrives(ovname, sptname):
    try:
        logging.info("getOVSPTStorageDrives: sptname: " + sptname)
        logging.info("getOVSPTStorageDrives: ovname: " + ovname)
        #drives = ["Local drive"]
        drives = []

        ovconfig = getOVConfig(ovname)
        oneview_client = oneviewConnect(ovconfig)

        # Get the server profile templat by name
        sptemplate = oneview_client.server_profile_templates.get_by_name(sptname)
        sptdata = sptemplate.data
        logging.debug(str(sptdata))
        logging.debug(json.dumps(sptdata))
        logging.debug(json.dumps(sptdata['localStorage']))


        # Look only for logical drives as OS installation is supported by this tool only on Logical drives
        logging.debug("##########################################")
        for controller in sptdata['localStorage']['controllers']:
            logging.debug(json.dumps(controller))
            for logicaldrive in controller['logicalDrives'] or []:
                logging.debug(json.dumps(logicaldrive))
                #data = logicaldrive['name'] + " --> " + ( logicaldrive['raidLevel'] or "Unknown RAID level" ) + " --> " + ( logicaldrive['driveTechnology'] or "Unspecified Drive Type")
                data = logicaldrive
                drives.append(data)


    #    for drive in sptdata['localStorage']['sasLogicalJBODs']:
    #        print("############")
    #        print(drive)
    #        data = drive['deviceSlot'] + " --> " + drive['driveTechnology'] + " --> " + str(drive['driveMaxSizeGB'])
    #        drives.append(data)

        logging.debug(drives)
        return drives
    except Exception as err:
        logging.exception(err)
        raise Exception from err

#############################################################################
#############################################################################
def getServerHardwaresForSPT(oneview_client, OVSPTName):
    try:
        # Get by name
        logging.info("\nGet a server profile templates by name")
        sptemplate = oneview_client.server_profile_templates.get_by_name(OVSPTName)
        template = sptemplate.data
        logging.debug(template)
        logging.debug("##############################################")

        enclosureGroupURI = template['enclosureGroupUri']
        serverHardwareTypeUri = template['serverHardwareTypeUri']

        # Get Server Hardware which matches specified server hardware type and
        # has no server profile assigned to it

        serversList = []
        
        # Get list of all server hardware resources that match serverHardwareType of the SPT
        # Omit server hardwares which are not healthy (status not equal to OK)
        logging.info("Get list of all server hardware resources")
        server_hardware_all = oneview_client.server_hardware.get_by('serverHardwareTypeUri', serverHardwareTypeUri)
        for serv in server_hardware_all:
            if serv['serverHardwareTypeUri'] == serverHardwareTypeUri:
                if serv['serverProfileUri'] == None and serv['status'] == 'OK' and serv['powerState'] == 'Off':
                    logging.debug('  %s' % serv['name'])
                    logging.debug('  %s' % serv['state'])
                    logging.debug('  %s' % serv['uri'])
                    serversList.append(serv)

        return serversList
    except Exception as err:
                logging.exception(err)
                raise Exception from err
###################################################################




#############################################################################
#############################################################################
def createSP(ovClient, ovServerHardware, ovServerProfileName, ovSPTName):

    # Create Server Profile from SPT
    try:
        # Create a server profile
        logging.info("\nCreate a basic connection-less assigned server profile")
        # Create unassigned instance of server profile from SPT
        sptemplate = ovClient.server_profile_templates.get_by_name(ovSPTName)
        profile = sptemplate.get_new_profile()
        logging.debug("get_new_profile: " )
        logging.debug(json.dumps(profile))
        logging.debug(json.dumps(ovServerHardware))

        # Assign the server hardware to the server profile instance
        profile['serverHardwareUri'] = ovServerHardware['uri']
        profile['name'] = ovServerProfileName

        logging.debug("get_new_profile: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX " )
        logging.debug(json.dumps(profile))

        serverprofile_data  = ovClient.server_profiles.create(profile)
        serverprofile  = serverprofile_data.data
        profile_uri = serverprofile ["uri"]
        logging.debug(serverprofile )
        return serverprofile 
    except HPEOneViewException as e:
        logging.exception("createSP: error: " + e.msg)
        return {'errorMsg': e.msg}



#############################################################################
#############################################################################
def getSP(ovClient, ovServerProfileName):
    # Retrive a Server Profile from SPName
    try:
        # retrive a server profile
        logging.info("\nRetriving a server profile: " + ovServerProfileName)
        # Create unassigned instance of server profile from SPT
        serverprofiledata = ovClient.server_profiles.get_by_name(ovServerProfileName)
        serverprofile = serverprofiledata.data
        return serverprofile
    except HPEOneViewException as e:
        logging.exception("getSP: error: " + e.msg)
        return {'errorMsg': e.msg}




#############################################################################
#############################################################################
def deployWithOV(taskID, subtaskID, OVConfig, OVServerProfileName, OVServerHW, OVSPTName, OSPackage, OSConfigJSON, createServerProfile):

    # Find servers not assigned with server profile
    # and matching with server hardware type of SPT
    # and in healthy state
    # If the server is powered ON then power it OFF
    osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "Creating the server profile", 1)
    logging.info("Creating the server profile")
    # TODO: First validate the input values

    oneview_client = oneviewConnect(OVConfig)

    retServerProfile = {}
    logging.debug(json.dumps(OVServerHW))

    #return;
    if createServerProfile == True:
       # Creating a Server Profile.
       #sptemplate = oneview_client.server_profile_templates.get_by_name(OVSPTName)
       #spt = sptemplate.data
       #sptURI = spt['uri']
       logging.debug("Server Profile Template URI: " + OVSPTName)
       retServerProfile = createSP(oneview_client, OVServerHW, OVServerProfileName, OVSPTName)
    else:
       # Retrieving a Server Profile.
       retServerProfile = getSP(oneview_client, OVServerProfileName)

    logging.debug(json.dumps(retServerProfile))
    if 'errorMsg' in retServerProfile:
        osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", "Failed to create/retrive server profile '" + OVServerProfileName + "' due to errors. " + retServerProfile['errorMsg'], -1)
        logging.exception(retServerProfile['errorMsg'])
        raise Exception(retServerProfile['errorMsg'])
    else:
        osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "Created the server profile: " + OVServerProfileName, 1)
        logging.info("Created the server profile: " + str(OVServerProfileName))

    # If server profile is successfully created then install OS
    # Valid server profile 
    logging.info('Server Profile created successfully.....')
    logging.debug(retServerProfile.get('name'))
    OSConfigJSON_updated = replaceWithSPData(oneview_client, OSConfigJSON, retServerProfile)

    ret = installOS(taskID, subtaskID, oneview_client, retServerProfile.get('serverHardwareUri'), OSPackage, OSConfigJSON_updated)
    if ret == 0:
        osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "OS deployment initiated", 1)


#############################################################################
# Get the MAC address based on portID of the server
#############################################################################
def replaceWithSPData(ovClient, OSConfigJSON, retServerProfile):
    try:
        logging.debug("replaceWithSPData: OSConfigJSON: " + str(OSConfigJSON))

        # Get the management nics MAC address extracted from SP data
        if "connectionSettings" in retServerProfile:
            if "connections" in retServerProfile['connectionSettings']:
                for connection in retServerProfile['connectionSettings']['connections']:
                    logging.debug(connection)
                    if connection['name'] == OSConfigJSON['networks'][0]['nic1']['connectionName']:
                        OSConfigJSON['networks'][0]['nic1']['macAddress'] =  connection['mac']
                        continue

                    if OSConfigJSON['networks'][0].get('nic2') and connection['name'] == OSConfigJSON['networks'][0]['nic2']['connectionName']:
                        OSConfigJSON['networks'][0]['nic2']['macAddress'] =  connection['mac']
                        continue

                    if len(OSConfigJSON['networks']) > 1:
                        if OSConfigJSON['networks'][1].get('nic1') and connection['name'] == OSConfigJSON['networks'][1]['nic1']['connectionName']:
                            OSConfigJSON['networks'][1]['nic1']['macAddress'] =  connection['mac']
                            continue

                        if OSConfigJSON['networks'][1].get('nic2') and connection['name'] == OSConfigJSON['networks'][1]['nic2']['connectionName']:
                            OSConfigJSON['networks'][1]['nic2']['macAddress'] =  connection['mac']
                            continue

        if 'osDrive' not in OSConfigJSON:
            OSConfigJSON['osDrive'] = {"driveID": ""}
            return OSConfigJSON

        logging.debug(OSConfigJSON['osDrive'])

        if 'driveName' not in OSConfigJSON['osDrive']:
            OSConfigJSON['osDrive'] = {"driveID": ""}
            return OSConfigJSON

        if OSConfigJSON['osDrive']['driveName'] == '':
            OSConfigJSON['osDrive'] = {"driveID": ""}
            return OSConfigJSON

        # Get the VolumeUniqueIdentifier for the input logical drive and update the deploy data with it

        # Get the VolumeUniqueIdentifier for the input logical drive and update the deploy data with it
        logicalDriveNumber = ""
        if "localStorage" in retServerProfile:
            if "controllers" in retServerProfile['localStorage']:
                for controller in retServerProfile['localStorage']['controllers']:
                    logging.debug(controller)
                    if "logicalDrives" in controller:
                        logging.info("Found controller with logicalDrives")
                        for logicaldrive in controller['logicalDrives']:
                            #print(logicaldrive)
                            if logicaldrive['name'] == OSConfigJSON['osDrive']['driveName']:
                                logging.info("Found matching drive")
                                logicalDriveNumber = logicaldrive['driveNumber']
                                break

        # Now get the drive ID
        serverHardwareUri = retServerProfile.get('serverHardwareUri')

        ilo_client = iLoClient(ovClient)

        logicalDriveName = ilo_client.get_logical_drive_VolumeUniqueIdentifier(serverHardwareUri, logicalDriveNumber)
        logging.debug("logicalDriveNumber")
        logging.debug(logicalDriveName)
        if not logicalDriveName:
            logging.exception("Failed to obtain OS drive infromation from iLO")
            raise Exception("Failed to obtain OS drive infromation from iLO")


        OSConfigJSON['osDrive']["driveID"] = logicalDriveName.lower()


    #    iloRedfish = ILORedfish()
    #    
    #    #iloRedfish.login_sso(ilo_sso_url['iloSsoUrl'])
    #    iloRedfish.login_sso(ilo_sso_url['iloSsoUrl'], ilosession)
    #    iloRedfish.get_logical_drive_by_number(OSConfigJSON['osDrive']['driveNumber'])
    #    print("##############Server########")
    #    print(json.dumps(server))

        logging.debug("@@@@@@@@@@replaceWithSPData@@@@@@@@@@")
        logging.debug(json.dumps(OSConfigJSON))

        return OSConfigJSON
    except Exception as err:
            logging.exception(err)
            raise Exception from err

# This function installs ESXi 
def installOS(taskID, subtaskID, ovClient, srvHardwareUri, osPackage, osConfigJSON):
    logging.info("installOS: start : srvHardwareUri", srvHardwareUri)

     # Find out the NIC for assigning the IP address from OSConfigJSON->MGMTNIC
    #logging.info("The user speficied Ethernet Port is: " + str(osConfigJSON['mgmtNIC']))


    try:
        # initialize iLO client with OneView connection
        iloclient = iLoClient(ovClient)
        logging.info("installOS: after iLoClient ")

        #Eject VirtualMedia if alredy Inserted
        iLoClient.vmedia_eject(iloclient, srvHardwareUri)

        # Generate modified ISO for Kickstart installation

        # Get http url for ISO to mount to virtual media
        isourl = getURLforOSPackage(osPackage)

        # update iLO Virtual Media settings with URL for ISO 
        logging.info("ISO URL to mount: " + isourl)
        iLoClient.mount_vmedia_iLO(iloclient, srvHardwareUri, isourl, True)
    except Exception as err:
        errorMsg = "Failed to mount the ISO to iLO Virtual DVD. {}".format(str(err))
        osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", errorMsg, -1 );
        logging.error(errorMsg)
        raise Exception(errorMsg)

    osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "ISO mounted successfully.", 1);
    logging.info("ISO mounted successfully.")

    # Generate Kickstart config file based on OSConfigJSON
    global walkman_settings
    targetdir = config.WalkmanSettings().get("local_http_root")
    ospackagedata = ospackages.getOSPackage(osPackage)
    ksimgpath = genksimg.generateKickStart(ospackagedata['osType'], targetdir, osConfigJSON)

    ksimgurl =  getKSURL(ksimgpath)
    logging.info("Kickstart URL to mount: " + ksimgurl)

    try:
        # mount IMG containing the ks.cfg as virtual USB 
        iLoClient.mount_vusb(iloclient, srvHardwareUri, ksimgurl)
    except Exception as err:
        errorMsg = "Failed to mount the kickstart to iLO Virtual USB. {}".format(str(err))
        osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "Error", errorMsg, -1 );
        logging.error(errorMsg)
        raise Exception(errorMsg)

    osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "Kickstart image and ISO mounted successfully.", 1);
    logging.info("Kickstart image and ISO mounted successfully.")

    # Sleep for 5 secs to ensure the mount operation are completed
    time.sleep(5)
    rebootByOV(ovClient, srvHardwareUri)

    osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "In-Progress", "Server rebooted to initiate OS installation using kickstart.", 1);
    logging.info("Server rebooted to initiate OS installation using kickstart.")

    if hostcheck.isOpen(osConfigJSON['networks'][0]["ipAddr"], ospackagedata['osType']) == True:
        osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "Complete", "Deployment completed successfully.", 10);
        logging.info("Deployment completed successfully.")
    else:
        osActivitiesConfig.setSubTaskStatus(taskID, subtaskID, "Fail", "Unable to confirm the completion of the deployment. Server not reachable. ", -1);
        logging.warn("Unable to confirm the completion of the deployment. Server not reachable. ")

    # Clean up
    # Unmount media drives
    iLoClient.umount_drives(iloclient, srvHardwareUri)
    
    # Delete kickstart file
    genksimg.cleanupKickstartFiles(ksimgpath)
    

def rebootByOV(ovClient, srvHardwareUri):

    # Reboot the server to allow it to boot into ISO for kickstart installation
    try:
        configuration = {
            "powerState": "On",
            "powerControl": "MomentaryPress"
        }
        server = ovClient.server_hardware.get_by_uri(srvHardwareUri)
        server_power = server.update_power_state(configuration)
        logging.info("Successfully changed the power state of server '{name}' to '{powerState}'".format(**server_power))
    except HPEOneViewException as e:
        logging.exception(e.msg)
        logging.info("Attempting second time to change the power state")
        time.sleep(10)
        server = ovClient.server_hardware.get_by_uri(srvHardwareUri)
        server_power = server.update_power_state(configuration)



# TODO: This function needs more work
def deployWithOVServerProfile(OVConfig, OVServerProfileName, OSPackage, OSConfigJSON):
    try:
        oneview_client = oneviewConnect(OVConfig)
        profile_data = oneview_client.server_profiles.get_by_name(OVServerProfileName)
        profile = profile_data.data
        logging.debug(profile['serverHardwareUri'] )
        installOS(oneview_client, profile['serverHardwareUri'], OVServerProfileName,  OSPackage, OSConfigJSON)
    except Exception as err:
        logging.exception(err)
        raise Exception from err


if __name__ == '__main__':

    print("main")
 #   ilocreds = {"user": "v241usradmin", "password": "HP!nvent123"}
  #  getILONetworkConnections("10.188.1.184", ilocreds )

  #  init("10.188.210.14")

    #taskID = createTask(3)
   # print("########################################")
    #print(TasksTable)
    #print("########################################")
    #setTaskStatus(taskID, 0, "Completed")

    init("10.188.210.14")

    ovconfig = getOVConfig("syn0210")
    oneview_client = oneviewConnect(ovconfig)
    spdata_data = oneview_client.server_profiles.get_by_name("sp21")
    spdata = spdata_data.data

    OSConfigJSON = json.loads('{"mgmtNIC": {"connectionName": "vmnic0"}, "osDrive": {"driveName": "localosdrive"}, "networkName": "testnetwork", "netmask": "255.255.255.0", "vlan": "210", "gateway": "10.188.210.1", "dns1": "10.188.0.2", "dns2": "10.188.0.3", "ipAddr": "10.188.210.45", "bootProto": "static", "hostName": "host45", "serverProfile": "sp21", "osPackage": "VMware-ESXi-6.7.0-Update3-15160138-HPE-Gen9plus-670.U3.10.5.0.48-Dec2019.iso", "id": 0, "progress": 4, "status": "In-Progress", "startTime": ["2020-04-12T01:45:56.261634"], "message": "Created the server profile: sp45"}') 

    replacedData = replaceWithSPData(oneview_client, OSConfigJSON, spdata) 
    print("Replaced data: ")
    print(replacedData)


    #genOVCert(ovdetails)

    #getOVSPTNetworkConnections("Synergy210", "SPT-ESXi")

    #createOSPackage({'ospackage': 'esxi12', 'ostype': 'ESXi6.7'}, "/tmp/VMware-ESXi-6.7.0-9484548-HPE-Gen9plus-670.10.3.5.6-Sep2018.iso")
