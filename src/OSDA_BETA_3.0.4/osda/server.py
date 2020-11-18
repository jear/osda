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
import json
from flask import Flask, flash, request, redirect, url_for, jsonify
from flask_cors import CORS

from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest

import sys
import socket
import uuid
import logging
from logging.handlers import RotatingFileHandler

import ssl

#sys.path.append('../scripts/')
import osda.walkman as walkman



#from flask import Flask, jsonify
#from flask import request

app = Flask(__name__)

CORS(app)

ALLOWED_EXTENSIONS = set(['txt', 'iso', 'ISO'])


@app.route('/rest/sessions', methods=['POST'])
def sessions():
    try:    
        logging.debug("Sessions.............")
        logging.debug(request.json)
        logging.debug(json.dumps(request.json))

        response1 = request.json;
        response1['token'] = uuid.uuid4().hex
        response1['password'] = ""

        return jsonify(response1)
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/dashboard', methods=['GET'])
def getDashboardData():
    try:
        dashboardData = walkman.getDashboardData()
        logging.debug("getDashboardData: ")
        logging.debug(dashboardData)
        return jsonify({ "result": dashboardData, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/tasks/<int:taskid>', methods=['GET'])
def getStatus(taskid):
    try:
        taskStatus = walkman.getTaskStatus(taskid)
        return jsonify({ 'result': taskStatus, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/ksconfig/<os>', methods=['GET'])
def getKSConfigURL(os):
    try:
        logging.debug("getKSConfigURL: ")
        logging.debug(request.headers)
        logging.debug("########################: ")
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/tasks', methods=['GET'])
def getAllStatus():
    try:    
        allTasksStatus = walkman.getAllTasks()
        #logging.debug(allTasksStatus)
        #logging.debug(jsonify(allTasksStatus))
        #return jsonify({ "tasks": jsonify(allTasksStatus), "count": len(allTasksStatus), "total": len(allTasksStatus), "error": {}})
        return jsonify({ "tasks": allTasksStatus, "count": len(allTasksStatus), "total": len(allTasksStatus), "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/networks/list', methods=['GET'])
def getNetworks():
    try:
        logging.debug("getNetworks: ")
        networks = walkman.getNetworks()

        logging.debug(networks)
        return jsonify({ "result": networks, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/networks/add', methods=['POST'])
def addNetwork():
    try:    
        logging.debug("addNetwork.............")
        logging.debug(request.json)
        logging.debug(json.dumps(request.json))
        result = walkman.addNetwork((request.json))

        return jsonify(result)
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/networks/<name>', methods=['GET'])
def getNetwork(name):
    try:
        logging.debug("get network for name: ", name)
        network = walkman.getNetwork(name)
        logging.debug(network)
        return jsonify({ "result": network, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/oneview/list', methods=['GET'])
def getRegisteredOVs():
    try:
        logging.debug("getRegisteredOVs: ")
        #logging.info("getRegisteredOVs: ")
        allOVs = walkman.getRegisteredOVs()

        logging.debug(allOVs)
        #logging.info(allOVs)
        return jsonify({ "result": allOVs, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/kickstart/list', methods=['GET'])
def getAvailableKickStarts():
    try:
        logging.info("getAvailableKickStarts ")
        # the URL query params ?ostype=ESXi7 
        # if no query parameter found then returns all kickstarts grouped by OS types
        osType = request.args.get('ostype', '')

        kickstarts = walkman.getAvailableKickStarts(osType)
        logging.debug(kickstarts)
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

    return jsonify({"result": kickstarts, 'error': {}})


@app.route('/rest/ostype/list', methods=['GET'])
def getSupportedOSList():
    try:
        supportedOSList = walkman.getSupportedOSList()
        logging.debug("getSupportedOSList: ")
        logging.debug(supportedOSList)
        #return jsonify(supportedOSList)
        return jsonify({ "result": supportedOSList, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/oneview/add', methods=['POST'])
def addOneView():
    try:
        logging.debug("addOneView.............")
        logging.debug(request.json)
        logging.debug(json.dumps(request.json))
        result = walkman.registerOV((request.json))
        logging.debug("result")
        logging.debug(result)

        return jsonify(result)
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/oneview/<alias>', methods=['GET', 'DELETE'])
def OVAppliance(alias):
    try:
        logging.debug(f"Request on OV appliance on {alias}")
        if request.method == 'DELETE':
            logging.debug(f'DELETE OV appliance alias {alias}')
            rc = walkman.deleteOVAppliance(alias)
            return jsonify({ "result": rc, "error": {}})
        elif request.method == 'GET':
            logging.debug(f'GET OV appliance alias {alias}')
            appliance = walkman.getOVAppliance(alias)
            logging.debug(appliance)
            return jsonify({ "result": appliance, "error": {}})
        else:
            #raise Exception(f'{request.method} is not supported')
            return jsonify({"result": {}, 'error': { 'errorCode': "E1301", 'msg': str(f'{request.method} is not supported')}})
    except Exception as err:
        logging.error(f'route error: {err}')
        #return jsonify({"result": "Fail", 'error': str(err)})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/oneview/spt/list', methods=['GET'])
def getSPTListForOV():
    try:
        ovalias = request.args.get('ovalias', '')
        logging.debug("ovalias: " + ovalias)
        ovsptlist = walkman.getSPTs(ovalias)
        #return jsonify(splist)
        return jsonify({ "result": ovsptlist, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/oneview/spt/connections', methods=['GET'])
def getOVSPTNetworkConnections():
    try:
        # Get the name of the server profile template through 
        # the URL query params ?spt=serverprofiletemplatename and
        # query param ?ovname=oneviewappliancename
        spt = request.args.get('spt', '')
        ovname = request.args.get('ovname', '')

        logging.debug("ovname: " + ovname)
        logging.debug("spt: " + spt)
        conns = walkman.getOVSPTNetworkConnections(ovname, spt)
        #return jsonify(conns)
        return jsonify({ "result": conns, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/oneview/spt/drives', methods=['GET'])
def getOVSPTStorageDrives():
    try:
        logging.debug("getOVSPTStorageDrives")

        # Get the name of the server profile template through 
        # the URL query params ?spt=serverprofiletemplatename and
        # query param ?ovname=oneviewappliancename
        spt = request.args.get('spt', '')
        ovname = request.args.get('ovname', '')

        logging.debug("ovname: " + ovname)
        logging.debug("spt: " + spt)
        drives = walkman.getOVSPTStorageDrives(ovname, spt)
        logging.debug("Drives")
        logging.debug(drives)
        #return jsonify(drives)
        return jsonify({ "result": drives, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/ilo/connections', methods=['POST'])
def getILONetworkConnections():

    try:
        logging.debug(json.dumps(request.json))

        # Gen9 changes
        conns = walkman.getILONetworkConnections(request.json['iloip'], request.json['ilocreds'], request.json['gen'])
        logging.debug("*********************************")
        logging.debug(conns)
        return jsonify({ "result": conns, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/ilo/storagedrives', methods=['POST'])
def getILOStorageDrives():
    try:
        logging.debug(json.dumps(request.json))

        drives = walkman.getILOStorageDrives(request.json['iloip'], request.json['ilocreds'], request.json['gen'])
        logging.debug("*********************************")
        logging.debug(drives)
        return jsonify({ "result": drives, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/ospackage/list', methods=['GET'])
def getOSPackages():
    try:
        logging.debug(request)
        logging.debug("get ospackage list: ")
        ospackages = walkman.getOSPackages()

        logging.debug(ospackages)
        #return jsonify(ospackages)
        return jsonify({ "result": ospackages, "error": {}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/ospackage/<id>', methods=['GET', 'DELETE'])
def OSPackageById(id):
    try:
        logging.debug(f'Request on OS package {id}')
        if request.method == 'DELETE':
            logging.debug(f'DELETE OS package id {id}')
            rc = walkman.deleteOSPackageById(id)
            return jsonify({ "result": rc, "error": {}})
        elif request.method == 'GET':
            logging.debug(f'GET OS package id {id}')
            ospackage = walkman.getOSPackageById(id)
            logging.debug(ospackage)
            return jsonify({ "result": ospackage, "error": {}})
        else:
            #raise Exception(f'{request.method} is not supported')
            return jsonify({"result": {}, 'error': { 'errorCode': "E1301", 'msg': str(f'{request.method} is not supported')}})
    except Exception as err:
        logging.error(f'route error: {err}')
        #return jsonify({"result": "Fail", 'error': str(err)})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/undeploy', methods=['DELETE'])
def unDeploy():
    logging.info("/rest/undeploy")
    try:
        logging.debug("/rest/undeploy: ", jsonify(request.json))
        logging.debug(json.dumps(request.json))
        (result, status_code) = walkman.deployMain(request.json, operation="UNDEPLOY")
        logging.debug(json.dumps(result))
        #return jsonify({"result": result['result'], 'error': result['error']})
        if 'error' in result and len(result['error']):
            return jsonify({"result": result['result'], 'error': {'errorCode': "E1000", 'msg': result['error']}}), status_code
        else:
            return jsonify({'result': result['result'], 'error': {}}), status_code
        #return jsonify({'result': {}, 'error': {'message': 'some error while processing undeploy request!'}})
    except Exception as err:
        logging.exception(err)
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.route('/rest/deploy', methods=['POST'])
def deploy():
    try:
        logging.debug("/rest/deploy: ", jsonify(request.json))
        logging.debug(json.dumps(request.json))
        (deploy_result, status_code) = walkman.deployMain(request.json)
        logging.debug(json.dumps(deploy_result))
        #return jsonify({"result": deploy_result['result'], 'error': deploy_result['error']})
        if 'error' in deploy_result and len(deploy_result['error']):
            return jsonify({"result": deploy_result['result'], 'error': {'errorCode': "E1000", 'msg': deploy_result['error']}}), status_code
        else:
            return jsonify({"result": deploy_result['result'], 'error': {}}), status_code
    except BadRequest as err:
        logging.error(err)
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}}), 400
    except Exception as err:
        logging.exception(err)
        #raise Exception from err
        #return jsonify({"result": {}, 'error': err})
        return jsonify({"result": {}, 'error': { 'errorCode': "E1000", 'msg': str(err)}})

@app.errorhandler(404)
def page_not_found(e):
    try:
        return jsonify({'result' : 'Page Not Found'})
    except Exception as err:
        logging.exception(err)
        raise Exception from err

def allowed_file(filename):
    try:
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    except Exception as err:
        logging.exception(err)
        raise Exception from err

@app.route('/rest/upload', methods=['POST'])
def upload():
    try:
        logging.info("HTTP Upload for uploading OS ISOs and other files")
        logging.info("&&&&&&&&&")

        # The form-data should include OS package meta data like data={'ospackage': 'ESXi6.5_1', 'ostype': 'ESXi'}

        if request.method == 'POST':
            logging.info("POST....")

            logging.debug("upload: files: " + str(request.files))
            logging.debug("upload: files request.form.get('data') : " + str(request.form.get('data')))
            data = json.loads(request.form.get('data'))
            logging.debug("upload: data: " + str(data))

            # check if the post request has the file part
            if 'file' not in request.files:
                logging.warn("No file part...")
                flash('No file part')
                #return {"result": {}, "error": "No file part found in POST request"}
                return { "result": {}, "error": {'errorCode': "E1000", 'msg': "No file part found in POST request"}}
            file = request.files['file']
            logging.debug("File is: ")
            logging.debug(file)
            # if user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                logging.info("No selected file...")
                flash('No selected file')
                return { "result": {}, "error": {'errorCode': "E1000", 'msg': "No input file found"}}
            if file and allowed_file(file.filename):
                logging.info("Saving the file...")
                filename = secure_filename(file.filename)
                # Target path for the uploading file 
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                # Save the file
                logging.info("Saving the file to: " + str(filepath))
                file.save(filepath)

                # This function is from walkman.py
                retval = walkman.createOSPackage(data, filepath)
                logging.info("createOSPackage returned: " + str(retval))
                return jsonify({"result": retval, "error": {}})
                #return redirect(url_for('upload', filename=filename))

        return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
        <input type=file name=file>
        <input type=submit value=Upload>
        </form>
        '''
    except Exception as err:
        logging.exception(err)
        return jsonify({"result": {}, 'error': str(err)})

LOGGING_LEVEL = {
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'DEBUG': logging.DEBUG,
}

def start(config):
    try:
        ipaddr = config.get('server')
        port   = config.get('port')
        logPath  = config.get('logPath')
        logLevel = LOGGING_LEVEL[config.get('logLevel').upper()]

        logFile = os.path.join(logPath, 'OSDA.log')

        if not os.path.exists(logPath):
            os.mkdir(logPath)

        logggingFormat = '%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s'
        #,datefmt='%Y-%m-%d %H:%M:%S'

        fh = RotatingFileHandler(logFile, maxBytes=10*1024*1024, backupCount=2)
        logging.basicConfig(
            level=logLevel,
            format=logggingFormat,
            handlers=[fh, logging.StreamHandler()])

        app.config['UPLOAD_FOLDER'] = '/tmp'
        app.secret_key = "secret key"

        # set max length of file that can be uploaded to 20 GB
        app.config['MAX_CONTENT_LENGTH'] = 20000 * 1024 * 1024
        logging.debug("{} : {} : {} : {}".format(ipaddr, port, logPath, logLevel))
        logging.debug("Server IP: " + ipaddr)
        logging.info("Starting REST server at http://{}:{}/".format(ipaddr, port))
        walkman.init(ipaddr) # this is from walkman.py
        #app.run(debug=True, host=LOCALHOST)
        #app.run(ssl_context="adhoc",debug=True, host=ipaddr)
        app.run(debug=True, host=ipaddr)
    except Exception as err:
        logging.exception(err, exc_info=True)

if __name__ == '__main__':
    userConfig = {
        'server': "10.188.210.206",
        'port': 5000,
        'logPath': "logs",
        'logLevel': "DEBUG"
    }



    start(userConfig)
