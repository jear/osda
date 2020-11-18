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
            redfish_obj = redfish.redfish_client(base_url=self.iloUrl, username=self.iloUser, password=self.iloPassword)
            redfish_obj.login()
        except ServerDownOrUnreachableError as excp:
            return "ERROR: server not reachable or does not support RedFish.\n"
        return redfish_obj

    #######################################
    # Logout 
    #######################################
    def logout(self):
        self.redfishObj.logout()
        return "Logout success"

    #######################################
    # Function for get the NetworkAdaperts
    #######################################
    def getILONWAdapters(self):
        logging.info("getILONWAdapters")
        #redfishObj = self.login()
        network_adapters = self.redfishObj.get("/redfish/v1/Systems/1/BaseNetworkAdapters")
        logging.debug("getILONWAdapters 1")
        network_adapters_list = []
        for member in network_adapters.dict['Members']:
            logging.debug("getILONWAdapters r21")
            adapter = self.redfishObj.get(member["@odata.id"])
            logging.debug("!!!!!!!!!!!!!!!!!!!!!!!!!!!adapter")
            logging.debug(adapter)
            if len(adapter.dict["FcPorts"]) > 0:
                adapter_item = dict()
                adapter_item['adapterId'] = adapter.dict["Id"]
                adapter_item['adapterName'] = adapter.dict["Name"]
                adapter_item['networkPorts'] = adapter.dict["FcPorts"]
                adapter_item['adapterType'] = "HBA"
                adapter_item['structuredName'] = adapter.dict["StructuredName"]
                network_adapters_list.append(adapter_item)
            elif len(adapter.dict["PhysicalPorts"]) > 0:
               adapter_item = dict()
               adapter_item['adapterId'] = adapter.dict["Id"]
               adapter_item['adapterName'] = adapter.dict["Name"]
               adapter_item['adapterType'] = "NIC"
               adapter_item['structuredName'] = adapter.dict["StructuredName"]
               network_ports = []
               for port in adapter.dict["PhysicalPorts"]:
                   mac_address = port["MacAddress"]
                   network_ports.append({"macAddress": mac_address, "linkStatus": port['LinkStatus']})

               adapter_item['networkPorts'] = network_ports
               network_adapters_list.append(adapter_item)

        logging.debug("##################output")
        logging.debug(json.dumps(network_adapters_list))
        return network_adapters_list

    #######################################
    # Function for get the Storage details
    #######################################
    def getILOStorageDrives(self):
        storage_details = []
        arrayResponse = self.redfishObj.get("/redfish/v1/Systems/1/SmartStorage/ArrayControllers")
        for array_controller in arrayResponse.dict["Members"]:
            drive_response = self.redfishObj.get(array_controller["@odata.id"])
            if "LogicalDrives" in drive_response.dict['Links']:
                for drive in (self.redfishObj.get(drive_response.dict['Links']['LogicalDrives']['@odata.id'])).dict["Members"]:
                    logical_drive = self.redfishObj.get(drive["@odata.id"])
                    capacity_gb = int(logical_drive.dict["CapacityMiB"])/1024
                    fault_tolerance = "RAID " + str(logical_drive.dict["Raid"])
                    driveName = logical_drive.dict["LogicalDriveName"]
                    logical_drive_number =  logical_drive.dict["LogicalDriveNumber"]
                    media_type = logical_drive.dict["MediaType"]
                    volume_unique_identifier = logical_drive.dict['VolumeUniqueIdentifier']
                    storage_details.append({"logicalDriveNumber": logical_drive_number, "driveType" : "Logical", "mediaType": media_type, "capacityGB": capacity_gb, 'driveID' : volume_unique_identifier,  "faultTolerance": fault_tolerance})
            if "PhysicalDrives" in drive_response.dict['Links']:
                for drive in (self.redfishObj.get(drive_response.dict['Links']['PhysicalDrives']['@odata.id'])).dict["Members"]:
                    physical_drive = self.redfishObj.get(drive["@odata.id"])
                    capacity_gb = physical_drive.dict["CapacityGB"]
                    name = physical_drive.dict["Name"]
                    location = physical_drive.dict["Location"]
                    media_type = physical_drive.dict["MediaType"]
                    location_format = physical_drive.dict["LocationFormat"]
                    storage_details.append({"driveName": name, "driveType" : "physical", "location": location,
                                            "LocationFormat": location_format,
                                            "mediaType": media_type, "capacityGB": capacity_gb})
        return storage_details

    #######################################
    # Class for iLO operations             ------   Testing in-progress 
    #######################################
    def mountVirtualMedia(self, media_url, media_type, bootOnNextServerReset=False):
        logging.info("mountVirtualMedia: mediaUrl: " + media_url)
        resource_res = self.redfishObj.get("/redfish/v1/resourcedirectory")
        resource_instances = resource_res.dict["Instances"]
        virtual_media_uri = None
        virtual_media_response = []
        disable_resource_dir = False
        if disable_resource_dir or not resource_instances:
            # if we do not have a resource directory or want to force it's non use to find the
            # relevant URI
            managers_uri = self.redfishObj.root.obj['Managers']['@odata.id']
            managers_response = self.redfishObj.get(managers_uri)
            managers_members_uri = next(iter(managers_response.obj['Members']))['@odata.id']
            managers_members_response = self.redfishObj.get(managers_members_uri)
            virtual_media_uri = managers_members_response.obj['VirtualMedia']['@odata.id']
        else:
            for instance in resource_instances:
                # Use Resource directory to find the relevant URI
                if '#VirtualMediaCollection.' in instance['@odata.type']:
                    virtual_media_uri = instance['@odata.id']
        if virtual_media_uri:
            virtual_media_response = self.redfishObj.get(virtual_media_uri)
            for virtual_media_slot in virtual_media_response.obj['Members']:
                data = self.redfishObj.get(virtual_media_slot['@odata.id'])
                if media_type in data.dict['MediaTypes']:
                    virtual_media_mount_uri = data.obj['Actions']['#VirtualMedia.InsertMedia']['target']
                    postBody = {"Image": media_url}
                    virtualMediaEjectUri = data.obj['Actions']['#VirtualMedia.EjectMedia']['target']

                    if media_url:
                        try:
                            self.redfishObj.post(virtualMediaEjectUri, body={})
                            self.redfishObj.post(virtual_media_mount_uri, body=postBody)
                        except Exception as err:
                            logging.exception("Unable to mount: {}".format(err))
                            return { "result": "Unable to mount", "error" : err }
                        if bootOnNextServerReset is True:
                            patch_body = {"Oem": {"Hpe": {"BootOnNextServerReset":
                                                              bootOnNextServerReset}}}
                            boot_resp = self.redfishObj.patch(data.obj['@odata.id'], body=patch_body)
                            if not boot_resp.status == 200:
                                #logging.exception("Failed to reset the server. Ensure the server is in Power OFF state before deployment")
                                #raise Exception("Failed to reset the server. Ensure the server is in Power OFF state before deployment.")
                                logging.exception("Failed to change one-time boot order to boot into " + media_type)
                                raise Exception("Failed to change one-time boot order to boot into " + media_type)
        return


    #######################################
    # Function to unmounts all the virtual
    # media drives mounted to the iLO
    #######################################
    def umountAllMediaDrives(self):
        logging.debug("umountAllMediaDrives: Begin")

        resource_res = self.redfishObj.get("/redfish/v1/resourcedirectory")
        resource_instances = resource_res.dict["Instances"]
        virtual_media_uri = None
        if not resource_instances:
            # if we do not have a resource directory or want to force it's non use to find the
            # relevant URI
            managers_uri = self.redfishObj.root.obj['Managers']['@odata.id']
            managers_response = self.redfishObj.get(managers_uri)
            managers_members_uri = next(iter(managers_response.obj['Members']))['@odata.id']
            managers_members_response = self.redfishObj.get(managers_members_uri)
            virtual_media_uri = managers_members_response.obj['VirtualMedia']['@odata.id']
        else:
            for instance in resource_instances:
                # Use Resource directory to find the relevant URI
                if '#VirtualMediaCollection.' in instance['@odata.type']:
                    virtual_media_uri = instance['@odata.id']
        if virtual_media_uri:
            # /redfish/v1/Managers/1/VirtualMedia
            virtual_media_response = self.redfishObj.get(virtual_media_uri)
            for virtual_media_slot in virtual_media_response.obj['Members']:
                data = self.redfishObj.get(virtual_media_slot['@odata.id'])
                virtual_media_eject_uri = data.obj['Actions']['#VirtualMedia.EjectMedia']['target']

                try:
                    logging.debug("Umounting virtual media uri : {}".format(virtual_media_eject_uri))
                    self.redfishObj.post(virtual_media_eject_uri, body={})
                except Exception as err:
                    logging.exception("Cleanup failed: Unable to unmount media: {}".format(err))
        else:
            logging.debug("umountAllMediaDrives: No virtual media found, skipping")


    # This function supports boot device of type logical drive with RAID using local drives
    def modifyBootOrder(self, drive):
        logging.info("modifyBootOrder: drive: " + str(drive))

        # Sometimes Boot Order/Sources may not show the newly created logical drive resulting in failure to modify boot-order
        # If the requested logical drive is not found in the boot sources then boot the server to ensure its updated with new logical drives
        attempts = 2
        while attempts:

            attempts = attempts -1

            response = self.redfishObj.get("/redfish/v1/Systems/1/BIOS/Boot/Settings/")
            logging.debug("####################")
            logging.debug(response.obj['PersistentBootConfigOrder'])
            boot_order = response.obj['PersistentBootConfigOrder']
            logging.debug("####################")
            boot_sources = response.obj['BootSources']

            # First find the matching boot source based on the OS boot drive
            # the matching criteria is, if requested OS drive RAID type matches one of the boot sources
            # and if there are multiple boot sources matching RAID type then look for logical volume number match 
            matched_boot_source_string = ""
 
            for boot_source in boot_sources:
                # HPE DL Gen10, boot source has entries with Logical Drive name like "Logical Drive 2"
                # For eg. 'BootString': 'Embedded RAID 1 : HPE Smart Array P816i-a SR Gen10 - 931.4 GiB, RAID1 Logical Drive 2(Target:0, Lun:1
                # But the ilo returns only a numeric for logical drive identifier
                # So look for matching logical drive number 
                logical_drive_name = "Logical Drive " + str(drive['logicalDrive']['logicalDriveNumber'])
                logging.debug("logical drive is: " + logical_drive_name)
                logging.debug("bootSource['BootString'] drive is: " + boot_source['BootString'])
                if logical_drive_name in boot_source['BootString']:
                    logging.debug("################## Match found ")
                    # If here then both RAID type and logical drive name are matching so this bootSource must be better match
                    matched_boot_source_string = boot_source['StructuredBootString']


            logging.info("Matching boot source is: " + matched_boot_source_string)
            boot_order = response.obj['PersistentBootConfigOrder']
            if matched_boot_source_string == "":
                logging.warning("Unable to find matching boot sources for the requested OS boot device: {}".format(drive))
                if attempts > 0:
                    logging.warning("#####################################")
                    logging.warning("Making another attempt after booting the server for syncing iLO with Storage Controller")
                    # Reset the server to reflect the changes
                    self.normalizeConfig()
                    self.ensurePowerState("graceful-shutdown")
                else:
                    logging.exception("Unable to find matching boot sources for the requested OS boot device: {}".format(drive))
                    raise Exception("Unable to find matching boot sources for the requested OS boot device: " + str(drive))
            else:
                break
        # End of while loop

        # build new boot order first adding the matching boot string to top of the list
        new_boot_order = [matched_boot_source_string]
        for boot_entry in boot_order:
            if boot_entry != matched_boot_source_string:
                new_boot_order.append(boot_entry)

        # now we have the modified boot order in newBootOrder
        # Now update iLO with new boot order
        body = dict()
        body["PersistentBootConfigOrder"] = new_boot_order
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
            logging.info("New BOOT order: {}".format(new_boot_order))

    def changeTemporaryBootOrder(self, boottarget="BiosSetup"):

        logging.info("changeTemporaryBootOrder: ")

        systems_members_uri = None
        systems_members_response = None

        #resource_instances = resourceRes = self.redfishObj.get("/redfish/v1/resourcedirectory")
        resource_res = self.redfishObj.get("/redfish/v1/resourcedirectory")
        resource_instances = resource_res.dict["Instances"]

        for instance in resource_instances:
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
        resource_res = self.redfishObj.get("/redfish/v1/resourcedirectory")
        resource_instances = resource_res.dict["Instances"]
        for instance in resource_instances:
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
        logging.info("getPowerState: START")
        ilo_info = self.redfishObj.get('/redfish/v1/Systems/1/')

        #logging.debug("getPowerState: {data}".format(data=ilo_info))
        logging.debug("getPowerState: {data}".format(data=ilo_info.obj['PowerState']))
        logging.info("getPowerState: END")
        return ilo_info.obj['PowerState']

    #######################################
    # Function to set iLO power state
    #######################################
    def setPowerState(self, state):
        iloInfo = self.redfishObj.get('/redfish/v1/Systems/1/')
        reset_body = {}
        if state.lower() == "on":
            reset_body = {"ResetType": self.POWER_ON}

        elif state.lower() == "off":
            reset_body = {"ResetType": self.POWER_OFF}

        elif state.lower() == "push":
            reset_body = {"ResetType": self.POWER_PUSH}

        elif state.lower() == "force-reset":
            reset_body = {"ResetType": self.POWER_RESET}

        elif state.lower() == "graceful-shutdown":
            reset_body = {"ResetType": self.POWER_GRACEFUL_SHUTDOWN}

        response = self.redfishObj.post("/redfish/v1/systems/1/Actions/ComputerSystem.Reset", body=reset_body)
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
        logging.info("ensurePowerState: START")
        state = self.getPowerState()

        if state.lower() != expectedState.lower():
            self.setPowerState(expectedState)

        logging.info("ensurePowerState: END")
   
    #######################################
    # Function to reset iLO power state
    #
    # If the server state is
    # - Off, func will power on
    # - on, func will force reset
    #######################################
    def resetPowerState(self):
        logging.info("resetPowerState: ")

        if self.getPowerState().lower() == "off":
            self.setPowerState("on")
        else:
            self.setPowerState("force-reset")


    #######################################
    # Function to wait for BIOS post to
    # be completed
    #######################################
    def waitForBiosPost(self):
        logging.info("waitForBiosPost: START")

        # Wait for BIOS to be unlocked
        sleep_time = 10
        counter = 25
        while self.isBiosLock():
            counter = counter - 1
            time.sleep(sleep_time)

            if counter == 0:
                # Power off the node and raise Exception
                self.ensurePowerState("graceful-shutdown")
                logging.exception("Timeout reach while waiting for BIOS")
                raise Exception("Timeout reach while waiting for BIOS")

        # Sleep additional 2 seconds, just to make sure BIOS 
        # updates reflect in redfish
        time.sleep(20)

        logging.info("waitForBiosPost: END")

    #######################################
    # Function to read all physical drives of smart array controllers
    #
    # Populates class attribute 'phyDrives' with list of physical disks
    #######################################
    def physicalDrives(self):
        logging.info("physicalDrives: START")

        self.phyDrives = []
        logging.info("Get the list of physical drives")
        for controller in self.redfishObj.get('/redfish/v1/Systems/1/SmartStorage/ArrayControllers').obj["Members"]:
            smart_array_controller_info = self.redfishObj.get(controller["@odata.id"] + "/DiskDrives")
            for disk in smart_array_controller_info.obj["Members"]:
                drive_info = {}
                disk_info_obj = self.redfishObj.get(disk["@odata.id"])
                drive_info["InterfaceType"] = disk_info_obj.obj["InterfaceType"]
                drive_info["Location"] = disk_info_obj.obj["Location"]
                drive_info["MediaType"] = disk_info_obj.obj["MediaType"]
                drive_info["CapacityGB"] = disk_info_obj.obj["CapacityGB"]
                drive_info["Health"] = disk_info_obj.obj["Status"]["Health"]
                drive_info["State"] = disk_info_obj.obj["Status"]["State"]
                drive_info["DiskDriveUse"] = disk_info_obj.obj["DiskDriveUse"]

                self.phyDrives.append(drive_info)

        logging.info("physicalDrives: END")
        return self.phyDrives

    #######################################
    # Function to read all physical drives of smart array controllers
    #
    # Return self.phyDrives with list of physical disks, if present
    # Else, will query and present
    #######################################
    def getPhysicalDrives(self):
        logging.info("getPhysicalDrives: START")
        if self.phyDrives:
            logging.info("getPhysicalDrives: END")
            return self.phyDrives

        return self.physicalDrives()

    #######################################
    # Function to normal configuration by reading BIOS config
    #######################################
    def normalizeConfig(self):
        logging.info("normalizeConfig: ")

        retry_count = 3
        logging.debug("Redfish does not respond to physical drive, run the POST to pull the information")
        self.changeTemporaryBootOrder()
        self.resetPowerState()
        self.waitForBiosPost()

        while retry_count and (not self.getPhysicalDrives()):
            time.sleep(20)
            retry_count -= 1
        #if (retry_count == 1):
        #    # Wait 20 seconds more for last retry
        #    time.sleep(20)

        while retry_count and (not self.physicalDrives()):
            time.sleep(20)
            retry_count -= 1

        if not self.phyDrives:
             message = "Failed to normalize configuration after multiple retries, either issue with server or no physical disks"
             logging.error(message)
             raise Exception(message)

    #######################################
    # Function to delete all logical drives
    #######################################
    def deleteAllLogicalDrives(self):
        logging.info("Delete all logical drives")

        logical_drive_req_data = {}
        logical_drive_req_data["DataGuard"] = "Disabled"
        logical_drive_req_data["LogicalDrives"] = []

        smart_config_delete_setting = self.redfishObj.put('/redfish/v1/Systems/1/smartstorageconfig/settings', body=logical_drive_req_data)

        if smart_config_delete_setting.status != 200:
            logging.exception("Failed to delete RAID configuration")
            raise Exception("Failed to delete RAID configuration")

        # Reset the server to reflect the changes
        self.normalizeConfig()

    #######################################
    # Function to delete logical drive
    #
    # Returns status or exception
    #######################################
    def deleteLogicalDrive(self, logicalDriveID):

        logging.info("Delete logical drive")

        # Request body for LG drive creation
        smart_config_setting = self.redfishObj.get('/redfish/v1/Systems/1/smartstorageconfig/settings/')
        logical_drive_req_data = smart_config_setting.obj

        logical_drive_req_data["DataGuard"] = "Permissive"

        logical_drive = {}
        logical_drive["Actions"] = [{"Action": "LogicalDriveDelete"}]
        logical_drive["VolumeUniqueIdentifier"] = logicalDriveID
        logical_drive_req_data["LogicalDrives"].append(logical_drive)

        logical_drive_req_data = {
                                  "LogicalDrives": [ 
                                      { 
                                          "Actions": [{"Action": "LogicalDriveDelete"}], 
                                          "VolumeUniqueIdentifier": logicalDriveID 
                                      } 
                                  ], 
                                  "DataGuard": "Permissive" 
                              }

        logging.debug("deleteLogicalDrive: logicalDriveReqData: {}".format(logical_drive_req_data))

        # Delete of logical drive
        smart_config_update_setting = self.redfishObj.put('/redfish/v1/Systems/1/smartstorageconfig/settings/', body=logical_drive_req_data)
        if smart_config_update_setting.status != 200:
            logging.exception("Rest request to delete RAID failed : " + smart_config_update_setting.text)

        # Reset the server to reflect the changes
        self.normalizeConfig()


    #######################################
    # Function to create logical drive
    #
    # Returns logical drive or exception
    #######################################
    def createLogicalDrive(self, logical_input_data):
        logging.info("Create logical drive")

        # iLO cannot receive local storage info from storage controller when the server is in off state
        # iLO can get the info through BIOS after completion of POST or 
        # it can get the info from the host operating system provided it is running AMS service
        self.normalizeConfig()

        # Read all the physical drives
        #self.getPhysicalDrives()
        #if not self.phyDrives:
        #    logging.exception("createLogicalDrive: Failed to create new logical drive: No physical drives present")
        #    raise Exception("createLogicalDrive: Failed to create new logical drive: No physical drives present")

        # Input parameters for LG creation
        logical_capacity = int(logical_input_data['capacity'])
        logical_capacity_unit = logical_input_data['capacityUnit']
        drive_technology = logical_input_data['driveTechnology']
        deploy_operation = logical_input_data['operation']
        raid_config = logical_input_data['raidLevel']
        do_deletion = False

        error_message = "Failed to create logical drive of raid {raid} " \
            "and drive technology {driveTech} with capacity {size} {unit}".format(
            raid=raid_config, driveTech=drive_technology, size=logical_capacity,
            unit=logical_capacity_unit)
        if deploy_operation.upper() == "DELETE_ALL_AND_CREATE".upper():
            do_deletion = True

        if raid_config.lower() != "raid1":
            logging.exception(error_message + " : Only RAID 1 is currently supported")
            raise Exception(error_message + " : Only RAID 1 is currently supported")

        if logical_capacity_unit.upper() == "TB":
            logical_capacity = logical_capacity * 1000

        # Get existing logical drives
        existing_logical_drives = self.getLogicalDrives()
        existing_drive_ids = [x['driveID'] for x in existing_logical_drives]

        # deployOperation can take inputs like "DELETE_ALL_AND_CREATE", "CREATE"
        # By default it is create New, if delete is needed change the REST body
        if do_deletion and existing_logical_drives:
            self.deleteAllLogicalDrives()

        # Get only unassigned physical drives
        #
        # In case of DELETE_ALL_AND_CREATE, all the physical disk
        # that matches to capacity, drive technology are selected
        unassigned_drives = []
        for drive in self.phyDrives:
            if drive.get('InterfaceType') in drive_technology and \
               drive.get('MediaType') in drive_technology and \
               drive.get("CapacityGB") == int(logical_capacity):

                 if do_deletion:
                      unassigned_drives.append(drive.get("Location"))
                 elif drive.get("DiskDriveUse").lower() == "raw":
                      unassigned_drives.append(drive.get("Location"))

        if not unassigned_drives:
            logging.exception(error_message + " : Cannot find raw physical drives")
            raise Exception(error_message + " : Cannot find raw physical drives")

        # TODO: print will be debug message
        logging.info("\nList of unassigned drives {} \n".format(unassigned_drives))

        # Map user RAID with redfish RAID level
        RAID_LEVEL = {
            "RAID1": "Raid1",
            "RAID5": "Raid5",
            "RAID10": "Raid10"
        }

        # Future Use: Minimum disk requirements for RAID
        RAID_MIN = {
            "RAID1": 2,
            "RAID5": 3,
            "RAID10": 4
        }

        # TODO: Check if there minimum unassigned drives are avaiable for the raid

        # Request body for LG drive creation
        smart_config_setting = self.redfishObj.get('/redfish/v1/Systems/1/smartstorageconfig/settings/')
        logical_drive_req_data = smart_config_setting.obj

        logical_drive_req_data["DataGuard"] = "Disabled"

        logical_drive = {}
        logical_drive["LogicalDriveName"] = "LogicalDrive_OSDA"
        logical_drive["Raid"] = RAID_LEVEL[raid_config.upper()]
        logical_drive["DataDrives"] = unassigned_drives[:RAID_MIN[raid_config.upper()]]
        logical_drive_req_data["LogicalDrives"].append(logical_drive)

        # Creation of logical drive
        smart_config_update_setting = self.redfishObj.put('/redfish/v1/Systems/1/smartstorageconfig/settings/', body=logical_drive_req_data)
        if smart_config_update_setting.status != 200:
            logging.exception(error_message + ": Rest request to create RAID failed : " + smart_config_update_setting.text)
            raise Exception(error_message + ": Rest request to create RAID failed : " + smart_config_update_setting.text)

        logging.info("Raid configuration updated successful. System reset required to reflect the changes")

        # Reset the server to reflect the changes
        self.normalizeConfig()
        #self.changeTemporaryBootOrder()
        #self.resetPowerState()

        # Wait and check if logical drive is created
        # Wait for maximum of 2 minutes
        #
        # TODO: Need to check for a better logic
        counter = 15
        #time.sleep(20)
        sleep_time = 10

        # Wait for BIOS to be unlocked
        #self.waitForBiosPost()
        while True:
            new_logical_drives = self.getLogicalDrives()
            if len(existing_logical_drives) != len(new_logical_drives) or do_deletion:
                lg_drive = self.getLogicalDriveFromDisk(new_logical_drives, unassigned_drives[0])
                if lg_drive and lg_drive['driveID'] not in existing_drive_ids:
                    return lg_drive

            if counter == 0:
                # Power off the node and raise Exception
                self.ensurePowerState("graceful-shutdown")
                logging.exception(error_message + " : Timeout to find new logical drive")
                raise Exception(error_message + " : Timeout to find new logical drive")

            counter = counter - 1
            time.sleep(sleep_time)
        
    #######################################
    # Function to check to get logical drive of a given physical disk
    # 
    # Returns logical drive or None
    #######################################
    def getLogicalDriveFromDisk(self, logical_drive_list, phydrive):
        lg_drive = next((x for x in logical_drive_list if phydrive in x["dataDrives"]), None)
        return lg_drive


    #######################################
    # Function to get logical drives
    #
    # This function re-read all the logical drives
    # even if the logicalDrives are available
    #
    # Populates class attribute 'logicalDrives' with list of logical drives
    #######################################
    def getLogicalDrives(self):
        smart_config_info = self.redfishObj.get('/redfish/v1/Systems/1/smartstorageconfig/')
        self.logicalDrives = []
        for lg_drive in smart_config_info.obj["LogicalDrives"]:
            drive = {}
            drive["logicalDriveNumber"] = lg_drive["LogicalDriveNumber"]
            drive["dataDrives"] = lg_drive["DataDrives"]
            drive["capacityGiB"] = lg_drive["CapacityGiB"]
            drive["raidLevel"] = lg_drive["Raid"]
            drive["driveID"] = lg_drive["VolumeUniqueIdentifier"]

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
        logging.info("getPostState: START")
        ilo_info = self.redfishObj.get('/redfish/v1/Systems/1/')
        logging.info("getPostState: END")
        return ilo_info.obj['Oem']['Hpe']['PostState']

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
        post_state = self.getPostState()
        logging.debug("Post State : {}".format(post_state))
        if post_state.upper() in ["INPOSTDISCOVERYCOMPLETE", "FINISHEDPOST"]:
            return False

        return True


if __name__ == '__main__':

    SYSTEM_URL = "10.188.2.16"
    LOGIN_ACCOUNT = "v0175usradmin"
    LOGIN_PASSWORD = "HP!nvent123"
    A = ILORedfish(SYSTEM_URL, LOGIN_ACCOUNT, LOGIN_PASSWORD)

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
    A.change_temporary_boot_order()


    quit()





    drive = {'logicalDriveNumber': 3, 'faultTolerance': 'RAID 1', 'driveID': '600508B1001CAA4ECFD2FBCFC754E865'}
    A.modifyBootOrder(drive)
    #print (A.getILOStorageDrives())

    #print (A.mountVirtualMedia("http://10.188.210.16/RHEL-7.6-20181010.0-Server-x86_64-dvd1.iso", "CD", bootOnNextServerReset=True))
    #print (A.mountVirtualMedia("http://10.188.210.16/rhelKsImage1.img", "USBStick"))


