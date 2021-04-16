########################################################################
#
#             ldmd commands functions
#
#########################################################################

# Standard Library imports
import  os
from    os import path
from    pathlib import Path
import  psutil
import  shutil
import  time
import  subprocess
from    subprocess import PIPE
import  glob
from    random import randrange

# Local application imports
import  ldmUtils as util
from    parseRegistry import RegistryParser
from    environHandler import LDMenvironmentHandler

###############################################################################
# print the LDM configuration information
###############################################################################

def ldmConfig(reg, env):

    paths = os.environ['PATH'].split(":")
    first = True
    print(f"\n")
    print(f"\thostname:              { reg['hostname'] }")
    print(f"\tos:                    { env['os'] }")
    print(f"\trelease:               { env['release'] }")
    print(f"\tldmhome:               { env['ldmhome'] }")
    print(f"\tLDM version:           6.13.14.15")
    print("\tPATH:                   ", end="")
    for aPath in paths:
        if aPath:
            first and print(f"{aPath}")
            not first and print(f"\t\t\t\t{aPath}")
            first = False

    print(f"\tLDM conf file:         { reg['ldmd_conf'] }")
    print(f"\tpqact(1) conf file:    { reg['pqact_conf'] }")
    print(f"\tscour(1) conf file:    { reg['scour_file'] }")
    print(f"\tproduct queue:         { reg['pq_path'] }")
    print(f"\tqueue size:            { reg['pq_size'] } bytes")
    print(f"\tqueue slots:           { reg['pq_slots'] }")
    print(f"\treconciliation mode:   { reg['reconMode'] }")
    print(f"\tpqsurf(1) path:        { reg['surf_path'] }")
    print(f"\tpqsurf(1) size:        { reg['surf_size'] }")
    print(f"\tIP address:            { reg['ip_addr'] }")
    print(f"\tport:                  { reg['port'] }")
    print(f"\tmaximum clients:       { reg['max_clients'] }")
    print(f"\tmaximum latency:       { reg['max_latency'] }")
    print(f"\ttime-offset limit:     { reg['server_time_offset'] }")    
    # ntp
    print(f"\tntpdate(1):            { reg['ntpdate_command'] }")
    print(f"\tntpdate(1) timeout:    { reg['ntpdate_timeout'] }")
    print(f"\tcheck time:            { reg['check_time_enabled'] }")
    print(f"\tcheck-time limit:      { reg['check_time_limit'] }")
    print(f"\tntpdate servers:       { ' '.join(reg['ntpdate_servers']) }")

    print(f"\tlog file:              { reg['log_file'] }")
    print(f"\tnumlogs:               { reg['num_logs'] }")
    print(f"\tlog_rotate:            { reg['log_rotate'] }")
    print(f"\tnetstat:               { reg['netstat'] }")
    print(f"\ttop:                   { reg['top'] }")
    print(f"\tmetrics file:          { reg['metrics_file'] }")
    print(f"\tmetrics files:         { reg['metrics_files'] }")
    print(f"\tnum_metrics:           { reg['num_metrics'] }")
    
    print(f"\tdelete info files:     { reg['delete_info_files'] }")

    # environment vars    
    print(f"\tPID file:              { env['pid_file'] }")
    print(f"\tLock file:             { env['lock_file'] }")
        
    print("\n")



###############################################################################
# Check the size of the queue.
###############################################################################


def grow(pq_path, newQueuePath): 

    status          = 1                    # failure default
    oldQueuePath    = pq_path

    print("Copying products from old queue to new queue...\n")
    pqcopy_cmd = f"pqcopy {oldQueuePath} {newQueuePath}"
    if os.system(pqcopy_cmd):
        errmsg("grow(): Couldn't copy products")

    else:
        print("Renaming old queue\n")
        oldQueuePath_old = f"{oldQueuePath}.old"

        if os.rename(oldQueuePath, oldQueuePath_old) != 0:  # check / confirm this return status
            errmsg("grow(): Couldn't rename old queue")

        else:
            print("Renaming new queue\n")
            if os.rename(newQueuePath, oldQueuePath) != 0:
                errmsg("grow(): Couldn't rename new queue")

            else:
                print("Deleting old queue\n")
                oldQueuePath_old =  f"{oldQueuePath}.old"
    
                if os.remove(oldQueuePath_old) != 0:
                    errmsg("grow(): Couldn't delete old queue")

                else:
                    status = 0

            
            if status != 0:
                print("Restoring old queue\n")
                oldQueuePath_old =  f"{oldQueuePath}.old"
                if os.rename(oldQueuePath_old, oldQueuePath) != 0:
                    errmsg("grow(): Couldn't restore old queue")

    return status

# Save new size and slots values to registry
def saveQueuePar(reg, env, size, slots):
    status = 1                     # failure default

    ldmhome     = env["ldmhome"]
    regHandler  = RegistryParser(ldmhome)
    
    pq_size     = reg["pq_size"]
    pq_slots    = reg["pq_slots"]
    
    # "size":
    try:
        regHandler.modifyRegistry(regHandler.DOMTree, "size", newSize)
    except Exception as e:
        print(f"SaveQueueParam(2) failed. Could not save 'size' (={newSize}) to registry.xml")
        return status

    # "slots":
    try:
        regHandler.modifyRegistry(regHandler.DOMTree, "slots", newSlots)
    except Exception as e:
        # Try revert 'size' value to pq_size
        try:
            regHandler.modifyRegistry(regHandler.DOMTree, "size", pq_size)
            print("\nSaveQueueParam(1) failed. Restored previous queue size element\n")
        except Exception as ee:
            print("\nSaveQueueParam(1) failed. Could not restore previous queue size elements\n")
            return status

        print(f"SaveQueueParam(2) failed. Could not save 'slots' (={newSlots}) to registry.xml. Nor restore previous 'size'. ")
        return status


    status = 0
    # Update registry dictionary
    reg["pq_size"]  = newSize
    reg["pq_slots"] = newSlots

    return status


# Save new timeOffset and max-latency values to registry
def saveTimePar(reg, env, newTimeOffset, newMaxLatency):
    
    status = 1                     # failure default

    ldmhome     = env["ldmhome"]
    regHandler  = RegistryParser(ldmhome)
    
    timeOffset  = reg["server_time_offset"]
    maxLatency  = reg["max_latency"]
    
    try:
        regHandler.modifyRegistry(regHandler.DOMTree, "max-latency", newMaxLatency)
    except Exception as e:
        print(f"saveTimePar() failed. Could not save 'max-latency' (={newMaxLatency}) to registry.xml")
        return status

    try:
        regHandler.modifyRegistry(regHandler.DOMTree, "time-offset", newTimeOffset)
    except Exception as e:
        # Try revert 'size' change
        try:
            regHandler.modifyRegistry(regHandler.DOMTree,  "max-latency", maxLatency)
            print("\nsaveTimePar() failed. Restored previous 'max-latency' element\n")
        except Exception as ee:
            print("\nsaveTimePar() failed. Could not restore previous 'max-latency' element\n")
            return status

        print("saveTimePar() failed. Could not save 'time-offset' element to registry, nor restore previous 'max-latency'!")
        return status


    status = 0
    # Update registry dictionary
    reg["server_time_offset"]   = newTimeOffset
    reg["max_latency"]          = newMaxLatency

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

    #print(max_latency, minVirtResTime, oldestProductAge, mvrtSize, mvrtSlots)

    if 0 >= minVirtResTime:
        # Use age of oldest product, instead
        minVirtResTime = oldestProductAge
    
    newByteCount = 0
    newSlotCount = 0
    if 0 < minVirtResTime:
        ratio = max_latency / minVirtResTime
        newByteCount = int(ratio * mvrtSize)
        newSlotCount = int(ratio * mvrtSlots)
        
        #print(f"ratio: {ratio} mvrtSize: {mvrtSize}")
        #print(f"ratio: {ratio} mvrtSlots: {mvrtSlots}")
    else:
        # Insufficient data
        #print("Insufficient data")
        newByteCount = mvrtSize   # Don't change
        newSlotCount = mvrtSlots  # Don't change

    #print( newByteCount, newSlotCount )

    return newByteCount, newSlotCount


# Returns the elapsed time since the LDM server was started, in seconds.
#
# Returns:
#       -1      The LDM system isn't running.
#       else    The elapsed time since the LDM server was started, in seconds.
#
def getElapsedTimeOfServer(envVar):

    pid_file    = envVar["pid_file"] 
    pid_time    = util._getMTime(pid_file)

    return time.time() - pid_time


# Returns
#       0       Success. Nothing wrong or it's too soon to tell.
#       1       The queue is too small or the maximum-latency parameter is
#               too large.
#       2       Major failure.
#
def vetQueueSize(reg, envVar):

    status      = 2          # default major failure

    pid_file    = envVar["pid_file"] 
    ip_addr     = reg["ip_addr"]
    max_latency = reg["max_latency"]

    if not isRunning(reg, envVar, True):
        print("\n\tvetQueueSize(): LDMserver is NOT running!...(Please start it and try again.)")
        return status

    etime       = getElapsedTimeOfServer(envVar)
    
    if False:
        if etime < max_latency:
            print(f"\n\tvetQueueSize(): etime: {etime} - max_latency: {max_latency}: Too soon to tell...")
            status = 0                    # too soon to tell
            return status
        
    pq_path = reg["pq_path"]
    status, pq_line = util._executePqMon(pq_path)
    if status == -1:
        errmsg("vetQueueSize(): pqmon(1) failure")
        status = 2
        return status

    isFull          = int(pq_line.split()[0])
    ageOldest       = int(pq_line.split()[7])
    minVirtResTime  = int(pq_line.split()[9])
    mvrtSize        = int(pq_line.split()[10])
    mvrtSlots       = int(pq_line.split()[11])

    pqMonElements = [isFull, ageOldest, minVirtResTime, mvrtSize, mvrtSlots, max_latency]

    #print(f"\n\tisFull: {isFull}, ageOldest: {ageOldest}, minVirtResTime: {minVirtResTime}, mvrtSize: {mvrtSize}, mvrtSlots: {mvrtSlots}, max_latency: {max_latency}")

    # A- No reconciliation needed
    ##############################

    if not (isFull == 0 or minVirtResTime < 0 or minVirtResTime >= max_latency or mvrtSize <= 0 or mvrtSlots <= 0):
        status = 0
        print(f"\n\t\t - No reconciliation needed\
            \n\tisFull: {isFull}, ageOldest: {ageOldest}, minVirtResTime: {minVirtResTime}, mvrtSize: {mvrtSize}, mvrtSlots: {mvrtSlots}, max_latency: {max_latency}")
        return status

    # B- Reconciliation needed
    ##########################
    print("\n\t\t - Reconciliation needed")

    reconMode           = reg["reconMode"]
    # print(f'\nINFO: The value of the registry parameter "RECONCILIATION_MODE" is "{reconMode}"\n')
    warning_msg = f"vetQueueSize(): The maximum acceptable latency (registry parameter 'MAX_LATENCY': {max_latency} seconds) is greater \
        \n\tthan the observed minimum virtual residence time of data-products in the queue ({minVirtResTime} seconds).  \
        \n\tThis will hinder detection of duplicate data-products.\n"
    warnmsg(warning_msg)
    
    reconModMsg = "\tThe value of the 'regpath{RECONCILIATION_MODE}" + f"' registry-parameter is '{reconMode}'\n"
    print(reconModMsg)

    #1.
    if reconMode == "increase queue":
        return increaseQueue(reg, envVar, pqMonElements)
    
    #2.
    if reconMode == "decrease maximum latency":
        return decreaseMaxLatency(reg, envVar, pqMonElements)

    #3.
    if reconMode == "do nothing":
        return doNothing(pqMonElements)

    #4.
    errmsg(f"Unknown reconciliation mode: '{reconMode}'")
    status = 2        # major failure
    return status



def doNothing(pqMonValues):

    ageOldest       = pqMonValues[1] 
    minVirtResTime  = pqMonValues[2] 
    mvrtSize        = pqMonValues[3] 
    mvrtSlots       = pqMonValues[4] 
    maxLatency      = pqMonValues[5] 

    newByteCount, newSlotCount = computeNewQueueSize(maxLatency, minVirtResTime, ageOldest, mvrtSize, mvrtSlots)
    
    error_msg = f"vetQueueSize(): The queue should be {newByteCount} bytes in size with {newSlotCount} slots or the \
        \n\tmaximum-latency parameter should be decreased to {minVirtResTime} seconds. \
        \n\tYou should set registry-parameter 'regpath" + "{RECONCILIATION_MODE}" + " \
        \n\tto 'increase queue' or 'decrease max latency' or manually adjust the relevant registry parameters \
        \n\tand recreate the queue."
    errmsg(error_msg)

    status = 1        # small queue or big max-latency
    
    return status




def increaseQueue(reg, envVar, pqMonValues):

    status          = 0            # success
    restartNeeded   = 0

    ageOldest       = pqMonValues[1] 
    minVirtResTime  = pqMonValues[2] 
    mvrtSize        = pqMonValues[3] 
    mvrtSlots       = pqMonValues[4] 
    maxLatency      = pqMonValues[5] 

    newByteCount, newSlotCount = computeNewQueueSize(maxLatency, minVirtResTime, ageOldest, mvrtSize, mvrtSlots)
    
    pq_path      = reg["pq_path"]
    newQueuePath = f"{pq_path}.new"

    if newByteCount <= 0 or newSlotCount <= 0:
        print(f"\n\t- Cannot increase the capacity of the queue with these values: {newByteCount} bytes and {newSlotCount} slots...")
        status = 1
        return status
    
    print(f"\n\t- Attempting to increase the capacity of the queue to {newByteCount} bytes and {newSlotCount} slots...")

    pqcreate_cmd = f"pqcreate -c -S {newSlotCount} -s {newByteCount} -q {newQueuePath}"
    #print(f"\n\t\t{pqcreate_cmd}")

    if os.system(pqcreate_cmd):
        errmsg(f"vetQueueSize(): Couldn't increase queue: {newQueuePath}")
        status = 2            # major failure
        return status
    
    #print(f"\n\t\tCreated new QUEUE: {newQueuePath}")


    if isRunning(reg, envVar, True): 
        if stop_ldm(): 
            status = 2        # major failure
            return status
    
        restartNeeded = 1
    
    # success so far
    # LDM is stopped
    print("vetQueueSize(): Grow  the queue...\n")
    if grow(pq_path, newQueuePath): 
        status = 2        # major failure
        return status
    
    print("vetQueueSize(): Save new queue parameters: (size, slots)\n")
    if saveQueuePar(reg, envVar, newByteCount, newSlotCount):
        status = 2    # major failure
        return status
        
    
    # success so far
    # restart needed
    if restartNeeded: 
        print("vetQueueSize(): Restarting the LDM server...\n")
        if start_ldm(reg, envVar):
            errmsg("vetQueueSize(): Could not restart LDM server")
            status = 2    # major failure
            return status
        
    # reset queue metrics
    # mode is increase queue
    os.system("pqutil -C")  
    return status



def decreaseMaxLatency(reg, envVar, pqMonValues):
    
    status = 0

    ageOldest       = pqMonValues[1] 
    minVirtResTime  = pqMonValues[2] 
    mvrtSize        = pqMonValues[3] 
    mvrtSlots       = pqMonValues[4] 
    maxLatency      = pqMonValues[5] 

    if 0 >= minVirtResTime:
        # Use age of oldest product, instead
        minVirtResTime = ageOldest
    
    # if 0 >= ageOldest then minVirtResTime = 1
    if 0 >= ageOldest:
        minVirtResTime = 1 
    
    newMaxLatency = minVirtResTime
    newTimeOffset = newMaxLatency

    print(f"\tvetQueueSize(): Decreasing the maximum acceptable latency and the time-offset of requests" +
        "\n\t\t\t(registry parameters 'regpath{MAX_LATENCY}' and 'regpath{TIME_OFFSET}')" + 
        f"\n\t\t\tto {newTimeOffset} seconds...")


    print("\n\tSaving new time parameters to the registry...\n")
    if saveTimePar(reg, envVar, newTimeOffset, newMaxLatency):
        status = 2    # major failure
        return status
    

    # new time parameters saved
    if not isRunning(reg, envVar, True):
        status = 0    # success : LDM is not running
    
    else: # LDM is running
    
        print("Stopping the LDM...\n")
        if stop_ldm(reg, envVar):
            errmsg("vetQueueSize(): Could not stop LDM server")
            status = 2        # major failure
            return status
        
        # LDM stopped
        if start_ldm(reg, envVar):
            errmsg("vetQueueSize(): Could not start LDM server")
            status = 2    # major failure
            return status
        
        status = 0     # success    

    # reset queue metrics
    status = os.system("pqutil -C")     # <-- not tested
    return status


###############################################################################
# check if the LDM is running.  return 0 if running, -1 if not.
###############################################################################

def isRunning(reg, envir, ldmpingFlag):    

    # init
    running                 = False
    pid                     = 0  
    pidFilename             = envir['pid_file']
    ip_addr                 = reg['ip_addr']
    envir['ldmd_running']   = False

    if util._getLdmdPid(pidFilename) != -1:   # valid pid found

        running                 = True
        envir['ldmd_running']   = True
        #print("\n\t\t LDM server is running...\n")
        return running

    # The following test is incompatible with the use of a proxy
    # if not running and ldmpingFlag:

    #     cmd_line = "ldmping -l- -i 0"
    #     if not ip_addr == "0.0.0.0":
    #         cmd_line = f"{ cmd_line }  { reg['ip_addr'] }"
        
    #     cmd_line    = f"{ cmd_line } > /dev/null 2>&1"
    #     output      = os.system( cmd_line ) >> 8

    #     # verbose and print(running)
    #     if output == 1:
    #         running                 = True
    #         envir['ldmd_running']   = True


    # print(running)

    return running



###############################################################################
# Check that a data-product has been inserted into the product-queue
###############################################################################

def check_insertion(reg):

    status = 0

    pq_path     = reg["pq_path"]
    status, pq  = util._executePqMon(pq_path)

    if status == -11:
        errmsg("\tcheck_insertion(): pqmon(1) failure")
        return status

    # debug and print(f"\n\t --> pqmon: {pq}")

    age         = int(pq.split()[8])
    check_period= reg["insertion_check_period"]

    if age > check_period:
        warnmsg(f'The last data-product was inserted {age} seconds ago, \
                \n\t\t which is greater than the registry - parameter "INSERTION_CHECK_INTERVAL" value (={check_period})')
        status = -1
    else:
        print(f"\n\tcheck_insertion(): age ({age}) is lower than the insertion_check_period ({check_period}) as set in the registry.\n")


    return status


###############################################################################
# rotate the specified log file, keeping 'numlog' files
# may apply to either ldm log or metrics log
###############################################################################

def newLog(reg, envVar):

    logFile     = reg['log_file']
    numLogs     = reg['num_logs']

    # different may be set on CLI
    if envVar['log_file'] != None:
        logFile = envVar['log_file']

    if envVar['num_logs'] != None:
        numLogs = envVar['num_logs']
    
    return _newLog(logFile, numLogs)



def newMetrics(reg):

    metricsFile     = reg['metrics_file']
    numMetrics      = reg['nums_metrics']

    return _newLog(metricsFile, numMetrics)

def _newLog(targetFile, num):

    status      = 1      # default failure

    # Rotate the log file

    newlog_cmd = f"newlog {targetFile} {num}"
    status = os.system(newlog_cmd)
    

    if status != 0:
        errmsg("new_log(): file rotation failed")
    else:
        # Refresh logging: is a refresh ok for metrics log too??
        refresh_logging_cmd = f"refresh_logging"
        status = os.system(refresh_logging_cmd)
    
        if status != 0:
            errmsg("new_log(): Couldn't refresh LDM logging")
    
    return status

            
#
# print metrics to file
def printMetrics(reg, flag):

    metricsFilePath = reg['metrics_file']
    port            = reg["port"]
    pq_path         = reg["pq_path"]

    pq_line         = list(util.getPq(pq_path))
    portCount       = list(util.getPortCount(reg, port))
    load            = list(util.getLoad())
    thisTime        = float(util.getTime())
    cpu             = list(util.getCpu(reg))
    
    all_metrics     =  load + portCount + pq_line + cpu 
    all_metrics.insert(0, thisTime)
    all_metrics     = f"{util._listToString(all_metrics)}\n"
    
    time_legend     = "\ttime: \t\tYYYYmmdd.hhmmss"
    load_legend     = "\tuptime (avg at): 1 mn, 5 mn, 15 mn"
    port_legend     = "\tport (count): \tremote, local"
    pq_legend       = "\tpq: \t\tage, prodCount, byteCount"
    cpu_legend      = "\tCPU: \t\tuserTime, sysTime, idleTime, waitTime, memUsed, memFree, swapUsed, swapFree, contextSwitches"

    all_legend      = "\n   time  \t|     uptime     | port |            pq          |   CPU "

    if flag:
        # print to file
        with open(metricsFilePath, "a") as metricsHandle:
            metricsHandle.write(all_metrics)

    else:
        print(all_legend) 
        print(all_metrics)
        # print the legend to the metricsFilePath
        print(f"\nLegend:\n{time_legend}\n{load_legend}\n{port_legend}\n{pq_legend}\n{cpu_legend}\n")


def addMetrics(reg):

    # print metrics to file named in registry
    status = printMetrics(reg, True)
        
    return status


#
# Command for plotting metrics: TO TEST!!!!!!!!!!!!!!!!!!!!!!!!!
def plotMetrics(reg, envVar):

    begin           = envVar['begin']
    end             = envVar['end']
    metrics_files   = reg['metrics_files']
    
    plot_cmd = f"plotMetrics -b {begin} -e {end} {metrics_files}"
    
    return os.system(plot_cmd)



# ###############################################################################
# # HUP the pqact program(s)
# ###############################################################################

def pqactHUP(envVar):

    status = 0
    cmd=""
    ps_cmd, default = util._whichPs(envVar)

    ps_output   = subprocess.check_output(ps_cmd, shell=True).decode()

    ps_lineList = ps_output.split('\n')

    pid_index = default
    pqact_pid = -1
    pqact_pids = ""

    # search for the position (pid_index) of PID
    for ps_line in ps_lineList:
        if 'PPID' in ps_line:
            ps_line_items = ps_line.split()
            try:
                pid_index = ps_line_items.index("PID") 
                
            except:
                errmsg(f"PID position not found in ps output: {ps_line}. Weird!")
    
        else:
            if 'pqact' in ps_line:
                pqact_line_item = ps_line.split()
                try:
                    pqact_pid = pqact_line_item[pid_index] 
                    pqact_pids += f" {pqact_pid}"
                    
                except:
                    errmsg(f"pqact position not found in ps output: {ps_line}. Weird!")
                
    if pqact_pids == "":
        errmsg("ldmadmin_pqactHUP: process not found, cannot HUP pqact\n")
        return status
    
    print("Check pqact HUP with command \"ldmadmin tail\"\n")
    kill_cmd = f"kill -HUP {pqact_pids}"
    
    status = os.system( kill_cmd )

    return status




###############################################################################
# Remove product-information files that are older than the LDM pid-file.
###############################################################################

def removeOldProdInfoFiles(env, pid_file):

    mtime = util._getMTime(pid_file)
    
    for file in glob.glob('.*.info'):
        file_mTime = util._getMTime(file)

        if file_mTime < mtime:
            remove_cmd = f"rm -f {file} 2>/dev/null"
            os.system(remove_cmd)



###############################################################################
# Check the LDM system.
###############################################################################

def checkLdm(reg, envVar):

    status   = 0

    print("\n\tcheckLdm(): 1. Checking for a running LDM server...\n")
    if not isRunning(reg, envVar, True):
        print("\t\t -> The LDM server is not running")
        status = 2
    
    else:
        print("\tcheckLdm(): 2. Checking the system clock...\n")
        if checkTime(reg) != 0:
            status = 3
            print("\n\t\t --> Consequently, skipping check_insertion() and vetQueueSize() checks...\n")

        else:
            print("\tcheckLdm(): 3. Checking the most-recent insertion into the queue...\n")
            if check_insertion(reg) != 0:
                status = 4
                print("\n\t\t --> Consequently, skipping vetQueueSize() check...\n")
            
            else:
                print("\tcheckLdm(): 4. Vetting the size of the queue against the maximum acceptable latency...\n")
                if vetQueueSize(reg, envVar) != 0:
                    status = 5
                
                else:
                    status = 0

    return status


# monitor incoming products
def watch(reg, env):


    feedset = env["feedset"]  # f: feedset
    pq_path = env["pq_path"]

    if not isRunning(reg, env, True):
        errmsg("There is no LDM server running")
        status = 1
    
    else:
        pqutil_cmd = f'pqutil -r -f "{feedset}" -w {pq_path}'
        print(pqutil_cmd)
        status = os.system(pqutil_cmd)
        
    return status


###############################################################################
# Check the system clock
###############################################################################

def checkTime(reg):
    
    failure = 0     # no failure (success)

    ntpdate_servers, ntpdate_cmd,\
    ntpdate_timeout, number_of_servers,\
    check_time, check_time_limit,\
    warn_if_check_time_disabled,\
    ntpdate_cmd_xpath, regUtil_cmd =  util._getTheseRegVariables(reg)

    failure = util._isCheckTimeEnabled(check_time, warn_if_check_time_disabled, regUtil_cmd)
    if failure == 1:
        return failure
 
    failure = util._areNTPServersAvailable( number_of_servers)
    if failure == 1:
        return failure

    
    offset = -10000
    nbServs = number_of_servers

    while nbServs > 0:
        i = randrange( nbServs )
        timeServer = ntpdate_servers[i]

        # execute ntpdate on available servers    
        print(f"\t\t- Checking time from NTP server: {timeServer}")
        status, offset = util._executeNtpDateCommand(ntpdate_cmd, ntpdate_timeout, timeServer)

        if status == -1:
            error = f"\nCould not execute the command '{ntpdate_cmd}'. \
                    \nExecute the command '{ntpdate_cmd_xpath}' to set the pathname of \
                    \nthe ntpdate(1) utility to 'path'."
            errmsg(error)
            return -1

        
        if status == -2:
            warning_msg = f'Could not get time from time-server at {timeServer} using the ntpdate(1) utility, {ntpdate_cmd} \
                    \t\t If the utility is valid and this happens often, then remove {timeServer} from registry parameter regpath "NTPDATE_SERVERS"'
            print(f"\t\t- Offset: <invalid>\n")
            warnmsg(warning_msg)
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
            print(f"\t\t- Offset: {offset}\n")

            if abs(offset) > check_time_limit:
                error = f"\nThe system clock is more than {check_time_limit} seconds off, \
                            \nwhich is specified by registry parameter 'regpath" + "{CHECK_TIME_LIMIT}" + "'."
                errmsg(error)

            else:
                failure = 0
            
            break


            # print(f"\t\t- Offset: {offset}\n")

    
    if failure == 1:

        checkTime_cmd = "\"regutil -u 0 regpath{CHECK_TIME}\""
        errmsg(f"\nYou should either fix the problem (recommended) or disable\
                \ntime-checking by executing the command {checkTime_cmd} (not recommended)." )
    
    return failure


###############################################################################
# Deletes a queue
###############################################################################

def deleteAQueue(reg, envVar, queuePath, queueName):

    status      = 1     # default failure

    # Check to see if the server is running.
    if isRunning(reg, envVar, True):
        return status
    
    # Check if queue exists
    if not util._doesFileExist(queuePath):
        status = 2
        return status
    
    # Delete the queue
    try:
        os.unlink(queuePath)
        status = 0
    except:
        status = 3
        
    return status


###############################################################################
# Deletes a product-queue
###############################################################################

def del_pq(reg, envVar):

    pqueuePath   = reg['pq_path']
    status = deleteAQueue(reg, envVar, pqueuePath, "product")

    if status == 1:
        errmsg("deleteQueue(): The LDM server is running, cannot delete the queue")
    else:
        if status == 3:
            errmsg(f"deleteQueue(): Couldn't delete '{queueName}-queue':  '{queuePath}'")
        else:
            if status == 2:
                print(f"\n\tproduct-queue '{pqueuePath}' doesn't exist...");
            else:
                if status == 0:
                    print(f"\n\tproduct queue: '{pqueuePath}' deleted.")
                else:
                    print(f"\n\tproduct queue '{pqueuePath}' NOT deleted.")

###############################################################################
# Deletes a surf-queue
###############################################################################

def del_surf_pq(reg, envVar):

    surfqueuePath   = reg['surf_path']
    status = deleteAQueue(reg, envVar, surfqueuePath , "surf")

    if status == 1:
        errmsg("deleteQueue(): The LDM server is running, cannot delete the queue")
    else:
        if status == 3:
            errmsg(f"deleteQueue(): Couldn't delete surf-queue:  '{surfqueuePath}'")
        else:    
            if status == 2:
                print(f"\n\tsurf-queue '{surfqueuePath}' doesn't exist...");
            else:
                if status == 0:
                    print(f"\n\tsurf queue {surfqueuePath} deleted!")
                else:
                    print(f" surf queue {surfqueuePath} NOT deleted.")


###############################################################################
# create a queue: common to both pq and surf
###############################################################################

def callQueueCreate(q_size, q_slots, clobber, verbose, debug, fast, q_path):

    status      = 1     # default failure

    diskOk      = True
    debug_opt   = verbose_opt = fast_opt = clobber_opt = ""

    if debug:
        debug_opt   = " -x" 
    if verbose:
        verbose_opt = " -v" 
    if fast:
        fast_opt    = " -f"
        diskOk = util.checkDiskSpace(q_path, q_size)   # shall return False if not enough space on disk
    if clobber:
        clobber_opt = " -c"
    
    # Build the command line
    q_cmd = f"pqcreate {debug_opt} {verbose_opt} {fast_opt} {clobber_opt} -S {q_slots}  -q {q_path} -s {q_size} "
    #print(q_cmd)

    if fast and not diskOk:
        errmsg(f"mkqueue(1): there is NOT enough space to make a queue of size {q_size}. ")
        return status

    if util._doesFileExist(q_path):
        errmsg(f"queueCreate failed. File {q_path} already exists!.")
        return status
    
    # execute pqcreate(1)
    status = os.system(q_cmd)
    if status:
        errmsg(f"queueCreate: failed ({q_path} not created!)")
        return status
    
    status = 0
    print(f"\n\tqueue: '{q_path}' created!\n")

    return status

###############################################################################
# create a product queue
###############################################################################

def make_pq(reg, envVar):

    # need the number of slots to create
    pq_size     = reg['pq_size']            # This does not change from registry
    pq_slots    = reg['pq_slots']           # This does not change from registry

    debug       = envVar['debug']       # Boolean
    verbose     = envVar['verbose']     # Boolean
    pq_clobber  = envVar['clobber']     # Boolean
    pq_fast     = envVar['fast']        # Boolean
    pq_path     = envVar['q_path']     # This CAN change from registry
    
    
    return callQueueCreate(pq_size, pq_slots, pq_clobber, verbose, debug, pq_fast, pq_path)


###############################################################################
# create a pq_surf queue
###############################################################################

def make_surf_pq(reg, envVar):


    # need the number of slots to create
    sq_size     = reg['surf_size']          # This does not change from registry
    sq_slots    = int(sq_size / 1000000 * 6881)

    debug       = envVar['debug']       # Boolean
    verbose     = envVar['verbose']     # Boolean
    sq_clobber  = envVar['clobber']     # Boolean
    sq_fast     = envVar['fast']        # Boolean
    sq_path     = envVar['q_path']     # This CAN change from registry
    
    return callQueueCreate(sq_size, sq_slots, sq_clobber, verbose, debug, sq_fast, sq_path)


###############################################################################
# start the LDM server
###############################################################################

def start(reg, envVar):

    status      = 0     # default success

    ip_addr     = reg["ip_addr"]
    port        = reg["port"]
    debug       = envVar["debug"]
    verbose     = envVar["verbose"]
    ldmd_conf   = envVar["ldmd_conf"]
    pid_file    = envVar['pid_file']

    max_clients = envVar["max_clients"]
    max_clients_opt = ""
    if max_clients == None:
        max_clients = reg["max_clients"]
        max_clients_opt = f" -M {max_clients}"

    max_latency_opt = ""
    max_latency = envVar["max_latency"]
    if max_latency == None:
        max_latency = reg["max_latency"]
        max_latency_opt = f" -m {max_latency}"

    offset      = envVar["server_time_offset"]
    if offset == None:
        offset = reg["server_time_offset"]

    pq_path     = envVar["q_path"]
    if pq_path == None  or pq_path == "":
        pq_path = reg["pq_path"]

    # Build the 'ldmd' command line
    ldmd_cmd = f"ldmd -I {ip_addr} -P {port} {max_clients_opt} {max_latency_opt} -o {offset} -q {pq_path} "

    #print(    ldmd_cmd   )
    if debug:
        ldmd_cmd += " -x -v "
    
    if verbose and not debug:
        ldmd_cmd += " -v "
    
    
    # Check the ldm(1) configuration-file
    print(f"start: 3. Checking LDM configuration-file ({ldmd_conf})...\n")            

    ldmd_cmd2 = f"{ldmd_cmd} -nvl- {ldmd_conf} 2>/dev/null "

    output = os.system(ldmd_cmd2) >> 8
    # print(f"\noutput: {output}\n")   # : 0 means no problem
    if output:
        print(f" >> start: 3.1. Problem with LDM configuration-file\n")
        status = 1
    
    else:
        print("\nstart: 4. Starting the LDM server...\n")
        
        ldmd_cmd += f" > {pid_file} 2>/dev/null"

        status = os.system(ldmd_cmd)
        
        if not util.isLdmdProcRunning(envVar):
            util.kill_ldmd_proc(envVar)
            errmsg(" >> start: 4.1. Could not start LDM server")
            print(f"\tFailed commad: {ldmd_cmd}\n")
            status = 1
            return status

        else:
            # Check to make sure the LDM is running
            while not isRunning(reg, envVar, True) :
                time.sleep(1)

        print("\nstart: 5. Started!\n")            

    return status



def start_ldm(reg, envVar):

    status      = 0     # default success
    line_prefix = ""

    # Make sure there is no other server running
    print("\nstart: 1. Checking for running LDM server\n")
    if isRunning(reg, envVar, True):
        print("start: 2. There is another server running... (start aborted) \n")
        status = 1    
        return status

    # LDM not running

    # Check the queues
    print("start: 2. Checking queues\n")
    if not areQueuesOk(reg):
        errmsg("Queues are not correct. LDM server not started!")
        status = 1
        return status
    
    # product-queue AND surfQueue (if applicable) OK

    # Ensure that the upstream LDM database doesn't exist
    # debug and print("\nstart_ldm(): 3. Attempting to delete upstream LDM database...")
    os.system("uldbutil -d")
        
    # Check the pqact(1) configuration-file(s)
    # debug and print("\nstart_ldm(): 4. Checking pqact(1) configuration-file(s)...")
 
    if not are_pqact_confs_ok(reg, envVar):
        errmsg("")
        status = 1
        return status

    # pqact(1) config-files OK
    # Rotate the ldm log files if appropriate
    log_file = reg["log_file"]
    num_logs = reg["num_logs"]

    dirname  = os.path.dirname(log_file)
    #os.path.mkdirs(dirname, exists_ok = True)    # silent if exists: only in Python3.9 only!
    if not os.path.exists(dirname):
        os.path.mkdirs(dirname)

    # Reset queue metrics
    os.system("pqutil -C")
    status = start(reg, envVar)

    return status


def restart(reg, envVar):   # restart the ldm

    # These var. are in envVar
    #   ldmd_conf 
    #   q_path
    #   verbose
    #   debug++, $verbose++
    #   max_clients
    #   max_latency
    #   offset
    #   q_path;
    
    # lock acquired
    status = stop_ldm(reg, envVar)
    if status == 0:
        status = start_ldm(reg, envVar)
    
    # lock release    
    return status

###############################################################################
# stop the LDM server
###############################################################################

def stop_ldm(reg, envVar):

    status      = 0                     # default success
    kill_status = 0
    pid_file    = envVar['pid_file']

    if not isRunning(reg, envVar, True):
        #print("\nThe LDM server is NOT running or its process-ID is 'unavailable'")
        print("\nstop 0: LDM server NOT running...")
        return status
    
        
    # kill the server and associated processes
    print("\nstop: 1. Stopping the LDM server...\n")
    rpc_pid = util._getLdmdPid(pid_file)    # already validated in isRunning()

    kill_rpc_pid_cmd = f"kill {rpc_pid}"
    print(f"\t - kill RPC pid:  {kill_rpc_pid_cmd}")
    kill_status = os.system( kill_rpc_pid_cmd )

    # we may need to sleep to make sure that the port is deregistered
    while isRunning(reg, envVar, True): 
        print(f"\t - LDM server is still running... Sleep 1 sec.")
        time.sleep(1)

    #if not isLdmdProcRunning(envVar):

    print("\t - LDM server has stopped running... ")

    # Remove the pid file if still there    
    pid_filePath = Path(pid_file)
    if kill_status == 0:
        
        print(f"\t - Removing old product information files")
        # remove product-information files that are older than the LDM pid-file.
        removeOldProdInfoFiles(envVar, pid_file)

        # get rid of the pid file
        print(f"\t - Unlinking pid file: {pid_filePath}\n")
        pid_filePath.unlink()
    
    print("stop: 2. LDM server stopped!\n")
    return status


###############################################################################
# Check the pqact.conf file(s) for errors
###############################################################################

# Parameters:
#         -p pqact_conf  (default: $LDMHOME/etc/pqact.conf)
#         conf_file 

def pqactcheck(reg, envVar):

    return are_pqact_confs_ok(reg, envVar)


def are_pqact_confs_ok(reg, envVar):

    are_ok              = True

    pathnames           = ()  # tuple?
    ldmd_conf           = envVar["ldmd_conf"]
    pqact_conf          = envVar['pqact_conf']
    pqact_conf_option   = envVar['pqact_conf_option']

    # precedence is:
    #     -p pqact_conf -->  ldmd_conf  --> (default: $LDMHOME/etc/pqact.conf)
    #
    if pqact_conf_option:
        # A "pqact" configuration-file was specified on the command-line.
        pathnames = (pqact_conf,)
    
    else:
        # No "pqact" configuration-file was specified on the command-line.
        # Set "@pathnames" according to the "pqact" configuration-files
        # specified in the LDM configuration-file.
        pathnames = util.readPqActConfFromLdmConf(ldmd_conf)

        # if none found, use the default:
        if not pathnames:
            #print(f"\n\t ... using default instead: {pqact_conf}\n")
            pathnames = (pqact_conf,)
    

    # At this point, are_ok == 1
    for pathname in pathnames:
        
        # Examine the "pqact" configuration-file for leading spaces. WHY?
        ####################################################################
        if 0:
            output = ""

            numOutput = 0
            print(f"{line_prefix}{pathname}: ")
            #print(f'grep -n "^ " {pathname} ')
            
            #( @output ) = 'grep -n "^ " $pathname 2> /dev/null'
            if numOutput >= 0:  # $#output >= 0:
                print("remove leading spaces in the following:\n")

                prev_line_prefix = line_prefix
                line_prefix += "    "

                for line in output:
                    print(f"{line_prefix}{line}")
                
                line_prefix = prev_line_prefix
                leading_spaces = 1

            if leading_spaces:
               are_ok = 0
            
        #else:
        ######################################################################

        # Check the syntax of the "pqact" configuration-file via "pqact".
        read_ok = False
        items_lines = []
        pqact_cmd = f"pqact -vl- -q /dev/null {pathname} 2>&1"
        
        try:
            pqact_output = subprocess.run(pqact_cmd, stdout=subprocess.PIPE,          shell=True).stdout.decode()                        
            items_lines = pqact_output.split("\n")

        except Exception as e:
            errmsg(e)

        for line in items_lines:
        
            if "Successfully read" in line:     
                read_ok = True
                print(f"\t- pqact_conf: syntactically correct. ({pathname}) \n") 
                return read_ok


        print(f"\t- pqact_conf: {pathname} has problems:\n")
        are_ok = False

    # for pathname in pathnames: end loop
    
    return are_ok



###############################################################################
# Check a queue-file for errors
###############################################################################

def getQueueStatus(queue_path, name):       # name e.g. "surf"
    
    status      = 0
    pqcheck_cmd = f"pqcheck -q {queue_path} 2> /dev/null"

    try:
        status      = os.system(pqcheck_cmd) >> 8    # to get the system status code
    except Exception as e:
        errmsg(e)
        return -1

    if 1 == status:
        errmsg(f"The self-consistency of the {name}-queue couldn't be determined.\nSee the logfile for details.")
        return status

    if 2 == status:
        errmsg(f"The {name}-queue doesn't have a writer-counter.\nUsing 'pqcheck -F' to create one...")
        return status

        pqcheck_cmd = f"pqcheck -F -q {queue_path} "
        status = os.system(pqcheck_cmd)     # >> 8; to get the system status code
        
        if status != 0:    
            errmsg("Couldn't add writer-counter to {name}-queue.")
        else:
            status = 0
        
        return status

    if 3 == status:
        pqcat_pqcheck_cmd = f"pqcat -l- -s -q {queue_path} && pqcheck -F -q {queue_path}"

        errmsg(f"The writer-counter of the {name}-queue isn't zero.  \
            \nEither a process has the product-queue open for writing or the queue might be corrupt.\
            \nTerminate the process and recheck or use:\
            \n{pqcat_pqcheck_cmd} \
            \nto validate the queue and set the writer-counter to zero.")

    return status


# check product-queue for corruption: return True if corrupted
def queueCheck(reg, env):
    
    statusOk = False
    print(f"\n\tqueueCheck(): LDM server status check")
    if isRunning(reg, env, True):     
        errmsg("queuecheck(): The LDM server is running! ('queuecheck' aborted)")
    
    else:

        statusOk = isProductQueueOk(reg)
        if statusOk:
            print(f"\n\t\t -- product-queue is correct.") 
    
    return statusOk


# Resets the LDM registry.
#
# Returns:
#       0               Success.
#       else            Failure.  "errmsg()" called.
#
def resetRegistry():

    status = 1     # default failure

    if os.system("regutil -R"):     # check return status here
        errmsg("Couldn't reset LDM registry")
        return status

    status = 0
    
    return status


###############################################################################
# Check the product-queue file for errors
###############################################################################

def isProductQueueOk(reg):

    print("\t- Checking the product-queue...", end='')
    pq_path     = reg['pq_path']
    status = getQueueStatus(pq_path, "product")
    
    if status != 0: 
        errmsg(
            "The product-queue is corrupt.  Use\n\
                ldmadmin delqueue && ldmadmin mkqueue\n \
            to remove and recreate it.")
    
    return status == 0


###############################################################################
# Check the surf-queue file for errors
###############################################################################

def isSurfQueueOk(reg):

    print("\t- Checking the surf-queue......", end='')
    # Open ldm config file
    ldmdConfig          = reg["ldmd_conf"]
    surfqueuePathname   = reg["surf_path"]
    exec_entry          = "exec"
    surf_entry          = "pqsurf"
    foundOne            = 0
    status              = 0

    # 1. First check if ldmd.conf has valid entr-y(-ies) for surf queue path
    with open(ldmdConfig, 'r') as conf_lines:

        # Search for the surf path when EXEC enabled        
        for entry in conf_lines:
            
            if (entry.startswith("#") or entry.startswith("\n")) or \
                not (entry.lower().startswith(exec_entry) and "pqsurf" in entry):
                continue

            # EXEC surfQueue /home/.../surfQueue.pq
            surfPathList = entry[:-1].split()
            if len(surfPathList) < 3:
                continue
            
            surfPath = surfPathList[2]
            # entry could be a commented out path: #/home/.../surfQueue.pq
            if not os.path.exists(surfPath): 
                continue
    
            status = getQueueStatus(surfPath, "surf")
            if status != 0:
                errmsg(f"The surf-queue {surfPath} specified in ldmd.conf is corrupt.\
                    \nUse these 2 commands to recreate it correctly: \n\tldmadmin delsurfqueue -q {surfPath} && \
                    \nldmadmin mksurfqueue -q {surfPath}")
            else:
                #foundOne += 1
                #break
                #print(f"\nisSurfQueueOk(): The surf-queue {surfPath} specified in ldmd.conf is valid.")
                return True

    # This scenario is not to be considered: found more than 1  ====================================
    # if foundOne > 1:
    #     print(f"isSurfQueueOk 3: found {foundOne} 'EXEC pqsurf path' valid entries in ldmd.conf.")
    #     return True
    # ==============================================================================================



    # 2. if unsuccessful, use the registry value
    # if foundOne == 0 and 
    if os.path.exists(surfqueuePathname): 
        
        #print(f"\nisSurfQueueOk(): Using surf-queue entry from registry ({surfqueuePathname}).")
        status = getQueueStatus(surfqueuePathname, "surf")
        if status != 0:
            errmsg(f"The surf-queue {surfqueuePathname} is corrupt.\
                \nUse these 2 commands to recreate it correctly: \n\tldmadmin delsurfqueue -q {surfqueuePathname} \
                \n&& \
                \n\tldmadmin mksurfqueue -q {surfqueuePathname}")
        #else:
            #print(f"\nisSurfQueueOk(): The surf-queue {surfqueuePathname} specified in registry is valid.")
    else:
        print(f"\tisSurfQueueOk(): registry specified surf-queue file ({surfqueuePathname}) does not exist...\n")
        status = 1

    return status == 0


# scour data directories
def scour(reg):

    scourFile = reg['scour_file']
    scour_cmd = f"scour  {scourFile}"
    status  = os.system(scour_cmd)
    
    return status


# page the logfile
def pageLog(reg):

    status      = 1
    pager_cmd   = os.environ.get('PAGER', None)
    logFile     = reg['log_file']

    if pager_cmd == None:
        pager_cmd = "more"
    
    pager_cmd += f" {logFile}"
    status  = os.system(pager_cmd)
    
    return status


# do a "tail -f" on the logfile
def tailLog(reg):

    logFile     = reg['log_file']
    tail_cmd    = f"tail -f {logFile}"
    status      = os.system(tail_cmd)
    return status


def clean(reg, env): 

    status = 0
    if isRunning(reg, env, True):
        print("\n\tThe LDM server is running!  Stop it first.")
        status = 1
        return status
    
    status = util.kill_ldmd_proc(env)
    if status != 0:
        print("clean(): Could not clean the ldmd processes...")
        return status

    # here, successfully removed pidFile: proceed or NOT?
    ldmHome     = env['ldmhome']
    remove_cmd  = f"rm -f {ldmHome}/MldmRpc_*"
    status      = os.system(remove_cmd)
    
    return status


def updateGempakTables():

    return os.system("updateGempakTables")
    

###############################################################################
# Check the queue-files for errors
###############################################################################

def areQueuesOk(reg):

    arePOk = isProductQueueOk(reg)
    if arePOk:
        print("... Ok")
    else:
        print("\n\t- ... the product-queue check FAILED.")

    areSOk = isSurfQueueOk(reg)
    if areSOk:
        print("... Ok")
    else:
        print("\n\t- ... the surf-queue check FAILED.")

    return arePOk and areSOk

######################################################################
#   show the settings information on users environment
######################################################################

def showSettings(reg, env):

    setuidEnabledPrograms = [
                "hupsyslog", 
                "ldmd", 
                "noaaportIngester", 
                "dvbs_multicast"
                ]

    LDMHOME         = env["ldmhome"]
    LDMHOME         = "/home/miles/projects/ldm"  # <-- remove in prod
    LDMHOME_bin     = f"{LDMHOME}/bin"

    print(  f"\t1- LDMHOME: {LDMHOME}")

    print(f"\n\t2- Setuid programs verification:")


    for file in setuidEnabledPrograms:
        try:
            ll_cmd      = f"ls -la {LDMHOME_bin} | grep {file}"
            output      = subprocess.check_output(ll_cmd, shell=True).decode()
            setuidOutput= output.split('\n')[0]
            print(f"\t{setuidOutput}")
        except:
            continue

    print(f"\n\t3- $LDMHOME listing:")
    ls_cmd          = f"ls -la {LDMHOME} "
    lsHomeOutput    = subprocess.check_output(ls_cmd, shell=True).decode()
    print(f"\t{lsHomeOutput}")

    print(f"\n\t4- $LDMHOME/bin listing:")   
    lsBin_cmd       = f"ls -la {LDMHOME_bin} "
    lsHomeBinOutput = subprocess.check_output(lsBin_cmd, shell=True).decode()
    print(f"\t{lsHomeBinOutput}")

    print(f"\n\t5- ldmadmin config:")   
    ldmConfig(reg, env)

    print(f"\n\t6- mount: $mount | grep `df $LDMHOME/bin`")
    mount_cmd       = "mount | grep `df $LDMHOME/bin | awk 'NR==2{print $1}'`"
    mountOutput     = subprocess.check_output(mount_cmd, shell=True).decode()
    print(f"\n\t{mountOutput}")


    # 7- SE (RedHat) status (sestatus)")   
    # Only if applicable:
    try:
        sestatus_cmd    = "sestatus 2>/dev/null"
        sestatusOutput  = subprocess.check_output(sestatus_cmd, shell=True).decode()

        print(f"\n\t7- SE (RedHat) status (sestatus):\n")   
        for item in sestatusOutput.split('\n'):
            print(f"\t{item}")
        
    except:

        print("")

# echo -e "\n$ sestatus"
# which sestatus
# # if output starts with "which: no sestatus" ---> not Linux SELINUX.

# output=`sestatus`

# # Split output on '\n' and display lines
# echo $output
# echo $?


# echo -e "\n\n"




def errmsg(msg):
    print(f"\n\tERROR: {msg}")

def  warnmsg(msg):
    print(f"\n\tWARNING: {msg}")



###############################################################################
#                                       main()
###############################################################################


if __name__ == "__main__":

    os.system('clear')

    ldmhome         = "/home/miles/projects/ldm"
    regHandler      = RegistryParser(ldmhome)
    envHandler      = LDMenvironmentHandler()

    registryDict    = regHandler.getRegistryEntries()
    envVarDict      = envHandler.getEnvVarsDict()
    
    # print the current ldm configuration
    # ldmConfig(registryDict, envVarDict)

    # Check if LDM is running: DONE
    isRunning(registryDict, envVarDict, True)

    envHandler.prettyPrintEnvVars()
    regHandler.prettyPrintRegistry()

    # new log rotation: TO-CHECK
    # newLog(logFile, numLogs)

    # LDM stop: DONE
    # stop_ldm(registryDict, envVarDict)

    
    # LDM check
    #check_ldm(envVarDict)

    # print("checkTime:")
    #checkTime(registryDict)



    #status = check_insertion(registryDict)

    # vetQueueSize(registryDict, envVarDict)

    #start(registryDict)

    envVarDict['pqact_conf'] = 'pqact.conf'
    envVarDict['pqact_conf_option'] = 0

    #are_pqact_confs_ok(registryDict, envVarDict)   # DONE


    # LDM start : TO-DO / DONE?
    #start_ldm(registryDict, envVarDict)
    #stop_ldm(registryDict, envVarDict)
