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


import os, sys
import json
import time
import datetime
import random
import logging

confWalkmanFile = '/opt/hpe/osda/data/config/ospackages.json'

class DefaultConfig():

    def __init__(self):
        try:
            self.kickstartFile = '/opt/hpe/osda/data/config/ksfiles.json'
            self.confWalkmanFile = '/opt/hpe/osda/data/config/walkman.json'
            self.osPackagesFile = '/opt/hpe/osda/data/config/ospackages.json'
            self.activityLogs = '/opt/hpe/osda/data/activities/activityLog.json'
            self.htmlPath = self.getHtmlPath()
            self.hostDistroName = self.getDistroName()
            self.htmlWebIP = '10.188.210.14'
            self.ksBaseImg = "/opt/hpe/osda/data/kickstarts/ks_base.img"
        except GetDistroError as err:
            logging.error(str(err))
            sys.exit(str(err))
        except Exception as err:
            raise err

    def getHtmlPath(self):
        try:
            if self.getDistroName() in ['sles']:
                return '/srv/www/htdocs/'
            elif self.getDistroName() in ['rhel', 'centos']:
                return '/var/www/html/'
            else:
                raise Exception("Local HTML path undetermined due to not able to identify host OS")
        except Exception as err:
            raise err

    def getDistroName(self):
        '''
        Get the name of the OS distribution by cat /etc/os-release
        '''
        try:
            distroName = None
            distroInfo = os.popen('cat /etc/os-release').read().split('\n')
            for entry in distroInfo:
                if entry.find('ID=') == 0:
                    distroName = entry.split('ID=')[1].replace('"', '')
            if not distroName:
                raise GetDistroError('OSDA not able to determine host OS distro. Exiting application') 
            return distroName.strip()
        except Exception as err:
            raise err

class GetDistroError(Exception):
    pass            

class WalkmanSettings():
    def __init__(self):
        try:
            self.conf = DefaultConfig()
        except Exception as err:
            raise err

    def getAll(self):
        fin = open(self.conf.confWalkmanFile, 'r')
        walkmanSettings = json.load(fin)
        fin.close()
        return walkmanSettings

    def get(self, key):
        cnf = self.getAll()
        if key in cnf:
            return cnf[key]
        else:
            return None
#        return walkmanSettings

    def set(self, key, value):
        fin = open(self.conf.confWalkmanFile, 'r')
        walkmanSettings = json.load(fin)
        fin.close()
        walkmanSettings[key] = value
        fout = open(self.conf.confWalkmanFile, 'w')
        json.dump(walkmanSettings, fout, indent=2)
        fout.close()




class Activities(object):

    TasksTable = dict()
    
    def createTask(self, deployData):
        taskID = random.randint(1001,999999)
        subTasks = []
        i = 0
        for task in deployData['hosts']:
            logging.debug("##############")
            logging.debug(task)
            subTasks.append(self.getSubTask(i, task))
            i = i + 1
        self.TasksTable[taskID] = {
                       "taskID": taskID,
                       "subTasks": subTasks,
                       "taskName": deployData['taskName'],
                       "deploymentMode": deployData['deploymentMode'],
                       "startTime": datetime.datetime.now().isoformat(),
                       "deploymentSettings": {}
                   }
        return taskID

    def setTaskStatus(self, taskID, status, message):
        logging.debug("setTaskStatus: ")
        logging.debug(taskID)
        logging.debug(status)
        

        task = self.TasksTable[taskID]
        task["status"] = status
        task["errorMsg"] = message
        self.TasksTable[taskID] = task

        return 0

    def getSubTask(self, id, task):
        # Add the subtask items
        task['id'] = int(id)
        task['progress'] = 0
        task['status'] = ""
        task['startTime'] = datetime.datetime.now().isoformat(),

        logging.debug("Sub-task: ")
        logging.debug(task)
        return task

    def getTaskStatus(self, taskID):
        try:
            return self.TasksTable[taskID]
        except KeyError:
            return {"errorMsg": "Task Id {} not found".format(taskID)}

    def setSubTaskStatus(self, taskID, subtaskID, status, message, progress):
        logging.debug("setTaskStatus: ")
        logging.debug(taskID)
        logging.debug(subtaskID)
        logging.debug(status)

        #TasksTable[taskID] = str(subtaskID) + ":" + status
        task = self.TasksTable[taskID]
        task["subTasks"][subtaskID]["status"] = status
        task["subTasks"][subtaskID]["message"] = message
        # In case of error, the progress will be set to -1 to indicate no increment to progress value
        # If the input arg progress == 10, then set the progress to 10. This means task completed
        if progress == 1:
            # ensure that progress is not greater than 9 when input arg progress == 1
            if task["subTasks"][subtaskID]["progress"] != 9:
                task["subTasks"][subtaskID]["progress"] = progress + task["subTasks"][subtaskID]["progress"]
        elif progress == 10:
            task["subTasks"][subtaskID]["progress"] = 10
#        elif:
#            # Do nothing. This must be due to error

        self.TasksTable[taskID] = task

        return 0

    def getAllTasks(self):
        logging.debug("getAllTasks: ")
        tasks = []
        for item in self.TasksTable:
            #tasks.append(self.TasksTable[item])
            # Latest task should be first array item
            tasks.insert(0, self.TasksTable[item])

        return tasks

if __name__ == '__main__':
    '''
    A = Activities()
    taskId = A.createTask({'servers': [{1: '123'},{2:'456'},{3:'789'}]})
    logging.debug(A.setTaskStatus(taskId, "initiated", "nothing"))
    logging.debug(A.getAllTasks())
    '''
    a = DefaultConfig()
    print(a.hostDistroName)
    print(a.htmlPath)

