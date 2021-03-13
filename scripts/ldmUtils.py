import os
from parseRegistry import RegistryParser
from environHandler import LDMenvironmentHandler
import psutil
import time

import subprocess
from subprocess import PIPE

import glob
from os import path
from pathlib import Path
from random import randrange

###############################################################################
# Helper functions: they star with _undescore_ to distinguish them from 
#                    ldmadmin-specific Perl routines
###############################################################################


def _increaseQueue(reg, envVar, pqMonValues):

    ageOldest       = pqMonValues[1] 
    minVirtResTime  = pqMonValues[2] 
    mvrtSize        = pqMonValues[3] 
    mvrtSlots       = pqMonValues[4] 
    maxLatency      = pqMonValues[5] 

    newByteCount, newSlotCount = computeNewQueueSize(maxLatency, minVirtResTime, ageOldest, mvrtSize, mvrtSlots)
    
    pq_path      = reg["pq_path"]
    newQueuePath = f"{pq_path}.new"

    print(f"\n\t- Increasing the capacity of the queue to {newByteCount} bytes and {newSlotCount} slots...")

    pqcreate_cmd = f"pqcreate -c -S {newSlotCount} -s {newByteCount} -q {newQueuePath}"
    print(f"\n\t\t{pqcreate_cmd}")

    if os.system(pqcreate_cmd):
        errmsg(f"vetQueueSize(): Couldn't create new queue: {newQueuePath}")
        status = 2            # major failure
        return status
    
    print(f"\n\t\tCreated new QUEUE: {newQueuePath}")

    exit(0)

    restartNeeded = 0
    status = 0            # success so far

    if isRunning(reg, envVar): 
        if stop_ldm(): 
            status = 2        # major failure
            return status
        else:
            restartNeeded = 1
    

    # success so far
    # LDM is stopped
    if grow(pq_path, newQueuePath): 
        status = 2        # major failure
        return status
    
    print("Saving new queue parameters...\n")
    if saveQueuePar(newByteCount, newSlotCount):
        status = 2    # major failure
        return status
        
    
    # success so far
    # restart needed
    if restartNeeded: 
        print("Restarting the LDM...\n")
        if start_ldm():
            errmsg("vetQueueSize(): Couldn't restart the LDM")
            status = 2    # major failure
            return status
        
    # reset queue metrics
    # mode is increase queue
    os.system("pqutil -C")  
    return status



def _decreaseQueue():
    
    #2. recon == decrease  
    
    if 0 >= minVirtResTime:
        # Use age of oldest product, instead
        minVirtResTime = ageOldest
    
    # if 0 >= ageOldest then minVirtResTime = 1
    if 0 >= minVirtResTime:
        minVirtResTime = 1 
    
    newMaxLatency = minVirtResTime
    newTimeOffset = newMaxLatency

    print(f"vetQueueSize(): Decreasing the maximum acceptable latency and \
        \nthe time-offset of requests (registry parameters 'regpath" + "{MAX_LATENCY}" \
        "' and 'regpath" + "{TIME_OFFSET}" + "') to {newTimeOffset} seconds...")


    print("Saving new time parameters...\n")
    if saveTimePar(newTimeOffset, newMaxLatency):
        status = 2    # major failure
        return status
    

    # new time parameters saved
    if not isRunning(reg, envVar):
        status = 0    # success : LDM is not running
    
    else: # LDM is running
    
        print("Restarting the LDM...\n")
        if stop_ldm():
            errmsg("vetQueueSize(): Couldn't stop LDM")
            status = 2        # major failure
            return status
        
        # LDM stopped
        if start_ldm():
            errmsg("vetQueueSize(): Couldn't start LDM")
            status = 2    # major failure
            return status
        
        status = 0     # success
        

    # reset queue metrics
    os.system("pqutil -C")     
    return status


def _doNothing(pqMonValues):

    ageOldest       = pqMonValues[1] 
    minVirtResTime  = pqMonValues[2] 
    mvrtSize        = pqMonValues[3] 
    mvrtSlots       = pqMonValues[4] 
    maxLatency      = pqMonValues[5] 

    newByteCount, newSlotCount = computeNewQueueSize(maxLatency, minVirtResTime, ageOldest, mvrtSize, mvrtSlots)
    
    error_msg = f"vetQueueSize(): The queue should be {newByteCount} \
        bytes in size with {newSlotCount} slots or the \
        maximum-latency parameter should be decreased to \
        {minVirtResTime} seconds. You should set \
        registry-parameter 'regpath" + "{RECONCILIATION_MODE}" + " \
        to 'increase queue' or 'decrease max latency' or \
        manually adjust the relevant registry parameters and recreate the queue."
    errmsg(error_msg)
    status = 1        # small queue or big max-latency
    return status


def _getMTime(aPath):
    mtime = Path(aPath).stat().st_mtime
    return int(mtime)


def _getTheseRegVariables(reg):

    servers             = reg['ntpdate_servers']
    command             = reg['ntpdate_command']
    timeout             = int(reg['ntpdate_timeout'])
    serversCount        = len(servers)
    time                = int(reg['check_time_enabled'])
    time_limit          = int(reg['check_time_limit'])
    warn_disabled       = int(reg['warn_if_check_time_disabled'])
    cmd_xpath           = "regutil -s path regpath{NTPDATE_COMMAND}"
    regUtil_cmd         = f"regutil -u 1 {time}"

    return  servers, command, timeout, serversCount, time, time_limit, warn_disabled, cmd_xpath, regUtil_cmd


def _isCheckTimeEnabled(time, warning_disabled, regUtil_cmd):
    failure = 0

    if time == 0:        
        if warn_disabled == 1:
            print("WARNING: The checking of the system clock is disabled.")
            print("You might loose data if the clock is off.  To enable this ")
            print("checking, execute the command {regUtil_cmd}")
        failure = 1

    return failure



def _areNTPServersAvailable( number_of_servers):
    failure = 0
    if number_of_servers == 0: 
        ntpdate_servers_xpath = f"/check-time/ntpdate/servers"
        warning = f"\nWARNING: No time-servers are specified by the registry \
                    \nparameter '{ntpdate_servers_xpath}'. Consequently, the \
                    \nsystem clock can't be checked and you might loose data if it's off."
        print(warning)
        failure = 1

    return failure



def _executePqMon(pq_path):

    failure = 0
    pqmon_cmd_line = f"pqmon -S -q {pq_path}  2>&1"

    try:
        process_output = subprocess.check_output( pqmon_cmd_line, shell=True )
        pqmon_output  = process_output.decode()[:-1]
        return failure, pqmon_output

    except:
        errmsg(f"Error: '{pqmon_cmd_line}' FAILED!")
        failure = -1
        return failure, ""


###############################################################################
# print the LDM configuration information
###############################################################################

def ldmConfig(reg, env):

    print(f"\n")
    print(f"hostname:              { reg['hostname'] }")
    print(f"os:                    { env['os'] }")
    print(f"release:               { env['release'] }")
    print(f"ldmhome:               { env['ldmhome'] }")
    print(f"LDM version:           6.13.14.15")
    print(f"PATH:                  { os.environ['PATH'] }")

    print(f"LDM conf file:         { reg['ldmd_conf'] }")
    print(f"pqact(1) conf file:    { reg['pqact_conf'] }")
    print(f"scour(1) conf file:    { reg['scour_file'] }")
    print(f"product queue:         { reg['pq_path'] }")
    print(f"queue size:            { reg['pq_size'] } bytes")
    print(f"queue slots:           { reg['pq_slots'] }")
    print(f"reconciliation mode:   { reg['reconMode'] }")
    print(f"pqsurf(1) path:        { reg['surf_path'] }")
    print(f"pqsurf(1) size:        { reg['surf_size'] }")
    if reg['ip_addr'] == None:
        reg['ip_addr'] = "all"
    print(f"IP address:            { reg['ip_addr'] }")       #, length({ reg['ip_addr) ? { reg['ip_addr : "all")
    if reg['port'] == None:
        reg['port'] = "388"
    print(f"port:                  { reg['port'] }")          #, length({ reg['port) ? { reg['port : 388) 
    print(f"maximum clients:       { reg['max_clients'] }")
    print(f"maximum latency:       { reg['max_latency'] }")
    print(f"time-offset limit:     { reg['server_time_offset'] }")    
    # ntp
    print(f"ntpdate(1):            { reg['ntpdate_command'] }")
    print(f"ntpdate(1) timeout:    { reg['ntpdate_timeout'] }")
    print(f"check time:            { reg['check_time_enabled'] }")
    print(f"check-time limit:      { reg['check_time_limit'] }")
    print(f"ntpdate servers:       { ' '.join(reg['ntpdate_servers']) }")

    print(f"log file:              { reg['log_file'] }")
    print(f"numlogs:               { reg['num_logs'] }")
    print(f"log_rotate:            { reg['log_rotate'] }")
    print(f"netstat:               { reg['netstat'] }")
    print(f"top:                   { reg['top'] }")
    print(f"metrics file:          { reg['metrics_file'] }")
    print(f"metrics files:         { reg['metrics_files'] }")
    print(f"num_metrics:           { reg['num_metrics'] }")
    
    print(f"delete info files:     { reg['delete_info_files'] }")

    # environment vars    
    print(f"PID file:              { env['pid_file'] }")
    print(f"Lock file:             { env['lock_file'] }")
        
    print("\n")



###############################################################################
# Check the size of the queue.
###############################################################################


def grow(pq_path, newQueuePath): 
    status = 1                    # failure default

    print("Copying products from old queue to new queue...\n")
    pqcopy_cmd = f"pqcopy {pq_path} {newQueuePath}"
    if os.system(pqcopy_cmd):
        errmsg("grow(): Couldn't copy products")
        return status
    
    print("Renaming old queue\n")
    pqmvf_cmd = f"mv -f {oldQueuePath} {oldQueuePath}.old"
    if os.system(pqmvf_cmd):
        errmsg("grow(): Couldn't rename old queue")
        return status
    
    print("Renaming new queue\n")
    pqmv_cmd = f"mv {newQueuePath} {oldQueuePath}"
    if os.system(pqmv_cmd):
        errmsg("grow(): Couldn't rename new queue")
        return status

    print("Deleting old queue\n")
    pqunlink_cmd = f"unlink {oldQueuePath}.old"
    if os.system(pqunlink_cmd) != 1:   # check this system return!
        errmsg("grow(): Couldn't delete old queue")
        return status
                               
    print("Restoring old queue\n")
    pqmvf_cmd = f"mv -f {oldQueuePath}.old {oldQueuePath}"
    if os.system(pqmvf_cmd):
        errmsg("grow(): Couldn't restore old queue")
        status = 1
        return status

    status = 0                     
    return status


def errmsg(msg):
    print(f"\n\tERROR: {msg}")


def saveQueuePar(pq_size, size, slots):
    status = 1                     # failure default

    regutil_cmd = f"regutil -u {size} regpath" + "{QUEUE_SIZE}"
    if os.system(regutil_cmd):
        errmsg("saveQueuePar(): Couldn't save new queue size")
        return status

    regutil_cmd = f"regutil -u {slots} regpath" + "{QUEUE_SLOTS}"
    if os.system(regutil_cmd):
        errmsg("saveQueuePar(): Couldn't save queue slots")

        print("Restoring previous queue size\n")
        regutil_cmd = f"regutil -u {pq_size} regpath" + "{QUEUE_SIZE}"
        if os.system(regutil_cmd):
            errmsg("saveQueuePar(): Couldn't restore previous queue size")

    else:
        pq_size = size      # <- WHAT use?
        pq_slots= slots     # <- WHAT use?

        status = 0                # success

    return status


def saveTimePar(newTimeOffset, newMaxLatency):

    status = 1                     # failure default

    regutil_cmd = f"regutil -u {newTimeOffset} regpath" + "{TIME_OFFSET}"
    if os.system(regutil_cmd):
        errmsg("saveTimePar(): Couldn't save new time-offset")
    
    else:
        regutil_cmd = f"regutil -u {newMaxLatency} regpath" + "{MAX_LATENCY}"
        if os.system(regutil_cmd):
            errmsg("saveTimePar(): Couldn't save new maximum acceptable latency")

            print("Restoring previous time-offset\n")
            regutil_cmd = f"regutil -u {offset} regpath" + "{TIME_OFFSET}"
            if os.system(regutil_cmd):
                errmsg("saveTimePar(): Couldn't restore previous time-offset")
            
        else:
            offset = newTimeOffset      # WHY these 2 assigments???
            max_latency = newMaxLatency # WHY these 2 assigments???

            status = 0                # success

    return status



# Returns new size parameters for the product-queue
#
# Arguments:
#       minVirtResTime          The minimum virtual residence time in seconds.
#       oldestProductAge        The age of the oldest product in the queue in
#                               seconds.
#       mvrtSize                The amount of space used in the queue for data
#                               in bytes.
#       mvrtSlots               The number of slots used in the queue for 
#                               products.
# Returns:
#       [0]                     The new size for the queue in bytes.
#       [1]                     The new number of slots for the queue.

def computeNewQueueSize(max_latency, minVirtResTime, oldestProductAge, mvrtSize, mvrtSlots):

    print(max_latency, minVirtResTime, oldestProductAge, mvrtSize, mvrtSlots)

    if 0 >= minVirtResTime:
        # Use age of oldest product, instead
        minVirtResTime = oldestProductAge
    
    newByteCount = 0
    newSlotCount = 0
    if 0 < minVirtResTime:
        ratio = max_latency / minVirtResTime
        newByteCount = int(ratio * mvrtSize)
        newSlotCount = int(ratio * mvrtSlots)
        
        print(f"ratio: {ratio} mvrtSize: {mvrtSize}")
        print(f"ratio: {ratio} mvrtSlots: {mvrtSlots}")
    else:
        # Insufficient data
        print("Insufficient data")
        newByteCount = mvrtSize   # Don't change
        newSlotCount = mvrtSlots  # Don't change

    print( newByteCount, newSlotCount )
    exit(0)

    return newByteCount, newSlotCount


# Returns the elapsed time since the LDM server was started, in seconds.
#
# Returns:
#       -1      The LDM system isn't running.
#       else    The elapsed time since the LDM server was started, in seconds.
#
def getElapsedTimeOfServer(reg, envVar):

    if isRunning(reg, envVar, True):
        pid_file    = envVar["pid_file"] 
        pid_time = _getMTime(pid_file)
        return time.time() - pid_time

    print("getElapsedTimeOfServer: LDM is NOT running!...")
    return -1



# Returns
#       0       Success. Nothing wrong or it's too soon to tell.
#       1       The queue is too small or the maximum-latency parameter is
#               too large.
#       2       Major failure.
#
def vetQueueSize(reg, envVar):

    print("\n\t>> vetQueueSize()\n")
    status      = 2          # default major failure
    pid_file    = envVar["pid_file"] 
    ip_addr     = reg["ip_addr"]
    max_latency = int(reg["max_latency"])
    etime       = getElapsedTimeOfServer(reg, envVar)

    if etime < max_latency:
        status = 0                    # too soon to tell
        return status
    
    pq_path = reg["pq_path"]
    status, pq_line = _executePqMon(pq_path)
    if status == -1:
        errmsg("vetQueueSize(): pqmon(1) failure")
        status = 2
        return status

    #print(f"\n\tpqmon: {pq_line}\n")

    isFull          = int(pq_line.split()[0])
    ageOldest       = int(pq_line.split()[7])
    minVirtResTime  = int(pq_line.split()[9])
    mvrtSize        = int(pq_line.split()[10])
    mvrtSlots       = int(pq_line.split()[11])

    pqMonElements = [isFull, ageOldest, minVirtResTime, mvrtSize, mvrtSlots, max_latency]

    print(f"\n\tisFull: {isFull}, ageOldest: {ageOldest}, minVirtResTime: {minVirtResTime}, mvrtSize: {mvrtSize}, mvrtSlots: {mvrtSlots}, max_latency: {max_latency}")

    # A- No reconciliation needed
    ##############################
    if 0:
        if isFull == 0 or minVirtResTime < 0 or minVirtResTime >= max_latency or mvrtSize <= 0 or mvrtSlots <= 0:
            status = 0
            print("    # A- No reconciliation needed")
            return status


    # B- Reconciliation needed
    ##########################
    print("    # B- Reconciliation needed")

    max_latency         = reg["max_latency"]
    reconMode           = reg["reconMode"]
    
    error_msg = f"vetQueueSize(): The maximum acceptable latency \
        \n(registry parameter 'MAX_LATENCY': {max_latency} seconds) is greater \
        \nthan the observed minimum virtual residence time of \
        \ndata-products in the queue ({minVirtResTime} seconds).  \
        \nThis will hinder detection of duplicate data-products."
    errmsg(error_msg)

    print(f'\nINFO: The value of the registry parameter "RECONCILIATION_MODE" is "{reconMode}"\n')

    reconMode = "increase queue"
#    reconMode = "decrease maximum latency"
#    reconMode = "do nothing"
    print(f"For testing purposes: set reconMode == {reconMode}")
    
    #1.
    if reconMode == "increase queue":
        return _increaseQueue(reg, envVar, pqMonElements)
    
    #2.
    if reconMode == "decrease maximum latency":
        return _decreaseQueue(reg, envVar)

    #3.
    if reconMode == "do nothing":
        return _doNothing(pqMonElements)

    #4. else
    errmsg(f"Unknown reconciliation mode: '{reconMode}'")
    status = 2        # major failure
    return status



###############################################################################
# check if the LDM is running.  return 0 if running, -1 if not.
###############################################################################

def isRunning(reg, envir, ldmpingFlag):    

    print(f"\n\t>>> isRunning() ? ( LDM )...")
    # init
    running                 = False
    pid                     = 0  
    pidFilename             = envir['pid_file']
    ip_addr                 = reg['ip_addr']
    envir['ldmd_running']   = False

    ldmhome = os.environ.get("LDMHOME", None)

    if ldmhome == None:
        errmsg(f"\n\tLDMHOME is not set. Bailing out...\n")
        exit(-1)

    # Ensure that the utilities of this version are favored
    os.environ['PATH'] = ldmhome + "/bin:" + ldmhome + "/util:" + os.environ['PATH']

    # Retrieve ldmd process id (if running):
    with open(pidFilename, 'r') as pidFile:
        pid = pidFile.read().replace('\n','')

    pid     = int(pid)

    status = psutil.pid_exists(pid)

    if psutil.pid_exists(pid):
        #print(f"\n\tprocess with pid { pid } exists!\n")
        envir['pid'] = pid
        running = True
        envir['ldmd_running'] = True
        return running
    

    # The following test is incompatible with the use of a proxy
    if not running and ldmpingFlag:

        cmd_line = "ldmping -l- -i 0"
        if not ip_addr == "0.0.0.0":
            cmd_line = f"{ cmd_line }  { reg['ip_addr'] }"
        
        cmd_line = f"{ cmd_line } > /dev/null 2>&1"
        running = os.system( cmd_line )
        if running:
            envir['ldmd_running'] = True

    return running



###############################################################################
# Check that a data-product has been inserted into the product-queue
###############################################################################

def check_insertion(reg):

    print("\n\t>> check_insertion()")
    status = 0

    pq_path = reg["pq_path"]
    status, pq = _executePqMon(pq_path)
    if status == -11:
        errmsg("check_insertion(): pqmon(1) failure")
        return status

    print(f"\n\t --> pqmon: {pq}")

    age= pq.split()[8]
    insertion_check_period = reg["insertion_check_period"]

    if age > insertion_check_period:
        errmsg(f'\tThe last data-product was inserted {age} seconds ago, \
                \nwhich is greater than the registry - parameter "INSERTION_CHECK_INTERVAL" ({insertion_check_period})')
        status = -1

    return status


###############################################################################
# rotate the specified log file, keeping 'numlog' files
###############################################################################

def newLog(reg):

    status = 1      # default failure

    # Rotate the log file
    newlog_cmd = f"newlog {reg['log_file']} {reg['num_logs']}"
    status = os.system(newlog_cmd)

    if status != 0:
        errmsg("new_log(): log rotation failed")
    else:
        # Refresh logging
        refresh_logging_cmd = f"refresh_logging"
        status = os.system(refresh_logging_cmd)
        if status != 0:
            errmsg("new_log(): Couldn't refresh LDM logging")
        else:
            status = 0        # success
    
    return status


def _getMTime(aPath):

    mtime = Path(aPath).stat().st_mtime
    return int(mtime) 


###############################################################################
# Remove product-information files that are older than the LDM pid-file.
###############################################################################

def removeOldProdInfoFiles(env, pid_file):

    mtime = _getMTime(pid_file)
    
    for file in glob.glob('.*.info'):
        file_mTime = _getMTime(file)

        if file_mTime < mtime:
            remove_cmd = f"rm -f {file} 2>/dev/null"
            os.system(remove_cmd)



###############################################################################
# Check the LDM system.
###############################################################################

def checkLdm(envVar):

    status   = 0
    pid_file = envVar['pid_file']
    ip_addr  = envVar['ip_addr']

    print("Checking for a running LDM system...\n")
    if not isRunning(reg, envVar, True):
        print("The LDM server is not running")
        status = 2
    
    else:
        print("Checking the system clock...\n")
        if checkTime():
            status = 3
        
        else:
            print("Checking the most-recent insertion into the queue...\n")
            if check_insertion():
                status = 4
            
            else:
                print("Vetting the size of the queue against the maximum acceptable latency...\n")
                if vetQueueSize():
                    status = 5
                
                else:
                    status = 0

    return status


def _executeNtpDateCommand(ntpdate_cmd, timeout, ntpServer):

    ntpdate_ls_cmd = f"ls {ntpdate_cmd}  2>&1>/dev/null"
    # Check the ntpdate command
    try:
        proc = subprocess.check_output(ntpdate_ls_cmd, shell=True )

    except Exception as e:
        errmsg(f"'ntpdate' command: {ntpdate_cmd} could not be found! ")
        return -1, -1

    # call ntpdate to compute offset    
    offsetParam = 0.0
    try:
        ntpdate_cmd_line = f"{ntpdate_cmd} -q -t {timeout} {ntpServer}  2>&1"

        #print(ntpdate_cmd_line)
        process_output = subprocess.check_output( ntpdate_cmd_line, shell=True )
        #print(process_output)
        offsetParam  = process_output.decode().split()[5][:-1]
        
        return 0, float(offsetParam)
    except:
        #print(f"{ntpServer} is not responding...{offsetParam}")
        return -2, -1
    

###############################################################################
# Check the system clock
###############################################################################

def checkTime(reg):
    
    failure = 0

    ntpdate_servers, ntpdate_cmd,\
    ntpdate_timeout, number_of_servers,\
    check_time, check_time_limit,\
    warn_if_check_time_disabled,\
    ntpdate_cmd_xpath, regUtil_cmd =  _getTheseRegVariables(reg)

    failure = _isCheckTimeEnabled(check_time, warn_if_check_time_disabled, regUtil_cmd)
    if failure == 1:
        return failure
 
    failure = _areNTPServersAvailable( number_of_servers)
    if failure == 1:
        return failure

    
    offset = -10000
    nbServs = number_of_servers

    while nbServs > 0:
        i = randrange( nbServs )
        timeServer = ntpdate_servers[i]

        # execute ntpdate on available servers    
        print(f"\n\tChecking time from NTP server: {timeServer}")
        status, offset = _executeNtpDateCommand(ntpdate_cmd, ntpdate_timeout, timeServer)
        print(f"\tOffset: {offset}\n")

        if status == -1:
            error = f"\nCould not execute the command '{ntpdate_cmd}'. \
                    \nExecute the command '{ntpdate_cmd_xpath}' to set the pathname of \
                    \nthe ntpdate(1) utility to 'path'."
            errmsg(error)
            return -1

        
        if status == -2:
            error = f'\nCould not get time from time-server at {timeServer} using the ntpdate(1) \
                    \nutility, {ntpdate_cmd} \
                    \nIf the utility is valid and this happens often, then remove {timeServer} \
                    \nfrom registry parameter regpath "NTPDATE_SERVERS"'

            errmsg(error)
            nbServs -= 1
            # remove this time server from list:
            ntpdate_servers.remove(timeServer)

            # check if no more valid server remain to try out:
            if len(ntpdate_servers) == 0:
                error = f"\nThere were no valid time servers that could be used to get time from. \
                            \nPlease check the registry parameter 'regutil regpath" + "{NTPDATE_SERVERS}" + "'."
                errmsg(error)
                return(-1)

            # continue with remaining servers
            #print(ntpdate_servers)
            continue

        else:
           
            if abs(offset) > check_time_limit:
                error = f"\nThe system clock is more than {check_time_limit} seconds off, \
                            \nwhich is specified by registry parameter 'regpath" + "{CHECK_TIME_LIMIT}" + "'."
                errmsg(error)

            else:
                failure = 0
            
            break


            # print(f"Offset: {offset}")

    
    if failure == 1:

        checkTime_cmd = "\"regutil -u 0 regpath{CHECK_TIME}\""
        errmsg(f"\nYou should either fix the problem (recommended) or disable\
                \ntime-checking by executing the command {checkTime_cmd} (not recommended)." )
    
    return failure



###############################################################################
# start the LDM server
###############################################################################

def start(reg):

    status      = 0     # default success
    debug       = 1
    verbose     = 1
    ldmd_conf   = reg["ldmd_conf"]
    ip_addr     = reg["ip_addr"]
    port        = reg["port"]
    max_clients = reg["max_clients"]
    max_latency = reg["max_latency"]
    offset      = reg["server_time_offset"]
    pq_path     = reg["pq_path"]

    # Build the 'ldmd' command line
    ldmd_cmd = f"ldmd -I {ip_addr} -P {port} -M {max_clients} -m {max_latency} -o {offset} -q {pq_path}"

    if debug:
        ldmd_cmd += " -x"
    
    if verbose:
        ldmd_cmd += " -v"
    
    
    # Check the ldm(1) configuration-file
    print(f"Checking LDM configuration-file ({ldmd_conf})...\n")
    line_prefix = ""               # used to indent the print outputs
    prev_line_prefix = line_prefix  
    line_prefix += "    "               # to indent the print outputs
    #( @output ) = `$cmd_line -nvl- $ldmd_conf 2>&1` ;
    # Use a subprocess()?
    ldmd_cmd += f" -nvl- {ldmd_conf} 2>&1"

    print(f"\n\tldmd config: {ldmd_cmd}\n")

    exit(0)


    output = os.system(ldmd_cmd) 
    if output:
        print(f"start(): Problem with LDM configuration-file: {output}\n")
        status = 1
    
    else:
        line_prefix = prev_line_prefix

        print("Starting the LDM server...\n")
        
        ldmd_cmd += f" > {pid_file}"
        #status = os.system("$cmd_line $ldmd_conf > $pid_file")
        status = os.system(ldmd_cmd)
        if status:
            os.unlink(pid_file)
            errmsg("start(): Could not start LDM server")
            status = 1
        
        else:
            # Check to make sure the LDM is running
            while not isRunning(reg, envVar):
                sleep(1)
            
    return status



def start_ldm(reg, envVar):

    status = 0     # default success

    # Make sure there is no other server running
    # print "start_ldm(): Checking for running LDM\n";
    if isRunning(reg, envVar):
        errmsg("start_ldm(): There is another server running, start aborted")
        status = 1
        return status
    # LDM not running
    
    #print("start_ldm(): Checking for PID-file\n")
    pid_file = reg["pid_file"]
    if not path.exists(pid_file):
        error_msg = f'start_ldm(): PID-file "{pid_file}" exists.\
            Verify that all is well and then execute "ldmadmin clean" to clean up.'
        errmsg(error_msg)
        status = 1
        return status
    # PID-file doesn't exist
    

    # Check the queues
    #print("start_ldm(): Checking queues\n")
    if not areQueuesOk():
        errmsg("LDM not started")
        status = 1
        return status
    # product-queue OK

    
    # Ensure that the upstream LDM database doesn't exist
    # print("Attempting to delete upstream LDM database...\n")
    system("uldbutil -d")
        
    # Check the pqact(1) configuration-file(s)
    print("Checking pqact(1) configuration-file(s)...\n")
    prev_line_prefix = line_prefix
    line_prefix += "    "
    if not are_pqact_confs_ok():
        errmsg("")
        status = 1
        return status
    # pqact(1) config-files OK

    line_prefix = prev_line_prefix

    # Rotate the ldm log files if appropriate
    log_rot_cmd = f"mkdir -p `dirname {log_file}`"
    os.system(log_rot_cmd)
    
    if log_rotate:  # 1 or 0
        print("start_ldm(): Rotating log files\n")
        if new_log():
            errmsg("start_ldm(): Couldn't rotate log files")
            status = 1
            return status

    if 0 == status:
        # Reset queue metrics
        system("pqutil -C")
        status = start()

    return status



###############################################################################
# stop the LDM server
###############################################################################

def stop_ldm(reg, envVar):

    status = 0                     # default success
    kill_status = 0

    # check if LDM is running: 0: running, -1: NOT running
    status = isRunning(reg, envVar, True)

    if status != 0:
        errmsg("\nThe LDM server is NOT running or its process-ID is 'unavailable'")
    
    else:
        
        # kill the server and associated processes
        print(" - Stopping the LDM server...\n")
        rpc_pid = envVar['pid']

        kill_rpc_pid_cmd = f"kill {rpc_pid}"
        print(f"\tstop_ldm(): kill RPC pid:  {kill_rpc_pid_cmd}\n")
        kill_status = os.system( kill_rpc_pid_cmd )

        # we may need to sleep to make sure that the port is deregistered
        while isRunning(reg, envVar, True) == 0: 
            print(f" - LDM is still running... Sleep 1 sec.")
            time.sleep(1)
        print(f" - LDM has stopped running... ")

    # Remove the pid file if still there    
    pid_file     = envVar['pid_file']
    pid_filePath = Path(pid_file)
    if pid_filePath.exists() and kill_status == 0:
        
        print(f"\n\tRemoving old product information files")
        # remove product-information files that are older than the LDM pid-file.
        removeOldProdInfoFiles(envVar, pid_file)

        # get rid of the pid file
        print(f"\tUnlinking pid file: {pid_filePath}\n")
        pid_filePath.unlink()

    return status



if __name__ == "__main__":

    os.system('clear')

    regHandler = RegistryParser()
    envHandler = LDMenvironmentHandler()

    registryDict = regHandler.getRegistryEntries()
    envVarDict = envHandler.getEnvVarsDict()
    
    # print the current ldm configuration
    #ldmConfig(registryDict, envVarDict)

    # Check if LDM is running: DONE
    isRunning(registryDict, envVarDict, True)

    envHandler.prettyPrintEnvVars()
    regHandler.prettyPrintRegistry()

    # new log rotation: TO-CHECK
    # newLog(registryDict)

    # LDM stop: DONE
    # stop_ldm(registryDict, envVarDict)

    # LDM start : TO-DO
    # startLdm(registryDict, envVarDict)

    # LDM check
    #checkLdm(envVarDict)

    # print("checkTime:")
    #checkTime(registryDict)



    #status = check_insertion(registryDict)

    # vetQueueSize(registryDict, envVarDict)

    start(registryDict)
