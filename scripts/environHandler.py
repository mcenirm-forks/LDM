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
import time

class LDMenvironmentHandler:

    verbose = True

    def __init__(self):
        
        # Set the $ldmhome variable from the LDMHOME environment variable if available;
        # otherwise, use the configure(1)-determined value. This is necessary for
        # relocated binary RPM installations.
        
        ldmhome = os.environ.get("LDMHOME", "/home/miles/projects/ldm")

        # Ensure that the utilities of this version are favored
        os.environ['PATH'] = f"{ldmhome}/bin:{ldmhome}/util:{os.environ['PATH']}"

        unameDict = os.uname()
        lockFile = f"{ldmhome}/.ldmadmin.lck"
        pidFile  = f"{ldmhome}/ldmd.pid"
        
        self.envVariables = { "progname": "ldmadmin", 
                              "ldmhome": ldmhome, 
                              "os": unameDict.sysname, 
                              "release": unameDict.release,
                              "lock_file": lockFile, 
                              "pid_file": pidFile, 
                              "lock": None,
                              "lock_acquired" : False,
                              "pqact_conf_option" : 0}
        
    def getEnvVarsDict(self):
        return self.envVariables


    def prettyPrintEnvVars(self):
        print(f"\n--> Environment Variables:\n")
        for k, v in self.envVariables.items():
            print(f"\t{k} \t{v}")

    # Resets the LDM registry.
    def resetRegistry(self):
        status = 1  # default failure
        ret = os.system("regutil -R")
        if not ret == 0:
            errmsg("Couldn't reset LDM registry")
        else:
            status = 0

        return status;


    # Lock the lock-file.
    def getLock(self):
        
        status = 0

        fileToLock = self.envVariables['lock_file']
        lock = FileLock(fileToLock)
        acquired = self.envVariables['lock_acquired']

        if not acquired:
            lock.acquire(timeout=20)
            self.envVariables['lock_acquired'] = True
            self.envVariables['lock'] = lock
            #self.verbose and print("Lock acquired.")
        else:
            self.verbose and print(f"\nLock already acquired: lockID: {lock}\n")
            return status

        #self.verbose and print(f"\n acquired: {self.envVariables['lock_acquired']}\n")
        #self.verbose and print(f"\n lockID: {self.envVariables['lock']}\n")
        
        return status

    def forceLockRelease(self):

        lock = self.envVariables['lock']
        self.verbose and print(f"\n lockID: {self.envVariables['lock']}\n")
        lock.release()


    def releaseLock(self):

        acquired = self.envVariables['lock_acquired']
        # close(LOCKFILE); lock.release() if already acquired
        if acquired != None: 
            try:
                # self.verbose and print(f"Attempt to acquire the lock BEFORE releasing it...")
                # fileToLock = self.envVariables['lock_file']
                # self.verbose and print(f"FileLock-ing..")
                # lock = FileLock(fileToLock, timeout=100)
                # self.verbose and print(f"Acquire-ing..")
                # lock.acquire(timeout=10)
                # self.verbose and print(f"Successfulllly Acquired!..")

                #self.verbose and print(f"Releasing it NOW...")
                self.envVariables['lock'].release()
                
                self.envVariables['lock_acquired'] = False
                self.envVariables['lock'] = None
                
                #self.verbose and print(f"releaseLock(): lock released.")

            except Timeout:
                self.verbose and print(f"releaseLock(): Could not release lock!")
        else:
            self.verbose and print(f"releaseLock(): lock NOT acquired.");
    

if __name__ == "__main__":

    os.system('clear')

    # Testing...
    c = LDMenvironmentHandler()
#    c.getLock()
    dico = c.getEnvVarsDict()
    
#    c.verbose and print("\n\n\tReleasing the lock...\n")
#    c.releaseLock()
    print("\n\t Environment Variables:\n")
    for k, v in dico.items():
        print(f"{k} \t\t{v}")


    