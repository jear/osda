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
#import redfish
import redfish
import time
from redfish.rest.v1 import ServerDownOrUnreachableError
import logging

# Redfish debug logs has bunch of unintended info which
# clutters the log file. Setting the default to 'INFO''
# for now.
#
# TODO: To move this to server code based on user request
logging.getLogger("redfish").setLevel(logging.INFO)

#######################################
# Class for iLO operations 
#######################################

class ILORedfish(object):

    # FIXED REST API based values for POWER
    POWER_OFF = "ForceOff"
    POWER_ON  = "On"
    POWER_RESET = "ForceRestart"
    POWER_PUSH = "PushPowerButton"
    POWER_GRACEFUL_SHUTDOWN = "GracefulShutdown"

    def __init__(self, iloIp, iloUser, iloPassword):
        self.iloUrl = "https://" + iloIp
        self.iloUser = iloUser
        self.iloPassword = iloPassword
        self.phyDrives = None
        self.logicalDrives = None
        self.redfishObj = self.login()

    #######################################
    # Login to the ILO
    #######################################
    def login(self):
        logging.info("ILORedfish: login: " + self.iloUrl)
        try:
            redfishObj = redfish.redfish_client(base_url=self.iloUrl, username=self.iloUser, password=self.iloPassword)
            #redfishObj = LegacyRestClient(base_url=self.iloUrl, username=self.iloUser, password=self.iloPassword)
            redfishObj.login()
        except ServerDownOrUnreachableError as excp:
            return "ERROR: server not reachable or does not support RedFish.\n"
        return redfishObj

    #######################################
    # Logout 
    #######################################
    def logout(self, redfishObj):
        self.redfishObj.logout()
        return "Logout success"

    #######################################
    # Function for get the NetworkAdaperts
    #######################################
    def getILONWAdapters(self):
        logging.info("getILONWAdapters")
        #redfishObj = self.login()
        #Gen9 change
        NetworkAdapters = self.redfishObj.get("/redfish/v1/Systems/1/NetworkAdapters")
        logging.debug("getILONWAdapters 1")
        networkAdaptersList = []
        for member in NetworkAdapters.dict['Members']:
            adapter = self.redfishObj.get(member["@odata.id"])
            logging.debug(adapter)
            if "PhysicalPorts" in adapter.dict and len(adapter.dict["PhysicalPorts"]) > 0:
               adapterItem = dict()
               adapterItem['adapterId'] = adapter.dict["Id"]
               adapterItem['adapterName'] = adapter.dict["Name"]
               adapterItem['adapterType'] = "NIC"
               networkPorts = []
               for port in adapter.dict["PhysicalPorts"]:
                   macAddress = port["MacAddress"]
                   status = ""
                   if "Status" in port:
                        status = port["Status"]["Health"]
                   else:
                        status = "Unknown"
                   networkPorts.append({"macAddress": macAddress, "structuredName": port['Oem']['Hp']["StructuredName"], "linkStatus": status})

               adapterItem['networkPorts'] = networkPorts
               networkAdaptersList.append(adapterItem)
               #networkAdaptersList.append({"adapterName" : adapterName, "adapterType": adapterType, "structuredName": structuredName, "networkPorts": networkPorts})
        #self.logout(redfishObj)



        logging.debug("##################output")
        logging.debug(json.dumps(networkAdaptersList))
        return networkAdaptersList

    #######################################
    # Function for get the Storage details
    #######################################
    def getILOStorageDrives(self):
        #redfishObj = self.login()
        storageDetails = []
        arrayResponse = self.redfishObj.get("/redfish/v1/Systems/1/SmartStorage/ArrayControllers")
        for ArrayController in arrayResponse.dict["Members"]:
            driveResponse = self.redfishObj.get(ArrayController["@odata.id"])
            logging.debug(driveResponse)
            if "LogicalDrives" in driveResponse.dict['Links']:
                logicalDrives =  self.redfishObj.get(driveResponse.dict['Links']['LogicalDrives']['@odata.id'])
                if logicalDrives.dict["Members@odata.count"] > 0:
                    for drive in logicalDrives.dict["Members"]:
                        logicalDrive = self.redfishObj.get(drive["@odata.id"])
                        capacityGB = int(logicalDrive.dict["CapacityMiB"])/1024
                        faultTolerance = "RAID " + str(logicalDrive.dict["Raid"])
                        driveName =  logicalDrive.dict["LogicalDriveName"]
                        logicalDriveNumber =  logicalDrive.dict["LogicalDriveNumber"]
                        mediaType =  ""
                        VolumeUniqueIdentifier = logicalDrive.dict['VolumeUniqueIdentifier']
                        storageDetails.append({"logicalDriveNumber": logicalDriveNumber, "driveType" : "Logical", "mediaType": mediaType, "capacityGB": capacityGB, 'driveID' : VolumeUniqueIdentifier,  "faultTolerance": faultTolerance})

        return storageDetails

    #######################################
    # Class for iLO operations             ------   Testing in-progress 
    #######################################
    def mountVirtualMedia(self, mediaUrl, mediaType, bootOnNextServerReset=False):


        logging.info("mountVirtualMedia: mediaUrl: " + mediaUrl)

        #redfishObj = self.login()
        resourceRes = self.redfishObj.get("/redfish/v1/resourcedirectory")
        resourceInstances = resourceRes.dict["Instances"]
        virtualMediaUri = None
        virtualMediaResponse = []
        for instance in resourceInstances:
            logging.debug(instance)
            # Use Resource directory to find the relevant URI
            if '#VirtualMediaCollection.' in instance['@odata.type']:
                virtualMediaUri = instance['@odata.id']
                break


        logging.debug("virtualMediaUri: " + virtualMediaUri)
        if virtualMediaUri:
            virtualMediaResponse = self.redfishObj.get(virtualMediaUri)
            logging.debug(type(virtualMediaResponse))
            logging.debug(virtualMediaResponse)
            for virtualMediaSlot in virtualMediaResponse.obj['Members']:
                data = self.redfishObj.get(virtualMediaSlot['@odata.id'])
                logging.debug(data)
                logging.debug(mediaType )
                if mediaType in data.dict['MediaTypes']:
                    virtualMediaMountUri = data.obj['Oem']['Hp']['Actions']['#HpiLOVirtualMedia.InsertVirtualMedia']['target']
                    postBody = {"Image": mediaUrl}
                    virtualMediaEjectUri = data.obj['Oem']['Hp']['Actions']['#HpiLOVirtualMedia.EjectVirtualMedia']['target']

                    if mediaUrl:
                        try:
                            self.redfishObj.post(virtualMediaEjectUri, body={})
                            self.redfishObj.post(virtualMediaMountUri, body=postBody)
                        except Exception as err:
                            logging.exception("Unable to mount: {}".format(err))
                            return ({ "result" : "Unable to mount", "error" : err })
                        if bootOnNextServerReset is True:
                            patchBody = {}
                            patchBody["Oem"] = {"Hp": {"BootOnNextServerReset": \
                                                     bootOnNextServerReset}}
                            bootResp = self.redfishObj.patch(data.obj['@odata.id'], body=patchBody)
                            if not bootResp.status == 200:
                                #logging.exception("Failed to reset the server. Ensure the server is in Power OFF state before deployment")
                                #raise Exception("Failed to reset the server. Ensure the server is in Power OFF state before deployment.")
                                logging.exception("Failed to change one-time boot order to boot into " + mediaType)
                                raise Exception("Failed to change one-time boot order to boot into " + mediaType)


        return

    #######################################
    # Function to unmounts all the virtual
    # media drives mounted to the iLO
    #######################################
    def umountAllMediaDrives(self):
        logging.debug("umountAllMediaDrives: Begin")

        resourceRes = self.redfishObj.get("/redfish/v1/resourcedirectory")
        resourceInstances = resourceRes.dict["Instances"]
        virtualMediaUri = None
        if not resourceInstances:
            # if we do not have a resource directory or want to force it's non use to find the
            # relevant URI
            managersUri = self.redfishObj.root.obj['Managers']['@odata.id']
            managersResponse = self.redfishObj.get(managersUri)
            managersMembersUri = next(iter(managersResponse.obj['Members']))['@odata.id']
            managersMembersResponse = self.redfishObj.get(managersMembersUri)
            virtualMediaUri = managersMembersResponse.obj['VirtualMedia']['@odata.id']
        else:
            for instance in resourceInstances:
                # Use Resource directory to find the relevant URI
                if '#VirtualMediaCollection.' in instance['@odata.type']:
                    virtualMediaUri = instance['@odata.id']
        if virtualMediaUri:
            # /redfish/v1/Managers/1/VirtualMedia
            virtualMediaResponse = self.redfishObj.get(virtualMediaUri)
            for virtualMediaSlot in virtualMediaResponse.obj['Members']:
                data = self.redfishObj.get(virtualMediaSlot['@odata.id'])
                virtualMediaEjectUri = data.obj['Actions']['#VirtualMedia.EjectMedia']['target']

                try:
                    logging.debug("Umounting virtual media uri : {}".format(virtualMediaEjectUri))
                    self.redfishObj.post(virtualMediaEjectUri, body={})
                except Exception as err:
                    logging.exception("Cleanup failed: Unable to unmount media: {}".format(err))
        else:
            logging.debug("umountAllMediaDrives: No virtual media found, skipping")


    # This function supports boot device of type logical drive with RAID using local drives
    def modifyBootOrder(self, drive):
        logging.info("modifyBootOrder: drive: " + str(drive))

        #redfishObj = self.login()



        response = self.redfishObj.get("/redfish/v1/Systems/1/BIOS/Boot/Settings/")
        #print(response)
        logging.debug("####################")
        logging.debug(response.obj['PersistentBootConfigOrder'])
        bootOrder = response.obj['PersistentBootConfigOrder']
        logging.debug("####################")
        logging.debug(response.obj)
        logging.debug(response.obj['BootSources'])
        bootSources = response.obj['BootSources']


        # First find the matching boot source based on the OS boot drive
        # the matching criteria is, if requested OS drive RAID type matches one of the boot sources
        # and if there are multiple boot sources matching RAID type then look for logical volume number match 
        raidTypeMatch = False
        matchedBootSourceString = ""
 
        for bootSource in bootSources:
            logging.debug(bootSource)
            # HPE DL Gen9, boot source has entries with Logical Drive name like "Logical Drive 01"
            # But the ilo returns only a numeric for logical drive identifier
            # So look for matching logical drive number 
            logicalDriveName = "Logical Drive " + str(drive['logicalDrive']['logicalDriveNumber'])
            logging.debug("logical drive is: " + logicalDriveName)
            logging.debug("bootSource['BootString'] drive is: " + bootSource['BootString'])
            if logicalDriveName in bootSource['BootString']:
                logging.debug("################## Match found ")
                # If here then both RAID type and logical drive name are matching so this bootSource must be better match
                matchedBootSourceString = bootSource['StructuredBootString']

#            if drive['faultTolerance'].replace(" ", "") in bootSource['BootString']:
#                print("Found!!") 
#                print(str(bootSource))
#                if raidTypeMatch == False:
#                    raidTypeMatch = True
#                    matchedBootSourceString = bootSource['StructuredBootString']
#                else:
#                    print("Duplicate found so try another check")
#                    # Looks like there are mode than 2 logical drives matching RAID mode
#                    # So look for matching logical drive number 
#                    logicalDriveName = "Logical Drive " + str(drive['logicalDriveNumber'])
#                    print("logical drive is: " + logicalDriveName)
#                    print("bootSource['BootString'] drive is: " + bootSource['BootString'])
#                    if logicalDriveName in bootSource['BootString']:
#                        print("##################Match found in duplicates")
#                        # If here then both RAID type and logical drive name are matching so this bootSource must be better match
#                        matchedBootSourceString = bootSource['StructuredBootString']


        logging.info("Matching boot source is: " + matchedBootSourceString)
        bootOrder = response.obj['PersistentBootConfigOrder']
        if matchedBootSourceString == "":
            logging.exception("Unable to find matching boot sources for the requested OS boot device: {}".format(drive))
            raise Exception("Unable to find matching boot sources for the requested OS boot device: " + str(drive))

        # build new boot order first adding the matching boot string to top of the list
        newBootOrder = [matchedBootSourceString]
        for bootEntry in bootOrder:
            if bootEntry != matchedBootSourceString:
                newBootOrder.append(bootEntry)

        # now we have the modified boot order in newBootOrder
        # Now update iLO with new boot order
        body = dict()
        body["PersistentBootConfigOrder"] = newBootOrder
        #body["DefaultBootOrder"] = newBootOrder
        #body = {'DefaultBootOrder': newBootOrder}
        resp = self.redfishObj.patch("/redfish/v1/Systems/1/BIOS/Boot/Settings/", body=body)
        if resp.status != 200:
            logging.info(resp.status)
            logging.error(json.dumps(resp.obj['error']['@Message.ExtendedInfo'], indent=4, sort_keys=True))
            logging.exception(json.dumps(resp.obj['error']['@Message.ExtendedInfo'], indent=4, sort_keys=True))
            raise Exception("Failed to update boot-order in the iLO")
        else:
            logging.info("Boot order updated successfully to boot from the choosen logical drive")
            logging.info("New BOOT order: {}".format(newBootOrder))


    def changeTemporaryBootOrder(self, boottarget="BiosSetup"):

        systems_members_uri = None
        systems_members_response = None

        #resource_instances = resourceRes = self.redfishObj.get("/redfish/v1/resourcedirectory")
        resourceRes = self.redfishObj.get("/redfish/v1/resourcedirectory")
        resourceInstances = resourceRes.dict["Instances"]

        for instance in resourceInstances:
            if '#ComputerSystem.' in instance['@odata.type']:
                systems_members_uri = instance['@odata.id']
                systems_members_response = self.redfishObj.get(systems_members_uri)

        if systems_members_response:
            logging.debug("\n\nShowing bios attributes before changes:\n\n")
            logging.debug(json.dumps(systems_members_response.dict.get('Boot'), indent=4, sort_keys=True))
        body = {'Boot': {'BootSourceOverrideTarget': boottarget}}
        logging.debug("body: ")
        logging.debug(body)
        resp = self.redfishObj.patch(systems_members_uri, body=body)
        logging.debug("redfishObj.patch returned: ")
        logging.debug(resp.status)

        #If iLO responds with soemthing outside of 200 or 201 then lets check the iLO extended info
        #error message to see what went wrong
        if resp.status == 400:
            try:
                logging.debug(json.dumps(resp.obj['error']['@Message.ExtendedInfo'], indent=4, sort_keys=True))
            except Exception as excp:
                logging.error("Setting the boot parameter BootSourceOverrideTarget returned HTTP status 400. Ignoring...")

        elif resp.status != 200:
            logging.error("Setting the boot parameter BootSourceOverrideTarget failed. Ignoring...")
        else:
            logging.debug("\nSuccess!\n")
            logging.debug(json.dumps(resp.dict, indent=4, sort_keys=True))
            if systems_members_response:
                logging.debug("\n\nShowing boot override target:\n\n")
                logging.debug(json.dumps(systems_members_response.dict.get('Boot'), indent=4, sort_keys=True))


    #######################################
    # Function to reboot the server
    #######################################
    def rebootServer(self):
        #redfishObj = self.login()
        resourceRes = self.redfishObj.get("/redfish/v1/resourcedirectory")
        resourceInstances = resourceRes.dict["Instances"]
        for instance in resourceInstances:
            #Use Resource directory to find the relevant URI
            if '#ComputerSystem.' in instance['@odata.type']:
                systems_members_uri = instance['@odata.id']
                systems_members_response = self.redfishObj.get(systems_members_uri)

        if systems_members_response:
            system_reboot_uri = systems_members_response.obj['Actions']['#ComputerSystem.Reset']['target']
            if systems_members_response.obj['PowerState'] == "On":
                logging.error("CRITICAL: Found the server in ON state. CANNOT PROCEED WITH DEPLOYMENT")
            elif systems_members_response.obj['PowerState'] == "Off":
                logging.info("Found the server in OFF state. PROCEEDING WITH DEPLOYMENT")

            try:
                body = dict()
                body['ResetType'] = "On"
                self.redfishObj.post(system_reboot_uri, body=body)
            except Exception as err:
                logging.exception("Failed to restart : {}".format(err))
                return ("Failed to restart", err)
        #self.logout(redfishObj)
        return "Restarted"

    #######################################
    # Function to get iLO power state
    #######################################
    def getPowerState(self):
        iloInfo = self.redfishObj.get('/redfish/v1/Systems/1/')
        return iloInfo.obj['PowerState']

    #######################################
    # Function to set iLO power state
    #######################################
    def setPowerState(self, state):
        iloInfo = self.redfishObj.get('/redfish/v1/Systems/1/')
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

        response = self.redfishObj.post("/redfish/v1/systems/1/Actions/ComputerSystem.Reset", body=resetBody)
        if response.status != 200:
            logging.exception("Failed to reset power state to {state}: {msg}".format(state=state, msg=response.text))
            raise Exception("Failed to reset power state to {state}: {msg}".format(state=state, msg=response.text))


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
    # Function to read all physical drives of smart array controllers
    #
    # Populates class attribute 'phyDrives' with list of physical disks
    #######################################
    def physicalDrives(self):
        self.phyDrives = []
        logging.info("Get the list of physical drives")
        for controller in self.redfishObj.get('/redfish/v1/Systems/1/SmartStorage/ArrayControllers').obj["Members"]:
            smartArrayControllerInfo = self.redfishObj.get(controller["@odata.id"] + "/DiskDrives")
            for disk in smartArrayControllerInfo.obj["Members"]:
                driveInfo = {}
                diskInfoObj = self.redfishObj.get(disk["@odata.id"])
                driveInfo["InterfaceType"] = diskInfoObj.obj["InterfaceType"]
                driveInfo["Location"] = diskInfoObj.obj["Location"]
                driveInfo["MediaType"] = diskInfoObj.obj["MediaType"]
                driveInfo["CapacityGB"] = diskInfoObj.obj["CapacityGB"]
                driveInfo["Health"] = diskInfoObj.obj["Status"]["Health"]
                driveInfo["State"] = diskInfoObj.obj["Status"]["State"]
                driveInfo["DiskDriveUse"] = diskInfoObj.obj["DiskDriveUse"]

                self.phyDrives.append(driveInfo)
        return self.phyDrives

    #######################################
    # Function to check to get logical drive of a given physical disk
    # 
    # Returns logical drive or None
    #######################################
    def getLogicalDriveFromDisk(self, logicalDriveList, phydrive):
        lgDrive = next((x for x in logicalDriveList if phydrive in x["dataDrives"]), None)
        return lgDrive


    #######################################
    # Function to get logical drives
    #
    # This function re-read all the logical drives
    # even if the logicalDrives are available
    #
    # Populates class attribute 'logicalDrives' with list of logical drives
    #######################################
    def getLogicalDrives(self):
        smartConfigInfo = self.redfishObj.get('/redfish/v1/Systems/1/smartstorageconfig/')
        self.logicalDrives = []
        for lgDrive in smartConfigInfo.obj["LogicalDrives"]:
            drive ={}
            drive["logicalDriveNumber"] = lgDrive["LogicalDriveNumber"]
            drive["dataDrives"] = lgDrive["DataDrives"]
            drive["capacityGiB"] = lgDrive["CapacityGiB"]
            drive["raidLevel"] = lgDrive["Raid"]
            drive["driveID"] = lgDrive["VolumeUniqueIdentifier"]

            self.logicalDrives.append(drive)
        return self.logicalDrives

    #######################################
    # Function to get ilO Post State
    #
    # This function gets the POST state of iLO
    #
    # Post States: Null Unknown Reset PowerOff
    #   InPost InPostDiscoveryComplete FinishedPost 
    #######################################
    def getPostState(self):
        iloInfo = self.redfishObj.get('/redfish/v1/Systems/1/')
        return iloInfo.obj['Oem']['Hpe']['PostState']

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

if __name__ == '__main__':

    logging.basicConfig( level=logging.DEBUG)
   
    SYSTEM_URL = "10.188.1.239"
    LOGIN_ACCOUNT = "v0232usradmin"
    LOGIN_PASSWORD = "HP!nvent123"
    A = ILORedfish(SYSTEM_URL, LOGIN_ACCOUNT, LOGIN_PASSWORD)
    #A.getILONWAdapters()
    A.getILOStorageDrives()

    #"BootSourceOverrideTarget@Redfish.AllowableValues": [
    #  "None",
    #  "Pxe",
    #  "Floppy",
    #  "Cd",
    #  "Usb",
    #  "Hdd",
    #  "BiosSetup",
    #  "Utilities",
    #  "Diags",
    #  "UefiTarget",
    #  "SDCard",
    #  "UefiHttp"
    #],
    #A.change_temporary_boot_order()


    quit()





    drive = {'logicalDriveNumber': 3, 'faultTolerance': 'RAID 1', 'driveID': '600508B1001CAA4ECFD2FBCFC754E865'}
    A.modifyBootOrder(drive)
    #print (A.getILOStorageDrives())

    #print (A.mountVirtualMedia("http://10.188.210.16/RHEL-7.6-20181010.0-Server-x86_64-dvd1.iso", "CD", bootOnNextServerReset=True))
    #print (A.mountVirtualMedia("http://10.188.210.16/rhelKsImage1.img", "USBStick"))


