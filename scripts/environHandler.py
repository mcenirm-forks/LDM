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


# Standard Library imports
import  os
from    os       import environ, system
from    filelock import Timeout, FileLock
import  psutil
import  time

class LDMenvironmentHandler():

    verbose = True

    def __init__(self, exec_prefix, ldmhome, ldm_port, ldm_version):
        
        # Set the $ldmhome variable from the LDMHOME environment variable if available;
        # otherwise, use the configure(1)-determined value. This is necessary for
        # relocated binary RPM installations.

        # Ensure that the utilities of this version are favored
        path = environ.get("PATH")
        environ['PATH'] = f"{exec_prefix}:{ldmhome}/util:{path}";

        unameDict = os.uname()
        lockFile = f"{ldmhome}/.ldmadmin.lck"
        pidFile  = f"{ldmhome}/ldmd.pid"
        
        self.envVariables = { "progname"            : "ldmadmin", 
                              "ldmhome"             : ldmhome, 
                              "os"                  : unameDict.sysname, 
                              "release"             : unameDict.release,
                              "version"             : ldm_version,
                              "port"                : ldm_port,
                              "lock_file"           : lockFile, 
                              "pid_file"            : pidFile, 
                              "lock"                : None,
                              "lock_acquired"       : False,
                              "pq_avg_size"         : 0,
                              "pqact_conf_option"   : 0
                            }
        
    def getEnvVarsDict(self):
        return self.envVariables


    def prettyPrintEnvVars(self):
        print(f"\n--> Environment Variables:\n")
        for k, v in self.envVariables.items():
            print(f"\t{k} \t{v}")

    # Resets the LDM registry.
    def resetRegistry(self):
        status = 1  # default failure
        ret = system("regutil -R")
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

    system('clear')

    # configure.ac replaces "@variable@"with actual value:
    ldmHome     = environ.get("LDMHOME", "/home/miles/dev")
    ldm_port    = "1.0.0.0"
    ldm_version = "6.13.14"

    # For testing purposes:
    ldmHome     = "/home/miles/dev" # <<---- remove in production setting !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    exec_prefix = ""

    # Testing...
    c = LDMenvironmentHandler(exec_prefix, ldmHome, ldm_port, ldm_version)
#    c.getLock()
    dico = c.getEnvVarsDict()
    
#    c.verbose and print("\n\n\tReleasing the lock...\n")
#    c.releaseLock()
    print("\n\t Environment Variables:\n")
    for k, v in dico.items():
        print(f"{k} \t\t{v}")


    