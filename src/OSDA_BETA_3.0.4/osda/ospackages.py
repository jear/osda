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
import osda.geniso as geniso
import osda.config as config
import logging
import os

g_ospackages_settings = []
g_osPackagesFilePath = ""
g_ksFilesPath = ""
g_htmlPath = ''

def init(osPackagesFilePath, ksFilesPath):

    global g_osPackagesFilePath
    g_osPackagesFilePath = osPackagesFilePath
    global g_ksFilesPath 
    g_ksFilesPath = ksFilesPath

    #fin = open('/opt/hpe/osda/data/config/ospackages.json', 'r')
    fin = open(g_osPackagesFilePath, 'r')
    global g_ospackages_settings

    g_ospackages_settings = json.load(fin)
    #print(g_ospackages_settings)
    fin.close()

    defaultConfig = config.DefaultConfig()
    global g_htmlPath 
    g_htmlPath = defaultConfig.htmlPath

def getSupportedOSList():
    
    ksFiles = getKSFiles()

    osList = []
    for ksFile in ksFiles:
        osList.append(ksFile['osType'])


    #return ["ESXi7", "ESXi6", "RHEL7", "RHEL8", "SLES15"]
    return osList

def getOSPackageById(id):

    logging.debug("getOSPackage")
    global g_ospackages_settings

    for package in g_ospackages_settings:
        logging.debug(package)
        if package['uri'] == id:
            return package

    return []

def deleteOSPackageById(id, osDistro):
    '''
    Delete OS package in g_ospackages_settings by id.
    Remove ISO referenced by ISO_http_path
    '''
    logging.debug('deleteOSPackageById')
    global g_ospackages_settings
    global g_htmlPath
    try:
        index = None
        logging.debug(f'id: {id}')
        for i, entry in enumerate(g_ospackages_settings):
            logging.debug(entry)
            logging.debug(f'i: {i} entry["uri"]: {entry["uri"]}')
            if entry['uri'] == id:
                index = i
                break
        if index == None:
            logging.error(f'{id} not found')
            raise Exception(f'OS package id {id} not found in OS package settings')
        else:
            isoName = g_ospackages_settings[index]['ISO_http_path']
            logging.debug(f'Delete ISO {g_htmlPath}{isoName}')
            os.remove(f'{g_htmlPath}{isoName}')
            logging.debug(f'Delete OS id {id}')
            del g_ospackages_settings[index]
            index = None
            #osConfigJson = '/opt/hpe/osda/data/config/ospackages.json'
            global g_osPackagesFilePath
            osConfigJson = g_osPackagesFilePath
            with open(osConfigJson,'w') as f:
                f.write(json.dumps(g_ospackages_settings, indent=2))
            return 'Success'
    except Exception as err:
        logging.error(err)
        raise Exception(str(err))

def getOSPackages():
    global g_osPackagesFilePath
    global g_ospackages_settings
    try:
        with open(g_osPackagesFilePath, 'r') as fin:
            g_ospackages_settings = json.load(fin)
        return g_ospackages_settings
    except Exception as err:
        logging.error(err)
        raise Exception(str(err))

def getOSPackagesStats():

    total = len(g_ospackages_settings)

    stats = dict()

    for package in g_ospackages_settings:
        logging.debug(package)
        if package['osType'] in stats:
            stats[package['osType']] += 1 
        else:
            stats[package['osType']] = 1
    statsJSON = []
    for key in stats.keys():
        statsJSON.append({ "osType": key, "count": stats[key]})

    return ({ "total": total, "stats": statsJSON})
        

def getOSPackage(ospackagename):
    logging.info("getOSPackage: ospackagename: " + ospackagename)
    #fin = open('/opt/hpe/osda/data/config/ospackages.json', 'r')
    global g_osPackagesFilePath
    fin = open(g_osPackagesFilePath, 'r')
    global g_ospackages_settings
    g_ospackages_settings = json.load(fin)
    fin.close()
    ospackage = {}
    for ospack in g_ospackages_settings:
        if ospack['package'] == ospackagename:
            ospackage = ospack
            break


    logging.info("#################### " + json.dumps(ospackage))
    if ospackage == {}:
        logging.error("The requested OS package is not found for: " + ospackagename)
        err =  ("Invalid or unknown OS package -" + ospackagename + " specified. Cannot proceed")
        raise Exception(err)

    return ospackage

def setOSPackage(ospackagedata):

    logging.debug("setOSPacage: ")
    logging.debug(ospackagedata)
    global g_ospackages_settings
    g_ospackages_settings.append(ospackagedata)
    logging.debug("ospackages: ")
    logging.debug( g_ospackages_settings)

    #fout = open('/opt/hpe/osda/data/config/ospackages.json', 'w')
    global g_osPackagesFilePath
    fout = open(g_osPackagesFilePath, 'w')
    json.dump(g_ospackages_settings, fout, indent=2)
    fout.close()

def createOSPackage(ospackagedata, orig_iso_path):
    global g_ospackages_settings


    logging.debug("createOSPackage: Generating OS package for: ")
    logging.debug(ospackagedata)
    #print(type(ospackagedata))

    ospackitem = json.loads('{ "uri": "", "package": "", "osType":  "", "ISO_http_path": "" }')

    logging.debug("%%%%%%%%%%%%%")
    logging.debug(ospackitem['package'])
    ospackitem['uri'] = uuid.uuid4().hex
    ospackitem['package'] = ospackagedata['ospackage']
    ospackitem['osType'] = ospackagedata['ostype']

    target_dir = config.WalkmanSettings().get("local_http_root")

    if ospackitem['osType'] == 'ESXi6':
        target_iso_path = geniso.createKickstartISO_ESXi67(orig_iso_path, target_dir)
        logging.info("createOSPackage: target_iso_path: " + str(target_iso_path))
        ospackitem['ISO_http_path'] = target_iso_path.split(target_dir)[1]
        setOSPackage(ospackitem)
        return ospackitem

    return {"error": "Unsupported OS type"}

def getKSFiles():
    #fin = open(f'/opt/hpe/osda/data/config/ksfiles.json', 'r')
    global g_ksFilesPath
   
    fin = open(g_ksFilesPath, 'r')
    ksFiles = json.load(fin)
    fin.close()

    return ksFiles

def getAvailableKickstarts(osType):
    logging.info("getAvailableKickstarts osType: " + osType)

    #supportedOSes = getSupportedOSList()
    ksFiles = getKSFiles()

    result = []

    for os1 in ksFiles:
        files = []
        if osType == "" or os1['osType'] == osType:
            logging.debug(os1)
            baseKSFile = os1['basekspath']
            ksPath = os.path.dirname(baseKSFile)
            files = os.listdir(ksPath)
            result.append({'osType': os1['osType'], 'kickStarts': files})

    return result



if __name__ == '__main__':
    print("sdsds")


    init()



    package = getOSPackage("junkos")
    print(package)
