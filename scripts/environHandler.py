#
#
# Description: This Python module provides support to handle all
# environment variables to run the ldmadmin script
#
#
#   @file:  environHandler.py
# @author:  Mustapha Iles
#
#    Copyright 2021 University Corporation for Atmospheric Research
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
##############################################################################



# Set the $ldmhome variable from the LDMHOME environment variable if available;
# otherwise, use the configure(1)-determined value. This is necessary for
# relocated binary RPM installations.



import os
from filelock import Timeout, FileLock
import psutil


class LDMenvironmentHandler:

    def __init__(self):
        
        # Set the $ldmhome variable from the LDMHOME environment variable if available;
        # otherwise, use the configure(1)-determined value. This is necessary for
        # relocated binary RPM installations.
        
        ldmhome = os.environ.get("LDMHOME", "")

        # Ensure that the utilities of this version are favored
        os.environ['PATH'] = f"{ldmhome}/bin:{ldmhome}/util:{os.environ['PATH']}"

        #print(f"PATH: {os.environ['PATH']}")

        # srand;  # called once at start

        unameDict = os.uname()
        lockFile = f"{ldmhome}/.ldmadmin.lck"
        pidFile  = f"{ldmhome}/ldmd.pid"
        
        self.envVariables = { "progname": "ldmadmin", "ldmHome": ldmhome, "os": unameDict.sysname, "release": unameDict.release,
                            "lock_file": lockFile, "pid_file": pidFile, "pqact_conf_option" : 0}
        
        # Check if lock was released first
        self.createLock()



    def getEnvVarsDict(self):
        return self.envVariables


    # Resets the LDM registry.
    def resetRegistry(self):
        status = 1  # default failure
        ret = os.system("regutil -R")
        if not ret == 0:
            errmsg("Couldn't reset LDM registry")
        else:
            status = 0

        return status;

    def createLock(self):

        fileToLock = self.envVariables['lock_file']

        lock = FileLock(fileToLock)

        print("Lock created once.")
        self.envVariables['file_lock'] = lock


    # Lock the lock-file.
    def getLock(self):
        
        status = 0
        lock = ""
        lock = self.envVariables['file_lock']

        if not lock == None:
            lock.acquire()
            self.envVariables['file_lock_acquired'] = True            
        else:
            status = -1
            print(f"getLock(): Couldn't lock lock-file \"{self.envVariables['lock_file']}\". \
                    \nAnother ldmadmin(1) script is likely running.");
        
        # close(LOCKFILE); lock.release() if already acquired
        return status



    # Unlock the lock file.
    def releaseLock(self):
        
        acquired = self.envVariables['file_lock_acquired']
        # close(LOCKFILE); lock.release() if already acquired
        if acquired:
            try:
                self.envVariables['file_lock'].release()
                #self.envVariables['file_lock'] = None      # keep the same lock handle in the dictionary
                self.envVariables['file_lock_acquired'] = False
                print(f"lock released.")

            except:
                print(f"Could not released lock!")
        else:
            print(f"releaseLock(): lock NOT acquired: \"{self.envVariables['lock_file']}\".");
    

    def isRunning(self):
        
        running     = -1
        pidFilename = self.envVariables['pid_file']
        ip_addr     = self.envVariables['ip_addr']

        pid = 0
        with open(pidFilename, 'r') as pidFile:
            pidStr = pidFile.read().replace('\n','')
        pid = int(pidStr)
        
        if psutil.pid_exists(pid):
            running = 0
        else:
            #print(f"process with pid {pid} does not exist!")
            
            # The following test is incompatible with the use of a proxy

            cmd_line = "echo ldmping -l- -i 0"
            if not ip_addr == "0.0.0.0":
                cmd_line = f"{cmd_line}  {ip_addr}"
            
            cmd_line = f"{cmd_line} > /dev/null 2>&1"
            running = os.system( cmd_line )
            
            #print(f" Running status: {running}")

        return running

# Testing...
# c = LDMenvironmentHandler()
# c.getLock()
# dico = c.getEnvVarsDict()
# print(dico)
# print("\n\n\tReleasing the lock...\n")
# c.releaseLock()
# print(dico)


