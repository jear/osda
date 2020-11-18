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


import requests
import json
import time
import logging

from hpOneView.exceptions import HPOneViewException
from hpOneView.oneview_client import OneViewClient

# Suppress warning - InsecureRequestWarning: Unverified HTTPS request is being made
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#######################################
# Class for iLO operations using SSO
#######################################
class iLoClient():

    # FIXED REST API based values for POWER
    POWER_OFF = "ForceOff"
    POWER_ON  = "On"
    POWER_RESET = "ForceRestart"
    POWER_PUSH = "PushPowerButton"
    POWER_GRACEFUL_SHUTDOWN = "GracefulShutdown"


    def __init__(self, ov_client):
        self._oneview_client = ov_client
        self._iLO_IP = None
        self._sessionID = None

    ##################################
    # Get iLO IP using oneview_client
    ##################################
    def get_iLOIp(self, srvHardwareUri):
        srvHardware = self._oneview_client.connection.get(srvHardwareUri)
        #print("############Server Hardware from get_iLOIp#####")
        #print(srvHardwareUri)
        #print(srvHardware)
        try:
            iLOIp = srvHardware["mpHostInfo"]["mpHostName"]
            iLOIpAddresses = srvHardware["mpHostInfo"]["mpIpAddresses"]
            for ip in iLOIpAddresses:
                if ip["type"] in ("DHCP", "Static"):
                    iLOIp = ip["address"]
                
            #iLOIp = [ ip["address"] for ip in iLOIpAddresses if ip["type"] in ("DHCP", "Static") ][0] 
        except Exception as e:
            raise Exception("Could not get iLO IP. Error message: {}".format(e))

        return iLOIp
    
    ##################################
    # Get SSO session ID
    ##################################
    def get_SSO_sessionID(self, srvHardwareUri):

        # Get SSO session ID
        url = srvHardwareUri + "/remoteConsoleUrl"
        resp = self._oneview_client.connection.get(url)
        # TODO: Sometimes the "remoteConsoleUrl" is blank, retry the operation to fix it.
        try:
            iLOSessionID = [ x.split("=")[1] for x in resp["remoteConsoleUrl"].split("&") if x.startswith("sessionkey")][0]
        except Exception as e:    
            raise Exception("Couldn't get session ID. remoteConsoleUrl = {}\nerrMessage : {}".format(resp["remoteConsoleUrl"], e))

        return iLOSessionID
        
    ##################################
    # Do rest/redfish GET
    ##################################
    def login(self, srvHardwareUri):
        self._iLO_IP = self.get_iLOIp(srvHardwareUri)
        self._sessionID = self.get_SSO_sessionID(srvHardwareUri)
        
    ##################################
    # Do rest/redfish GET
    ##################################
    def do_get(self, uri):
        reqUrl = "https://" + self._iLO_IP + uri
        headers = { 'X-Auth-Token': self._sessionID }

        resp = requests.get(reqUrl, headers=headers, verify = False)
        if isinstance(resp.status_code ,str):
            # The response status received is a string. So converted to this format.
            if (resp.status_code != str(200)):
                raise Exception("Failed to do GET. Status code = {}\nError Message = {}.".format(resp.status_code, resp.text))
        else:
            if (resp.status_code != 200):
                raise Exception("Failed to do GET. Status code = {}\nError Message = {}.".format(resp.status_code, resp.text))
            
        #logging.debug(resp.json())
        return resp.json()
        
    ##################################
    # Do rest/redfish PATCH
    ##################################
    def do_patch(self, uri, body):
        reqUrl = "https://" + self._iLO_IP + uri
        headers = { 'X-Auth-Token': self._sessionID }

        resp = requests.patch(reqUrl, headers=headers, json=body, verify = False)

        if (resp.status_code != 200):
            raise Exception("Failed to do PATCH. Status code = {}\nError Message = {}.".format(resp.status_code, resp.text))

        return resp.json()

    ##################################
    # Do rest/redfish POST
    ##################################
    def do_post(self, uri, body):
        reqUrl = "https://" + self._iLO_IP + uri
        headers = { 'X-Auth-Token': self._sessionID }

        resp = requests.post(reqUrl, headers=headers, json=body, verify = False)

        if (resp.status_code != 200):
            raise Exception("Failed to do POST. Status code = {}\nError Message = {}.".format(resp.status_code, resp.text))

        return resp.json()


    

    ##############################################
    # Get the VolumeUniqueIdentifier of logical drive matching the logical drive number
    ##############################################
    def get_logical_drive_VolumeUniqueIdentifier(self, srvHardwareUri, logicalDriveNumber):

        logging.debug("get_logical_drive_VolumeUniqueIdentifier: logicalDriveNumber: " + str(logicalDriveNumber))
        #Login to iLO using SSO
        self.login(srvHardwareUri)

        # Before querying iLO for local storage information power-up the server to allow POST 
        # to complete to allow BIOS to update iLO with current local storage configuration
        # In certain cases the iLO has missing local storage information when the server is in OFF state
        # Boot order is changed to boot to System Configuration (F9) to avoid server from booting 
        # into previously installed OS
        self.changeTemporaryBootOrder()
        self.resetPowerState()
        self.waitForBiosPost()

        controllers = self.do_get('/redfish/v1/Systems/1/SmartStorage/ArrayControllers')
        logicalDriveID = ""

        for arrayController in controllers["Members"]:
            driveResponse = self.do_get(arrayController["@odata.id"])
            if "LogicalDrives" in driveResponse['Links']:
                logicalDrives = self.do_get(driveResponse['Links']['LogicalDrives']['@odata.id'])['Members']
                for item in logicalDrives:
                    logicalDrive = self.do_get(item["@odata.id"])
                    logging.debug(logicalDrive)
                    if logicalDriveNumber == logicalDrive['LogicalDriveNumber']:
                        logicalDriveID = logicalDrive['VolumeUniqueIdentifier']

        # After getting the storage information shutdown the server gracefully
        self.setPowerState("graceful-shutdown")
        time.sleep(5)
        return logicalDriveID


    ##############################################
    # Check and Eject if Virtual Media Mounted  
    ##############################################
    def vmedia_eject(self, srvHardwareUri):
        #Login to iLO using SSO
        self.login(srvHardwareUri)

        managers = self.do_get('/redfish/v1/Managers')

        for manager in managers["Members"]:
            resp = self.do_get(manager['@odata.id'])
            if not resp["VirtualMedia"]:
                continue

            vmediaUri = resp["VirtualMedia"]["@odata.id"]
            resp = self.do_get(vmediaUri)
            for member in resp["Members"]:
                resp = self.do_get(member['@odata.id'])
                logging.debug("##########################")
                logging.debug(resp['MediaTypes'])

                if 'DVD' in resp['MediaTypes']:
                    if resp['Inserted']:
                         logging.info("CD/DVD Media already Inserted, Now Ejecting")
                         body={}
                         rejecturi="/redfish/v1/Managers/1/VirtualMedia/2/Actions/VirtualMedia.EjectMedia"
                         self.do_post(rejecturi, body)

                if 'USBStick' in resp['MediaTypes']:
                    if resp['Inserted']:
                         logging.info("Virtual Floppy/USB Media already Inserted, Now Ejecting")
                         body={}
                         rejecturi="/redfish/v1/Managers/1/VirtualMedia/1/Actions/VirtualMedia.EjectMedia"
                         self.do_post(rejecturi, body)

    
    ##################################
    # Mount iso to iLO virtual media
    ##################################
    def mount_vmedia_iLO(self, srvHardwareUri, isoUrl, BootOnNextServerReset):
        #Login to iLO using SSO
        self.login(srvHardwareUri)

        managers = self.do_get('/redfish/v1/Managers')

        for manager in managers["Members"]:
            resp = self.do_get(manager['@odata.id'])
            if not resp["VirtualMedia"]:
                continue

            vmediaUri = resp["VirtualMedia"]["@odata.id"]
            resp = self.do_get(vmediaUri)
            for member in resp["Members"]:
                resp = self.do_get(member['@odata.id'])
                logging.debug("##############")
                logging.debug(resp['MediaTypes'])

                if 'DVD' not in resp['MediaTypes']: 
                    continue

                body = {"Image": isoUrl }
                body["Oem"] = {"Hpe": {"BootOnNextServerReset": BootOnNextServerReset}}

                resp = self.do_patch(resp['@odata.id'], body)
        return resp


    ##################################
    # Mount IMG to iLO virtual USB
    ##################################
    def mount_vusb(self, srvHardwareUri, imgUrl):
        #Login to iLO using SSO
        self.login(srvHardwareUri)

        managers = self.do_get('/redfish/v1/Managers')

        for manager in managers["Members"]:
            resp = self.do_get(manager['@odata.id'])
            if not resp["VirtualMedia"]:
                continue

            vmediaUri = resp["VirtualMedia"]["@odata.id"]
            resp = self.do_get(vmediaUri)
            for member in resp["Members"]:
                resp = self.do_get(member['@odata.id'])
                logging.debug("##############")
                logging.debug(resp['MediaTypes'])

                if 'USBStick' not in resp['MediaTypes']:
                    continue

                body = {"Image": imgUrl }

                resp = self.do_patch(resp['@odata.id'], body)
        return resp

    ##################################
    # Unmount media drives from iLO
    ##################################
    def umount_drives(self, srvHardwareUri):
        #Login to iLO using SSO
        self.login(srvHardwareUri)

        managers = self.do_get('/redfish/v1/Managers')

        for manager in managers["Members"]:
            resp = self.do_get(manager['@odata.id'])
            if not resp["VirtualMedia"]:
                continue

            vmediaUri = resp["VirtualMedia"]["@odata.id"]
            resp = self.do_get(vmediaUri)
            for member in resp["Members"]:
                resp = self.do_get(member['@odata.id'])
                logging.debug("##############")
                logging.debug(resp['MediaTypes'])

                resp = self.do_post(resp['Actions']['#VirtualMedia.EjectMedia']['target'], {})
        return resp

    ##################################
    # get the host ip 
    ##################################
    def get_host_ip(self, srvHardwareUri, mac, timeout):
        #Login to iLO using SSO
        self.login(srvHardwareUri)

        logging.info("\nWaiting to get Host IP...")
        systems = self.do_get('/redfish/v1/Systems')

        interface_uri = ""
        for system in systems["Members"]:
            response = self.do_get(system["@odata.id"])
            EthInterfaces = self.do_get(response['EthernetInterfaces']['@odata.id'])
            while True:
                try:
                    if not EthInterfaces["Members"]:
                        time.sleep(10)
                    elif EthInterfaces["Members"]:
                        break
                except KeyError:
                    time.sleep(10)
                EthInterfaces = self.do_get(response['EthernetInterfaces']['@odata.id'])

            timeout = time.time() + 60*timeout
            while time.time() < timeout:
                for EthInterface in EthInterfaces["Members"]:
                    try:
                        interface = self.do_get(EthInterface["@odata.id"])
                    except:
                        continue
        
                    if interface:
                        if interface.get('MACAddress') and interface.get('IPv4Addresses'):
                            if interface['MACAddress']:
                                if interface['MACAddress'].lower() == mac.lower():
                                    ipaddr = interface['IPv4Addresses'][0].get('Address')
                                    if ipaddr:
                                        return ipaddr
                    time.sleep(20)
        return ""











    def changeTemporaryBootOrder(self, boottarget="BiosSetup"):

        systems_members_uri = None
        systems_members_response = None

        resourceRes = self.do_get("/redfish/v1/resourcedirectory")
        resourceInstances = resourceRes["Instances"]

        for instance in resourceInstances:
            if '#ComputerSystem.' in instance['@odata.type']:
                systems_members_uri = instance['@odata.id']
                systems_members_response = self.do_get(systems_members_uri)

        if systems_members_response:
            logging.debug("\n\nShowing bios attributes before changes:\n\n")
            logging.debug(json.dumps(systems_members_response['Boot'], indent=4, sort_keys=True))
        body = {'Boot': {'BootSourceOverrideTarget': boottarget}}
        logging.debug("body: ")
        logging.debug(body)
        resp = self.do_patch(systems_members_uri, body=body)
        logging.debug("redfishObj.patch returned: ")
        logging.debug(resp)




    #######################################
    # Function to get iLO power state
    #######################################
    def getPowerState(self):
        iloInfo = self.do_get('/redfish/v1/Systems/1/')
        logging.debug(iloInfo['PowerState'])
        return iloInfo['PowerState']

    #######################################
    # Function to set iLO power state
    #######################################
    def setPowerState(self, state):
        iloInfo = self.do_get('/redfish/v1/Systems/1/')
        resetBody = {}
        if state.lower() == "on":
            resetBody = {"ResetType": self.POWER_ON}

        elif state.lower() == "off":
            resetBody = {"ResetType": self.POWER_OFF}

        elif state.lower() == "push":
            resetBody = {"ResetType": self.POWER_PUSH}

        elif state.lower() == "force-reset":
            resetBody = {"ResetType": self.POWER_RESET}

        elif state.lower() == "graceful-shutdown":
            resetBody = {"ResetType": self.POWER_GRACEFUL_SHUTDOWN}

        response = self.do_post("/redfish/v1/systems/1/Actions/ComputerSystem.Reset", body=resetBody)



    #######################################
    # Function to ensure iLO power state
    #
    # If the expected power state is different
    # from iLO server power state, function will
    # ensure to set the expected power state
    #
    # else, will skip
    #######################################
    def ensurePowerState(self, expectedState):
        state = self.getPowerState()

        if state.lower() != expectedState.lower():
            self.setPowerState(expectedState)

    #######################################
    # Function to reset iLO power state
    #
    # If the server state is
    # - Off, func will power on
    # - on, func will force reset
    #######################################
    def resetPowerState(self):
        if self.getPowerState().lower() == "off":
            self.setPowerState("on")
        else:
            self.setPowerState("force-reset")


    #######################################
    # Function to wait for BIOS post to
    # be completed
    #######################################
    def waitForBiosPost(self):
        # Wait for BIOS to be unlocked
        sleepTime = 10
        counter = 25
        while self.isBiosLock():
            counter = counter - 1
            time.sleep(sleepTime)

            if counter == 0:
                # Power off the node and raise Exception
                self.ensurePowerState("graceful-shutdown")
                logging.exception(errorMessage + " : Timeout reach while waiting for BIOS")
                raise Exception(errorMessage + " : Timeout reach while waiting for BIOS")

        # Sleep additional 2 seconds, just to make sure BIOS
        # updates reflect in redfish
        time.sleep(20)

    #######################################

    #######################################
    # Function to get ilO Post State
    #
    # This function gets the POST state of iLO
    #
    # Post States: Null Unknown Reset PowerOff
    #   InPost InPostDiscoveryComplete FinishedPost
    #######################################
    def getPostState(self):
        iloInfo = self.do_get('/redfish/v1/Systems/1/')
        logging.debug(iloInfo['Oem']['Hpe']['PostState'])
        return iloInfo['Oem']['Hpe']['PostState']

    #######################################
    # This function check the right time to
    # updates BIOS
    #
    # Returns true if the post state is
    #   'InPostDiscoveryComplete', 'FinishedPost'
    #
    # Returns False in all other cases
    #######################################
    def isBiosLock(self):
        postState = self.getPostState()
        logging.debug("Post State : {}".format(postState))
        if postState.upper() in ["INPOSTDISCOVERYCOMPLETE", "FINISHEDPOST"]:
            return False

        return True

