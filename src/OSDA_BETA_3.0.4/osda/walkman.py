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

from pprint import pprint
from hpOneView.oneview_client import OneViewClient
from hpOneView.exceptions import HPOneViewException

import json
import threading
import random
import socket

import os
import uuid
import re
import time
import datetime
import logging

import osda.config as config
import osda.ospackages as ospackages
import osda.geniso  as geniso
import osda.rhelgeniso as rhelgeniso
import osda.susegeniso as susegeniso
import osda.ilodeployment as ilodeployment
import osda.ilodeploymentgen9 as ilodeploymentgen9
import osda.synergydeployment as synergydeployment


# You can use username/password or sessionID for authentication.
# Be sure to inform a valid and active sessionID.
osActivitiesConfig = config.Activities()
defaultConfig = config.DefaultConfig()

walkman_settings = {}
#ksfiles_settings = {}
#ospackages_settings = []


def init(hostname):
    try:
        # Set up cert directory and config directory if not present
        directories = ['/opt/hpe/osda/data/config', '/opt/hpe/osda/data/certs']
        for directory in directories:
            if not os.path.exists(directory):
                os.mkdir(directory)

        # Check for the default config files. Create new config with its default contents if file does not exists.
        defaultConfigs ={
            '/opt/hpe/osda/data/config/ksfiles.json' : '[]',
            '/opt/hpe/osda/data/config/ksfiles.json' : json.dumps([
                    {
                        "osType": "ESXi6",
                        "basekspath": "/opt/hpe/osda/data/kickstarts/esxi67/ks.cfg"
                    },
                    {
                        "osType": "ESXi7",
                        "basekspath": "/opt/hpe/osda/data/kickstarts/esxi70/ks.cfg"
                    },
                    {
                        "osType": "RHEL7",
                        "basekspath": "/opt/hpe/osda/data/kickstarts/rhel76/ks.cfg"
                    },
                    {
                        "osType": "SLES15",
                        "basekspath": "/opt/hpe/osda/data/kickstarts/sles15/autoinst.xml"
                    }], indent=2),
            '/opt/hpe/osda/data/config/networks.json' : '[]',
            '/opt/hpe/osda/data/config/ospackages.json' : '[]',
            '/opt/hpe/osda/data/config/ovappliances.json' : '[]',
            '/opt/hpe/osda/data/config/walkman.json' : json.dumps({
                "ov_certs_path": "/opt/hpe/osda/data/certs",
                "temp_dir": "/tmp",
                "ks_basedir": "/opt/hpe/osda/data/kickstarts", 
                "http_server": "local", 
                "local_http_root": defaultConfig.htmlPath, 
                "http_file_server_url": "http://127.0.0.1/"})
        }
        for configFile, defaultContent in defaultConfigs.items():
            if not os.path.exists(configFile):
                with open(configFile, 'w') as newFile:
                    newFile.write(defaultContent)
        
        config.WalkmanSettings().set("http_file_server_url", "http://" + hostname + "/")

    #    fin = open('../config/ksfiles.json', 'r')
    #    global ksfiles_settings 
    #    ksfiles_settings = json.load(fin)
    #    #print(ksfiles_settings)
    #    fin.close()

    #    fin = open('../config/ospackages.json', 'r')
    #    global ospackages_settings
    #    ospackages_settings = json.load(fin)
    #    print(ospackages_settings)
    #    fin.close()

        ospackages.init('/opt/hpe/osda/data/config/ospackages.json', '/opt/hpe/osda/data/config/ksfiles.json' )

        synergydeployment.init()
    except Exception as err:
        logging.exception(err)
        raise err

def getDashboardData():
    try:
        #ovcount = len(ov_appliances)
        ovcount = synergydeployment.getOVCount()
        osPackagesStats = ospackages.getOSPackagesStats()

        return ({ "ovCount": ovcount, "osPackages": osPackagesStats})
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def getOSPackageById(id):
    try:
        return ospackages.getOSPackageById(id)
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def deleteOSPackageById(id):
    try:
        hostOSdistro = defaultConfig.hostDistroName
        return ospackages.deleteOSPackageById(id, hostOSdistro)
    except Exception as err:
        logging.exception(err)
        raise Exception(str(err))

def getOSPackages():
    try:
        return ospackages.getOSPackages()
    except Exception as err:
        logging.exception(err)
        raise Exception from err


# TASK is any long running operation that runs asynchrously as a thread/process
# Each long running task shall be assigned with TASKID so that the caller can
# poll for the task status using this identifier

# Tasks lookup table for storing task progress
# Lookup this table using TASKID for querying task progress information

# VALID STATES
# Main Task Status: What are the expected values (Running/Success/Fail)
# Sub Task status: What are the expected values (Complete/Running/Error/)

def getTaskStatus(taskid):
    '''
    The overall task status should be either Running, Success, or Fail
    The subtask status should be either Error, Complete, or In-Progress
    '''
    try:
        taskStatus = osActivitiesConfig.getTaskStatus(taskid)
        logging.debug(f"Task[{taskid}]: {taskStatus}")
        overallProgress = 0
        if not taskStatus.get("subTasks"):
            return taskStatus
        
        totalTasks = subTasksToComplete = len(taskStatus["subTasks"])
        subTasksError = 0
        failedHosts = []
        running = 0
        completed = 0
        error = 0
        for subTask in taskStatus["subTasks"]:
            #logging.debug(f"{subTask['hostName']} progress: {subTask['progress']}, status: {subTask['status']}")
            if subTask["status"].lower() == "complete":
                completed += 1
            elif subTask["status"].lower() == "in-progress":
                running += 1
            elif subTask["status"].lower() == "error":
                error += 1

            overallProgress += subTask["progress"]
            if subTask["status"].lower() == "complete" or subTask["status"].lower() == "error":
                subTasksToComplete -= 1
                if subTask["status"].lower() == "error":
                    subTasksError += 1
                    #failedHosts.append(subTask["hostName"])
        taskStatus['progress'] = round(overallProgress / totalTasks)
        if running > 0:
            taskStatus["status"] = "Running"
        elif error > 0:
            taskStatus["status"] = "Failed"
            failedHosts = ", ".join(failedHosts)
            errorMsg = f"Task {taskid} failed. Total {subTasksError} hosts failed to deploy: {failedHosts}"
            taskStatus["errorMsg"] = errorMsg
        elif completed > 0:
            taskStatus["status"] = "Completed"

        #if subTasksToComplete == 0 and subTasksError == 0:
        #    taskStatus["status"] = "Success"
        #elif subTasksToComplete == 0 and subTasksError > 0:
        #    taskStatus["status"] = "Fail"
        return taskStatus
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def getAvailableKickStarts(osType):
    return ospackages.getAvailableKickstarts(osType)



def getSupportedOSList():
    try:
        #return config.OSPackage().getSupportedOSList()
        return ospackages.getSupportedOSList()
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def getAllTasks():
    try:
        return osActivitiesConfig.getAllTasks()
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def getOVAppliance(ovalias):
    try:
        return synergydeployment.getOVAppliance(ovalias)
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def deleteOVAppliance(ovalias):
    try:
        return synergydeployment.deleteOVAppliance(ovalias)
    except Exception as err:
        logging.exception(str(err))
        raise Exception(str(err))

def getRegisteredOVs():
    try:
        return synergydeployment.getRegisteredOVs()
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def checkOVdetailInputs(oneviewDetails):
    ovParameters = ["ovName", 'ovSPT']
    for param in ovParameters:
        if param not in oneviewDetails:
            errMsg = f"Missing {param} in user input. Deployment may fail. Please add {param}."
            logging.error(errMsg)
            return errMsg
        elif oneviewDetails[param] is None or oneviewDetails[param] == "":
            errMsg = f"Empty {param} parameter. Deployment may fail. Please specify {param}."
            logging.error(errMsg)
            return errMsg
    return None

def checkILOinputs(hosts):
    try:
        hostParameters = ["iloIPAddr","iloUser", "iloPassword", "hostName", "osPackage", "kickstartFile", "networks", "osDrive"]
        networkParameters = ["ipAddr", "netmask", "gateway", "dns", "bootProto", "nic1", "nic2", "bondingType", "vlans"]
        nicParameters = ["adapterId", "portId"]
        osDriveParameters = ["logicalDrive"]
        logicalDriveParameters = ["logicalDriveNumber", "operation"]
        
        for host in hosts:
            for param in hostParameters:
                if param not in host:
                    errMsg = f'Missing {param} parameter in host parameters. Deployment may fail. Please add {param} in target host parameters.'
                    logging.error(errMsg)
                    return errMsg
                elif host[param] is None:
                    errMsg = f'Empty {param} parameter in host parameters. Deployment may fail. Please specify {param} in target host.'
                    logging.error(errMsg)
                    return errMsg
                else:
                    continue

            networks = host["networks"]
            if len(networks) == 0:
                errMsg = f'Empty networks in host parameters. Deployment may fail. Please add networks for target host.'
                logging.error(errMsg)
                return errMsg
#            else:
#                emptyNetwork = 0
#                for network in networks:
#                    if not network or len(network) == 0:
#                        emptyNetwork += 1
#                        break
#                    else:
#                        for param in networkParameters:
#                            if param not in network:
#                                return f'Missing {param} parameter in target network parameters. Deployment may fail. Please add {param} in target target network parameters.'
#                            elif network[param] == None:
#                                return f'Empty {param} in network parameters. Deployment may fail. Please specify {param} in network parameters.'
#                            else:
#                                pass
#
#                    nic1 = network["nic1"]
#                    for param in nicParameters:
#                        if param not in nic1:
#                            return f'Missing {param} in nic1 parameters. Deployment may fail. Please add {param} in nic1.'
#                        elif nic1[param] is None or nic1[param] == "":
#                            return f'Empty {param} in nic1 parameters. Deployment may fail. Please specify {param} in nic1.'
#                        else:
#                            pass
#
#                    nic2 = network["nic2"]
#                    for param in nicParameters:
#                        if param not in nic2:
#                            return f'Missing {param} in nic2 parameters. Deployment may fail. Please add {param} in nic2.'
#                        elif nic1[param] is None:
#                            return f'Empty {param} in nic2 parameters. Deployment may fail. Please specify {param} in nic2.'
#                        else:
#                            pass
#                if emptyNetwork == len(networks):
#                    return f'Empty networks. Deployment may fail. Need at least one network.'

#            osDrive = host["osDrive"]
#            for param in osDriveParameters:
#                if param not in osDrive:
#                    return f'Missing {param} in osDrive parameters. Deployment may fail. Please add {param} in osDrive.'
#                elif osDrive[param] is None or osDrive[param] == "":
#                    return f'Empty {param} in osDrive parameters. Deployment may fail. Please specify {param} in osDrive.'
#                else:
#                    pass

            #logicDrive = osDrive["logicalDrive"]
            #for param in logicalDriveParameters:
            #    if param not in logicDrive:
            #        return f'Missing {param} in logicalDrive parameters. Deployment may fail. Please add {param} in logicalDrive.'
            #    elif logicDrive[param] is None or logicDrive[param] == "":
            #        return f'Empty {param} in logicalDrive parameters. Deployment may fail. Please specify {param} in logicalDrive.'
            #    else:
            #        pass
        return None
    except Exception as err:
        logging.exception(err)
        raise(err)

def checkSynergyHostInputs(hosts):
    try:
        hostParameters = ["serverProfile", "hostName", "osPackage", "kickstartFile", "networks", "osDrive"]
        networkParameters = ["ipAddr", "netmask", "gateway", "dns", "bootProto", "nic1", "nic2", "bondingType", "vlans"]
        nicParameters = ["connectionName"]
        osDriveParameters = ["driveName"]
        for host in hosts:
            for param in hostParameters:
                if param not in host:
                    errMsg = f'Missing {param} parameter in host parameters. Deployment may fail. Please add {param} in target host parameters.'
                    logging.error(errMsg)
                    return errMsg
                elif host[param] is None:
                    errMsg = f'Empty {param} parameter in host parameters. Deployment may fail. Please specify {param} in target host.'
                    logging.error(errMsg)
                    return errMsg
                else:
                    continue

            networks = host["networks"]
            if len(networks) == 0:
                errMsg = f'Empty networks in host parameters. Deployment may fail. Please add networks for target host.'
                logging.error(errMsg)
                return errMsg
            '''
            else:
                emptyNetwork = 0
                for network in networks:
                    logging.debug("Network: {network}".format(network=network))
                    if not network or len(network) == 0:
                        logging.debug("Empty Network: {network}".format(network=network))
                        emptyNetwork += 1
                        break
                    else:
                        for param in networkParameters:
                            if param not in network:
                                errMsg = f'Missing {param} parameter in target network parameters. Deployment may fail. Please add {param} in target target network parameters.'
                                logging.error(errMsg)
                                return errMsg
                            elif network[param] == None:
                                errMsg = f'Empty {param} in network parameters. Deployment may fail. Please specify {param} in network parameters.'
                                logging.error(errMsg)
                                return errMsg
                            else:
                                pass

                    nic1 = network["nic1"]
                    for param in nicParameters:
                        if param not in nic1:
                            errMsg = f'Missing {param} in nic1 parameters. Deployment may fail. Please add {param} in nic1.'
                            logging.error(errMsg)
                            return errMsg
                        elif nic1[param] is None or nic1[param] == "":
                            errMsg = f'Empty {param} in nic1 parameters. Deployment may fail. Please specify {param} in nic1.'
                            logging.error(errMsg)
                            return errMsg
                        else:
                            pass

                    nic2 = network["nic2"]
                    for param in nicParameters:
                        if param not in nic2:
                            errMsg = f'Missing {param} in nic2 parameters. Deployment may fail. Please add {param} in nic2.'
                            logging.error(errMsg)
                            return errMsg
                        elif nic1[param] is None:
                            errMsg = f'Empty {param} in nic2 parameters. Deployment may fail. Please specify {param} in nic2.'
                            logging.error(errMsg)
                            return errMsg
                        else:
                            pass

                if emptyNetwork == len(networks):
                    errMsg = f'Empty networks. Deployment may fail. Need at least one network.'
                    logging.error(errMsg)
                    return errMsg
            '''
#            osDrive = host["osDrive"]
#            for param in osDriveParameters:
#                if param not in osDrive:
#                    errMsg = f'Missing {param} in osDrive parameters. Deployment may fail. Please add {param} in osDrive.'
#                    logging.error(errMsg)
#                    return errMsg
#                elif osDrive[param] is None or osDrive[param] == "":
#                    errMsg = f'Empty {param} in osDrive parameters. Deployment may fail. Please specify {param} in osDrive.'
#                    logging.error(errMsg)
#                    return errMsg
#                else:
#                    pass
        return None

    except Exception as err:
        logging.exception(err)
        raise(err)

def validateDeployData(deployData):
    try:
        logging.info("Running validation check on user input JSON")
        logging.debug(deployData)
        
        logging.info("Checking for OS packages on OSDA")
        OSPackages = getOSPackages()
        if len(OSPackages) == 0:
            msg = "OSDA does not have any OS ISO packages. Deployment may fail. Please upload the OS ISO for deployment."
            logging.error(msg)
            return (200, msg)
        logging.debug(OSPackages)

        logging.info("Checking task paramters")
        taskParameters = ["taskName", "hosts", "deploymentMode"]
        for param in taskParameters:
            if param not in deployData:
                msg = f"Missing {param} in the deployment parameters. Deployment may fail. Please add {param}."
                logging.error(msg)
                return (400, msg)
        
        if len(deployData["hosts"]) == 0:
            msg = "Empty hosts information in user input. Deployment may fail. Please add target hosts."
            logging.error(msg)
            return (400, msg)
        
        #if deployData["osPackage"] is None or deployData["osPackage"] == "":
        #    msg = "Missing OS package information in user input. Deployment may fail. Please specify OS package to install."
        #    logging.error(msg)
        #    return (1, msg)

        synergyTaskParameters = ["createServerProfile", "oneviewDetails"]
        if deployData["deploymentMode"] == "hpesynergy":
            logging.info("Checking parameters for Synergy deployment tasks")
            logging.info("Checking for OV appliances on OSDA")
            registeredOVs = getRegisteredOVs()
            if len(registeredOVs) == 0:
                msg = "OSDA does not have any OV appliance registered for Synergy deployment. Please add the OV appliance for deployment."
                logging.error(msg)
                return (200,msg)
            logging.debug(registeredOVs)

            logging.info("Checking Synergy task parameters")
            for param in synergyTaskParameters:
                if param not in deployData:
                    msg = f"Missing {param} in the deployment parameters. Deployment may fail. Please add {param}."
                    logging.error(msg)
                    return (400, msg)
            
            if deployData["createServerProfile"] is None:
                msg = "Empty createServerProfile parameter. Deployment may fail. Please specify createServerProfile parameter."
                logging.error(msg)
                return (400,msg)

            errorMessage = checkOVdetailInputs(deployData["oneviewDetails"])
            if errorMessage:
                logging.error(errorMessage)
                return (400, errorMessage)         

            logging.info("Checking hosts parameters for Synergy deployment")
            errorMessage = checkSynergyHostInputs(deployData["hosts"])
            if errorMessage:
                return (400, errorMessage)    

            logging.info("Checking OV appliance specified in deploy JSON")
            targetOV_found = False
            ovName = deployData["oneviewDetails"]["ovName"]
            for ov in registeredOVs:
                if ovName == ov['alias']:
                    targetOV_found = True
                    break
            if not targetOV_found:
                msg = f"Target {ovName} OV appliance specified in user input not found. Deployment may fail. Please check the OneView detail in the deployment confiugration."
                logging.error(msg)
                return (200,msg)

        elif deployData["deploymentMode"] == "hpeilo" or deployData["deploymentMode"] == "hpeilo_gen9":
            logging.info("Checking parameters for iLO deployment tasks")
            
            logging.info("Checking hosts parameters for iLO deployment")
            errorMsg = checkILOinputs(deployData["hosts"])
            if errorMsg:
                logging.error(errorMsg)
                return (400, errorMsg)
        else:
            msg = "Unidentified deployment mode in user input. Deployment may fail. Please specify hpeilo, hpeilo_gen9, or hpyesynergy"
            logging.error(msg)
            return(400, msg)
        
        return (0, "")
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def deployMain(deployData, operation="DEPLOY"):
    try:
        logging.debug("deployMain: deployData: ")
        logging.debug(deployData)

        logging.debug("deployMain: operation: " + operation)

        if operation == "DEPLOY":
            validationresult, errorMsg = validateDeployData(deployData)
            status_code = validationresult
            if(validationresult != 0):
                return({"result": {},  "error": errorMsg}, status_code)

        taskID = osActivitiesConfig.createTask(deployData)

        #return ({"result": { "taskID": taskID}, 'error': {}})

        # thread function for each deployment method
        threadfunction = ""
        deployErrors = {}
        result = {}
        if operation == "DEPLOY":
            if(deployData['deploymentMode'] == "hpeilo"):
                logging.info("HPE iLO based deployment for Gen10 servers")
                result = ilodeployment.deploy(osActivitiesConfig, taskID, deployData)

            elif(deployData['deploymentMode'] == "hpesynergy"):
                logging.info("HPE OneView based deployment")
                result = synergydeployment.deploy(taskID, deployData)

            elif(deployData['deploymentMode'] == "hpeilo_gen9"):
                logging.info("HPE iLO based deployment for Gen9 servers")
                result = ilodeploymentgen9.deploy(osActivitiesConfig, taskID, deployData)

            else:
                logging.info("Unsupported deployment method")
                errMsg = "Unsupported deployment method [" + deployData['deploymentMode'] + "] specified"
                return({"result": {}, "error": errMsg}, 503)

        elif operation == "UNDEPLOY":
                if(deployData['deploymentMode'] == "hpeilo"):
                    logging.info("HPE iLO based deployment for Gen10 servers")
                    result = ilodeployment.unDeploy(osActivitiesConfig, taskID, deployData)

#                elif(deployData['deploymentMode'] == "hpesynergy"):
#                    logging.info("HPE OneView based deployment")
#                    result = synergydeployment.unDeploy(taskID, deployData)
#
#                elif(deployData['deploymentMode'] == "hpeilo_gen9"):
#                    logging.info("HPE iLO based deployment for Gen9 servers")
#                    result = ilodeploymentgen9.unDeploy(osActivitiesConfig, taskID, deployData)
#
                else:
                    logging.info("Unsupported deployment method")
                    errMsg = "Unsupported deployment method [" + deployData['deploymentMode'] + "] specified"
                    return({"result": {}, "error": errMsg}, 503)

        else:
            errMsg = "Invalid operation type specified for deployMain. Exiting"
            logging.error(errMsg)
            #raise Exception("Invalid operation type specified for deployMain. Exiting")
            return({"result": {}, "error": errMsg}, 400)

        if result:
            deployErrors = result.get('error', {})
        
        return ({"result": { "taskID": taskID}, 'error': deployErrors}, 200)

    except Exception as err:
        logging.exception(err)
        raise Exception from err

def registerOV(ovdetails):

    try:
        ov_entry =  synergydeployment.registerOV(ovdetails)
        return ({"result": "success", "error": {}})
    except Exception as err:
        return ({"result": "error", "error": {"message": str(err)}})
        

def getSPTs(ovalias):
    try:
        return synergydeployment.getSPTs(ovalias)
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def getILONetworkConnections(iloip, ilocreds, gen="Gen10"):
    try:
        if gen == "Gen10": 
            return ilodeployment.getILONetworkConnections_ex(iloip, ilocreds['user'], ilocreds['password'])
        elif gen == "Gen9": 
            return ilodeploymentgen9.getILONetworkConnections_ex(iloip, ilocreds['user'], ilocreds['password'])
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def getILOStorageDrives(iloip, ilocreds, gen="Gen10"):
    try:
        if gen == "Gen10": 
            return ilodeployment.getILOStorageDrives_ex(iloip, ilocreds['user'], ilocreds['password'])
        elif gen == "Gen9": 
            return ilodeploymentgen9.getILOStorageDrives_ex(iloip, ilocreds['user'], ilocreds['password'])
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def getOVSPTNetworkConnections(ovname, sptname):
    try:
        return synergydeployment.getOVSPTNetworkConnections(ovname, sptname)
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def getOVSPTStorageDrives(ovname, sptname):
    try:
        return synergydeployment.getOVSPTStorageDrives(ovname, sptname)
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


def createOSPackage(ospackagedata, orig_iso_path):
    try:
        logging.info("createOSPackage: Generating OS package for: ")
        logging.info(ospackagedata)

        ospackitem = json.loads('{ "uri": "", "package": "", "osType":  "", "ISO_http_path": "" }')

        ospackitem['uri'] = uuid.uuid4().hex
        ospackitem['package'] = ospackagedata['name']
        ospackitem['osType'] = ospackagedata['osType']

        target_dir = config.WalkmanSettings().get("local_http_root")
        hostOSdistro = defaultConfig.hostDistroName

        if ospackitem['osType'] == 'ESXi6':
            target_iso_path = geniso.createKickstartISO_ESXi67(orig_iso_path, target_dir, hostOSdistro)
            logging.info("createOSPackage: target_iso_path: " + str(target_iso_path))
            ospackitem['ISO_http_path'] = target_iso_path.split(target_dir)[1]
            ospackages.setOSPackage(ospackitem)
            return { "result": ospackitem, "error": ""}
        elif ospackitem['osType'] == 'ESXi7':
            target_iso_path = geniso.createKickstartISO_ESXi67(orig_iso_path, target_dir, hostOSdistro)
            logging.info("createOSPackage: target_iso_path: " + str(target_iso_path))
            ospackitem['ISO_http_path'] = target_iso_path.split(target_dir)[1]
            ospackages.setOSPackage(ospackitem)
            return { "result": ospackitem, "error": ""}
        elif ospackitem['osType'] == 'RHEL7':
            target_iso_path = rhelgeniso.createKickstartISO_RHEL76(orig_iso_path, target_dir, hostOSdistro)
            logging.info("createOSPackage: target_iso_path: " + str(target_iso_path))
            ospackitem['ISO_http_path'] = target_iso_path.split(target_dir)[1]
            ospackages.setOSPackage(ospackitem)
            return { "result": ospackitem, "error": ""}
        elif ospackitem.get('osType').upper() == 'SLES15':
            target_iso_path = susegeniso.createAutoYastISO(orig_iso_path, target_dir, hostOSdistro)
            logging.info("createOSPackage: target_iso_path: " + str(target_iso_path))
            ospackitem['ISO_http_path'] = target_iso_path.split(target_dir)[1]
            ospackages.setOSPackage(ospackitem)
            return { "result": ospackitem, "error": ""}

        return {"result": {}, "error": "Unsupported OS type"}
    except Exception as err:
            logging.exception(err)
            raise Exception from err

def getNetworks():
    try:
        fin = open('/opt/hpe/osda/data/config/networks.json', 'r')
        networks = json.load(fin)
        fin.close()

        return networks
    except Exception as err:
            logging.exception(err)
            raise Exception from err

def addNetwork(network):
    try:
        if not network:
            raise Exception('Empty network information')
        fin = open('/opt/hpe/osda/data/config/networks.json', 'r')
        networks = json.load(fin)
        fin.close()

        for networkitem in networks:
            if networkitem['name'] == network['name']:
                errMsg = "A network with name " + network['name'] + "already exists"
                logging.error(errMsg)
                return { 'error': errMsg, 'result': "fail"}
                

        networks.append(network)
        fout = open('/opt/hpe/osda/data/config/networks.json', 'w')
        json.dump(networks, fout,indent=2)
        fout.close()

        return {'error': "", 'result': "success"}
    except Exception as err:
            logging.exception(err)
            raise Exception from err

def getNetwork(networkname):
    try:

        fin = open('/opt/hpe/osda/data/config/networks.json', 'r')
        networks = json.load(fin)
        fin.close()

        for network in networks:
            logging.debug(network)
            if network['name'] == networkname:
                return { "result": network, "error": ""}

        return { "result": {}, "error": "Requested deployment network NOT found "}
    except Exception as err:
            logging.exception(err)
            raise Exception from err

if __name__ == '__main__':

    print("main")
 #   ilocreds = {"user": "v241usradmin", "password": "HP!nvent123"}
  #  getILONetworkConnections("10.188.1.184", ilocreds )


    #taskID = createTask(3)
   # print("########################################")
    #print(TasksTable)
    #print("########################################")
    #setTaskStatus(taskID, 0, "Completed")

    init("10.188.210.14")

    #ovconfig = getOVConfig("syn0210")
    #oneview_client = oneviewConnect(ovconfig)
    #spdata = oneview_client.server_profiles.get_by_name("sp21")

    #OSConfigJSON = json.loads('{"mgmtNIC": {"connectionName": "vmnic0"}, "osDrive": {"driveName": "localosdrive"}, "networkName": "testnetwork", "netmask": "255.255.255.0", "vlan": "210", "gateway": "10.188.210.1", "dns1": "10.188.0.2", "dns2": "10.188.0.3", "ipAddr": "10.188.210.45", "bootProto": "static", "hostName": "host45", "serverProfile": "sp21", "osPackage": "VMware-ESXi-6.7.0-Update3-15160138-HPE-Gen9plus-670.U3.10.5.0.48-Dec2019.iso", "id": 0, "progress": 4, "status": "In-Progress", "startTime": ["2020-04-12T01:45:56.261634"], "message": "Created the server profile: sp45"}') 

    #replacedData = replaceWithSPData(oneview_client, OSConfigJSON, spdata) 
    #print("Replaced data: ")
    #print(replacedData)


    #genOVCert(ovdetails)

    #getOVSPTNetworkConnections("Synergy210", "SPT-ESXi")

    #createOSPackage({'name': 'esxi12', 'osType': 'SLES15'}, "/tmp/VMware-ESXi-6.7.0-9484548-HPE-Gen9plus-670.10.3.5.6-Sep2018.iso")
    #
    '''
    osInfo = {'name': 'SLES-test', 'osType': 'SLES15'}
    isoPath = "/tmp/SLE-15-Installer-DVD-x86_64-GM-DVD1.iso"
    print(f'create OS package for {osInfo} with {isoPath}')
    createOSPackage(osInfo, isoPath)

    osInfo = {'name': 'RHEL7-test', 'osType': 'RHEL7'}
    isoPath =  "/tmp/RHEL-7.8-20200225.1-Server-x86_64-dvd1.iso"
    isoPath =  "/tmp/RHEL-7.7-20190723.1-Server-x86_64-dvd1.iso"
    print(f'create OS package for {osInfo} with {isoPath}')
    createOSPackage(osInfo, isoPath)

    osInfo = {'name': 'esxi12', 'osType': 'ESXi6'}
    isoPath =  "/tmp/VMware-ESXi-6.7.0-9484548-HPE-Gen9plus-670.10.3.5.6-Sep2018.iso"
    print(f'create OS package for {osInfo} with {isoPath}')
    createOSPackage(osInfo, isoPath)

    createOSPackage({'name': 'esxi12', 'osType': 'SLES15'}, "/tmp/VMware-ESXi-6.7.0-9484548-HPE-Gen9plus-670.10.3.5.6-Sep2018.iso")
    createOSPackage({'name': 'RHEL_7.8', 'osType': 'RHEL7'}, "/tmp/RHEL-7.8-20200225.1-Server-x86_64-dvd1.iso")
    '''

    osInfo = {'name': 'CentOS-7-x86_64-Minimal-2003', 'osType': 'RHEL7'}
    isoPath =  "/root/CentOS-7-x86_64-Minimal-2003.iso"
    print(f'create OS package for {osInfo} with {isoPath}')
    createOSPackage(osInfo, isoPath)

    print(defaultConfig.htmlPath)
