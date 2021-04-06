
# Standard Library imports
import  os
from    os import path
import  sys
import  psutil
from    filelock import Timeout, FileLock
import  subprocess
from    subprocess import PIPE
import  glob
from    pathlib import Path
from    random import randrange
from    uptime import uptime
import  time

# Local application imports
import  ldmSubs     as sub
from    parseRegistry import RegistryParser
from    environHandler import LDMenvironmentHandler


###############################################################################
# Helper functions: they star with _undescore_ to distinguish them from 
#                    ldmadmin-specific Perl routines
###############################################################################

def _executeNtpDateCommand(ntpdate_cmd, timeout, ntpServer):

    ntpdate_ls_cmd = f"ls {ntpdate_cmd}  2>&1>/dev/null"
    # Check if the ntpdate command exists as set in registry
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
        # process the first one found only
        offsetParam  = process_output.decode().split()[5][:-1]
        
        return 0, float(offsetParam)
    except:
        #print(f"{ntpServer} is not responding...{offsetParam}")
        return -2, -1
    


def _increaseQueue(reg, envVar, pqMonValues):

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

    #print(f"\n\t- Increasing the capacity of the queue to {newByteCount} bytes and {newSlotCount} slots...")

    pqcreate_cmd = f"pqcreate -c -S {newSlotCount} -s {newByteCount} -q {newQueuePath}"
    #print(f"\n\t\t{pqcreate_cmd}")

    if os.system(pqcreate_cmd):
        errmsg(f"vetQueueSize(): Couldn't increase queue: {newQueuePath}")
        status = 2            # major failure
        return status
    
    #print(f"\n\t\tCreated new QUEUE: {newQueuePath}")


    if sub.isRunning(reg, envVar, True): 
        if stop_ldm(): 
            status = 2        # major failure
            return status
    
        restartNeeded = 1
    
    # success so far
    # LDM is stopped
    print("Grow  the queue...\n")
    if sub.grow(pq_path, newQueuePath): 
        status = 2        # major failure
        return status
    
    print("Saving new queue parameters...\n")
    if sub.saveQueuePar(newByteCount, newSlotCount):
        status = 2    # major failure
        return status
        
    
    # success so far
    # restart needed
    if restartNeeded: 
        print("Restarting the LDM...\n")
        if sub.start_ldm(reg, envVar):
            errmsg("vetQueueSize(): Couldn't restart the LDM")
            status = 2    # major failure
            return status
        
    # reset queue metrics
    # mode is increase queue
    os.system("pqutil -C")  
    return status



def _decreaseQueue(reg, envVar):
    
    #2. recon == decrease  
    
    if 0 >= minVirtResTime:
        # Use age of oldest product, instead
        minVirtResTime = ageOldest
    
    # if 0 >= ageOldest then minVirtResTime = 1
    if 0 >= minVirtResTime:
        minVirtResTime = 1 
    
    newMaxLatency = minVirtResTime
    newTimeOffset = newMaxLatency

    print(f"vetQueueSize(): Decreasing the maximum acceptable latency and " +
        "\nthe time-offset of requests (registry parameters 'regpath" + "{MAX_LATENCY}'" + 
        "\nand 'regpath" + "{TIME_OFFSET}')" + " to {newTimeOffset} seconds...")


    print("Saving new time parameters...\n")
    if sub.saveTimePar(newTimeOffset, newMaxLatency):
        status = 2    # major failure
        return status
    

    # new time parameters saved
    if not sub.isRunning(reg, envVar, True):
        status = 0    # success : LDM is not running
    
    else: # LDM is running
    
        print("Restarting the LDM...\n")
        if sub.stop_ldm(reg, envVar):
            errmsg("vetQueueSize(): Couldn't stop LDM")
            status = 2        # major failure
            return status
        
        # LDM stopped
        if sub.start_ldm(reg, envVar):
            errmsg("vetQueueSize(): Couldn't start LDM")
            status = 2    # major failure
            return status
        
        status = 0     # success    

    # reset queue metrics
    status = os.system("pqutil -C")     # <-- not tested
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



def _areNTPServersAvailable(number_of_servers):

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


def _doesFileExist(path):
    return os.path.exists(path)

def _getLdmdPid(pidFilename):
    
    status = -1

    if not _doesFileExist(pidFilename) or os.stat(pidFilename).st_size == 0:
        # debug and print(f"\nisRunning(): ldmd NOT running ({pidFilename} does not exist.)\n")
        return status

    if os.stat(pidFilename).st_size == 0:
        # debug and print(f"\nisRunning(): ldmd NOT running ({pidFilename} exists but is empty!)\n")
        return status

    # Retrieve ldmd process id :
    with open(pidFilename, 'r') as pidFile:
        pid = pidFile.read().replace('\n','')

        # verbose and print(f"\npid_file: {pidFilename} - pid: '{pid}'\n")
        try:
            pid     = int(pid)

        except Exception as e:
            errmsg(e)
            print("You may need to run 'ldmadmin clean'.")
            return status

        if psutil.pid_exists(pid):
            #print(f"\n\tprocess with pid { pid } exists!\n")
            return pid

    return status


###############################################################################
# Check a queue-file for errors
###############################################################################


def errmsg(msg):
    print(f"\n\tERROR: {msg}")

def isProductQueueOk():

    path = "/home/miles/projects/ldm/var/queues/ldm.pq"
    status = getQueueStatus(path, "product")

    if 4 == status:
        errmsg("The product-queue is corrupt.  Use\n\
            ldmadmin delqueue && ldmadmin mkqueue\n\
            to remove and recreate it.")
    
    return status == 0



def isSurfQueueOk():

    path = "/home/miles/projects/ldm/var/queues/pq_surf.pq"
    status = getQueueStatus(path, "surf")

    if 4 == status:
        errmsg(f"The surf-queue is corrupt.  Use\n \
        ldmadmin delsurfqueue -q {path} && ldmadmin mksurfqueue -q {path}\n \
        to remove and recreate it.")
    
    return status == 0


# Consolidated behavior (fewer cases)
def getQueueStatus(queue_path, name):
    
    status = 0

    print(f"Checking the {name}-queue...\n")
    pqcheck_cmd = f"pqcheck -q {queue_path} 2>/dev/null"
    
    status = os.system(pqcheck_cmd) >> 8
    
    if 1 == status:
        errmsg(f"The self-consistency of the {name}-queue couldn't be determined.  \n\
            See the logfile for details.")
        return status
    
    if 2 == status:
        errmsg(f"The {name}-queue doesn't have a writer-counter.  \n\
            Using 'pqcheck -F' to create one...")
        return status

    
    pqcheck_cmd = f"pqcheck -F -q {queue_path} "
    status = os.system(pqcheck_cmd) >> 8    # to get the system status code
    
    if status != 0:    
        errmsg("Couldn't add writer-counter to {name}-queue.");
        return status
   
    if 3 == status:
        pqcat_pqcheck_cmd = f"pqcat -l- -s -q {queue_path} && pqcheck -F -q {queue_path}"
        errmsg(f"The writer-counter of the {name}-queue isn't zero.  Either \
            a process has the product-queue open for writing or the queue \
            might be corrupt.  \n\
            Terminate the process and recheck or use:\n\
            {pqcat_pqcheck_cmd} \
            to validate the queue and set the writer-counter to zero.")
    

    return status


###############################################################################
# Date Routine.  Gets data and time as GMT in the same format as the LDM log
# file.
###############################################################################

def get_date():

    month_array = { 1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 
                    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    
    year, mon, mday, hour, minute, sec, wday, yday, isdst = time.gmtime(time.time()) 
    hh_mm_ss = _formatToHhMmSs(hour,minute,sec, ":")
    #hh_mm_ss = time.strftime('%H:%M:%S', time.gmtime(time.time()))
    date_string = f" {month_array[int(mon)]} {mday} {hh_mm_ss} UTC"
        
    return date_string

def _formatToHhMmSs(h,m,s, colon):
    return "%02i%s%02i%s%02i" % (h, colon, m, colon, s)
    


###############################################################################
# Metrics:
###############################################################################

# Command for getting a UTC timestamp:
def getTime():

    year, mon, mday, hour, minute, sec, wday, yday, isdst = time.gmtime(time.time()) 

    if mon in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
        mon = f"0{mon}"
    hh_mm_ss = _formatToHhMmSs(hour,minute,sec, "")
    dateTime = f"{year}{mon}{mday}.{hh_mm_ss}"

    return dateTime

#
# Command for getting the running 1, 5, and 15 minute load averages:
def getLoad():

    uptime_string   = subprocess.check_output(["uptime"], shell=True).decode()
    all3LoadAvgs    = uptime_string[uptime_string.index("average") + 8:].split()
    
    loadAvg1        = float( all3LoadAvgs[0][:-1])
    loadAvg2        = float(all3LoadAvgs[1][:-1])
    loadAvg3        = float(all3LoadAvgs[2][:-1])
    
    return (loadAvg1, loadAvg2, loadAvg3)


#
# Command for getting the number of connections to the LDM port (remote, local):
def getPortCount(reg, port):# DONE

    totalCount = 0
    netstat_cmd = reg["netstat"]
    netstat_cmd = f"netstat | grep ESTAB | grep {port}"
    try:
        netstat_output = subprocess.check_output(netstat_cmd, shell=True).decode()
        total = len(netstat_output.split("\n")) -1

        lclCount = 0
        uldbutil_cmd = "uldbutil 2>/dev/null"

        uldbutil_output = subprocess.check_output(uldbutil_cmd, shell=True).decode()
        lclCount = len(uldbutil_output.split("\n")) -1
        rmtCount = totalCount - lclCount
        if rmtCount < 0:
            rmtCount = 0
        
        return (rmtCount, lclCount)

    except:
        #print(f"No result for {netstat_cmd}\n")
        return (0,0)


#
# Command for getting product-queue metrics (age, #prods, #bytes):
def getPq(pq_path):

    age = -1
    prodCount = -1
    byteCount = -1

    pqmon_cmd = f"pqmon -S -q {pq_path}"
    try:
        pqmon_output = subprocess.check_output(pqmon_cmd, shell=True).decode()
        outputList = pqmon_output[:-1].split()

        age = int(outputList[7])
        prodCount = int(outputList[6])
        byteCount = int(outputList[3])
        
        return (age, prodCount, byteCount)

    except:
        return "000"


################################################################################
#
# Command for getting space-usage metrics:
#
def getCpu(reg):

    userTime    = -1
    sysTime     = -1
    idleTime    = -1
    waitTime    = -1
    memUsed     = -1
    memFree     = -1
    swapUsed    = -1
    swapFree    = -1
    contextSwitches = -1
    haveMem     = 0
    haveSwap    = 0

    ########################################################
    #                          top                        v#
    top_cmd = reg["top"]
    memUsed, memFree, swapUsed, swapFree, haveMem, haveSwap = readTop(top_cmd)

    ########################################################
    #                          free                        #   
    # If unsuccessful getting memory and swap usage from top(1), try using
    # free(1)
    if not haveMem or not haveSwap:
        memUsed, memFree, swapUsed, swapFree = readFree()

    ########################################################
    #                          vmstat                      #   
    contextSwitches, sysTime, userTime, idleTime, waitTime = readVmstat()


    return (userTime, sysTime, idleTime, waitTime,
        memUsed, memFree, swapUsed, swapFree, contextSwitches)

# Not used
def get_ram_usage():
    return int(psutil.virtual_memory().total - psutil.virtual_memory().available)
# Not used
def readMem():
    print('RAM usage is {} MB'.format(int(get_ram_usage() / 1024 / 1024)))


def readTop(top_cmd):

    top_cmd = f"{top_cmd} | egrep 'free.*used|total.*used'"
    try:
        top_output  = subprocess.check_output(top_cmd, shell=True).decode()
        
        items_lines = top_output.split("\n")
        mem_line    = items_lines[0].split()
        swap_line   = items_lines[1].split()
        
        mem_total   = int(mem_line[3])
        mem_free    = int(mem_line[5])
        mem_used    = int(mem_line[7])

        swap_total  = int(swap_line[2])
        swap_free   = int(swap_line[4])
        swap_used   = int(swap_line[6])

        #print(mem_used, mem_free, swap_used, swap_free, 1, 1)
        return (mem_used, mem_free, swap_used, swap_free, 1, 1)
        

    except Exception as e:
        #print(e)
        return (0,0,0,0,0,0)  # last 2 zeros to tell readFree() to execute


def readFree():

    free_cmd = f"free -b"
    try:
        free_output  = subprocess.check_output(free_cmd, shell=True).decode()

        items_lines = free_output.split("\n")
        mem_line    = items_lines[1].split()
        swap_line   = items_lines[2].split()
        
        mem_total   = int(mem_line[1])
        mem_used    = int(mem_line[2])
        mem_free    = int(mem_line[3])

        swap_total  = int(swap_line[1])
        swap_used   = int(swap_line[2])
        swap_free   = int(swap_line[3])

        #print(mem_used, mem_free, swap_used, swap_free)
        return (mem_used, mem_free, swap_used, swap_free)
        

    except Exception as e:
        print(e)
        return (0,0,0,0)


# Retrieve CPU times
def readVmstat():
    csIndex = -1
    usIndex = -1
    syIndex = -1
    idIndex = -1
    waIndex = -1
    line = ""

    vmstat_cmd = f"vmstat 1 1"
    try:
        vmstat_output   = subprocess.check_output(vmstat_cmd, shell=True).decode()
        items_lines     = vmstat_output.split("\n")

        base_line       = items_lines[1].split()
        value_line      = items_lines[2].split()

        pos = -1
        for term in base_line:
            pos += 1
            if term == "cs":
                contextSwitches = int(value_line[pos])

            if term == "us":
                userTime        = int(value_line[pos])

            if term == "sy":
                sysTime         = int(value_line[pos])

            if term == "id":
                idleTime        = int(value_line[pos])

            if term == "wa":
                waitTime        = int(value_line[pos])

        return (contextSwitches, sysTime, userTime, idleTime, waitTime)

    except Exception as e:
        print(e)
        return (contextSwitches, sysTime, userTime, idleTime, waitTime) # all zeros


#
# print metrics to file
def printMetrics(reg):

    metricsFilePath = reg['metrics_file']
    port            = reg["port"]
    pq_path         = reg["pq_path"]
    pq_line         = list(getPq(pq_path))
    portCount       = list(getPortCount(reg, port))
    load            = list(getLoad())
    thisTime        = float(getTime())    
    cpu             = list(getCpu(reg))
    
    all_metrics     =  load + portCount + pq_line + cpu 
    all_metrics.insert(0, thisTime)
    
    time_legend     = "\ttime: \t\tYYYYmmdd.hhmmss"
    load_legend     = "\tuptime (avg at): 1 mn, 5 mn, 15 mn"
    port_legend     = "\tport (count): \tremote, local"
    pq_legend       = "\tpq: \t\tage, prodCount, byteCount"
    cpu_legend      = "\tCPU: \t\tuserTime, sysTime, idleTime, waitTime, memUsed, memFree, swapUsed, swapFree, contextSwitches"

    all_legend      = "\n   time  \t|     uptime     | port |            pq          |   CPU "

    # print to file
    with open(metricsFilePath, "w+") as metricsFile:
        print(all_legend,   file=metricsFile) 
        print(all_metrics,  file=metricsFile)

        # print the legend to the metricsFilePath
        # print(f"\nLegend:\n{time_legend}\n{load_legend}\n{port_legend}\n{pq_legend}\n{cpu_legend}\n", file=metricsFile)



def addMetrics(reg):

    status          = 0
    metricsFilename = reg['metrics_file']

    if not _doesFileExist(metricsFilename):
        errmsg("addMetrics(): Cannot create/open metrics-file '{metricsFilename}'\n")
        status  = 1
        return status

    fileToLock  = f"{metricsFilename}.lock"
    lock        = FileLock(fileToLock)

    try:
        lock.acquire(timeout=20)
        
        # print metrics to file
        printMetrics(reg, metricsFilename)

    except:
        print(f"\nLock already acquired: lockID: {lock}\n")
        errmsg(f"addmetrics(): Couldn't lock metrics-file '{metricsFilename}'. \
                \nAnother 'ldmadmin addmetrics' is likely running.")
        status  = 2
        return status

    try:
        lock.release()
    except Timeout:
        print(f"releaseLock(): Could not release lock on '{fileToLock}'! \
            \n(Manually delete it.)")
        status  = 3
        
    return status


#
# Command for plotting metrics: TO TEST!!!!!!!!!!!!!!!!!!!!!!!!!
def plotMetrics(reg, envVar):

    begin           = envVar['begin']
    end             = envVar['end']
    metrics_files   = reg['metrics_files']
    
    plot_cmd = f"plotMetrics -b {begin} -e {end} {metrics_files}"
    
    return os.system(plot_cmd)


def newMetrics(reg):

    metricsFile     = reg['metrics_file']
    numMetrics      = reg['nums_metrics']

    return ldmSubs.newLog(metricsFile, numMetrics)



def readPqActConfFromLdmConf(ldmdConfPathname):

    pqactConfs = ()

    f = open(ldmdConfPathname, "r")
    for line in f:
        if not (line.lower().startswith("exec") and "pqact" in line):
            continue
    
        if len(line.split()) >= 3:
            newPqAtConf = os.path.expanduser(line.split()[2])
            if not os.path.exists(newPqAtConf):
                print(f'\tldmd_conf: EXEC "pqact" {newPqAtConf}, file does not exist!')
            else:
                pqactConfs = pqactConfs + (newPqAtConf,)
        else:
            print('Notice: No EXEC "pqact" pqact configuration file referenced in ldmd.conf\n')

    f.close()
    return pqactConfs


# Which 'ps(1)' command to use depends on the running OS
def _whichPs(envVar):

    whichOs = envVar['os']
    rel     = envVar['release']

    if whichOs == "SunOS" and release.startswith(4):
        cmd = "ps -gawxl"
        default = 0 
     
    else:
        if "BSD" in whichOs.lower():
            cmd = "ps ajx"
            default = 1

        else:
            userEnv = os.getenv('USER')
            cmd = f"ps -fu {userEnv}"
            default = 1 
        
    return cmd, default

# ###############################################################################
# # HUP the pqact program(s)
# ###############################################################################

def pqactHUP(envVar):

    status = 0
    cmd=""
    ps_cmd, default = _whichPs(envVar)

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


def copyCliArgsToEnvVariable(envVar, cliDico):

    mapArgsToNames = {
            'm': 'max_latency', 
            'M': 'max_clients',
            'q': 'pq_path',
            'o': 'server_time_offset',
            'conf_file': 'ldmd_conf', 
            'v': 'verbose',
            'x': 'debug',
            'f': '',           # concerns both : force and feedset but they are disjoint (2 different commands)
            'c': 'clobber',
            'n': 'num_logs',
            'l': 'log_file',
            'b': 'begin',
            'e': 'end',
            "pqact_conf_option": "pqact_conf_option",
            "p": "pqact_conf"

    }
    # set the defaults:
    envVar['feedset']           = "ANY"
    envVar['pq_path']           = ""
    envVar['sq_path']           = ""
    envVar['ldmd_conf']         = ""
    envVar['log_file']          = ""
    envVar['pqact_conf']        = ""
    envVar['debug']             = False
    envVar['clobber']           = False
    envVar['verbose']           = False
    envVar['fast']              = False
    envVar['max_latency']       = 0
    envVar['max_clients']       = 0
    envVar['server_time_offset']= 0
    envVar['begin']             = 19700101  # YYYYMMDD
    envVar['end']               = 30000101  # ...
    envVar['num_logs']          = 0

    for key,val in cliDico.items():

        mappedAttribute = mapArgsToNames[key]
        envVar[mappedAttribute] = val


def checkDiskSpace(pq_path, pqSize):

    rootAvailSize   = -1
    residualMem     = int( pqSize * 10 / 100)   # allow 10% availability

    df_cmd = f"df -k {pq_path}"
    
    try:
        proc = subprocess.check_output(["df", "-k"], shell=True ).decode()
        
        headLine = False
        for line in proc.split('\n'):
            lineList = line.split()
            if not lineList:
                continue
            
            if "Available" in line:

                availIndex = lineList.index("Available")
                mountedOnIndex = lineList.index("Mounted")

                headLine = True

            else:
                if headLine:
                    mountPoint = lineList[mountedOnIndex]
                    if mountPoint == "/": 
                        rootAvailSize = int(lineList[availIndex])
                        break

    except Exception as e:
        print(e)
        errmsg(f"command: {df_cmd} failed! ")

    # 1K block
    return rootAvailSize * 1024 > pq_size + residualMem

def kill_ldmd_proc(env):
    
    status = 0
    
    # Kill the ldmd processes
    ldmd_processes      = "ldmd -I"
    ps_grep_ldmd_cmd    = f"ps -ef | grep '{ldmd_processes}'"
    try:
        proc = subprocess.check_output(ps_grep_ldmd_cmd, shell=True ).decode()   
        for line in proc.split("\n"):
            if not line or "grep" in line:
                continue

            proc_id = line.split()[1]
            kill_cmd= f"kill -9 {proc_id}"
            proc    = subprocess.check_output( kill_cmd, shell=True )

    except Exception as e:
        print(e)
        errmsg(f"'kill_ldmd_proc(): command: {ps_grep_ldmd_cmd} or {kill_cmd} failed! ")
        status = -1
        return status

    # Remove the pid file
    pidFile = env['pid_file']
    if util._doesFileExist(pidFile): 
        try:
            os.unlink(pidFile) 
        except: 
            errmsg(f"Couldn't remove LDM server PID-file '{pidFile}'")
            status = 3
            return status

    #else: debug and print(f"pid file {pidFile} does not exist!")
        
    return status


def isLdmdProcRunning(env):
    
    ldmd_processes      = "ldmd -I"
    ps_grep_ldmd_cmd    = f"ps -ef | grep '{ldmd_processes}'"

    ldmd_procs_found    = 0
    try:
        proc = subprocess.check_output(ps_grep_ldmd_cmd, shell=True ).decode()   
        for line in proc.split("\n"):
            if not line or "grep" in line:
                continue
            ldmd_procs_found += 1

    except Exception as e:
        print(e)
        errmsg(f"'isLdmdProcRunning(): command: {ps_grep_ldmd_cmd} failed! ")

    pidFilename = env['pid_file']
    return ldmd_procs_found > 0 and _doesFileExist(pidFilename)



if __name__ == "__main__":

    os.system('clear')

    regHandler = RegistryParser()


    # configure.ac replaces "@variable@"with actual value:
    ldmHome     = environ.get("LDMHOME", "/home/miles/dev")
    ldm_port    = "1.0.0.0"
    ldm_version = "6.13.14"

    # For testing purposes:
    ldmHome     = "/home/miles/dev" # <<---- remove in production setting !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    exec_prefix = ""

    envHandler = LDMenvironmentHandler(exec_prefix, ldmHome, ldm_port, ldm_version)

    registryDict = regHandler.getRegistryEntries()
    envVarDict = envHandler.getEnvVarsDict()
    
    envHandler.prettyPrintEnvVars()
    regHandler.prettyPrintRegistry()

    kill_ldmd_proc(envVarDict)
    print(ldmd_procs_stopped(envVarDict))

    exit(0)

    #print(_get_date()) DONE

    #getTime() DONE

    #print(getLoad()) # DONE

    pqsurf_path = registryDict["surf_path"]
    #getQueueStatus(pqsurf_path, "surf") # DONE
    spath = "/home/miles/projects/ldm/var/queues/pqsurf.pq"
    path = "/home/miles/projects/ldm/var/queues/ldm.pq"

    #print(isSurfQueueOk())     # DONE
    #print(isProductQueueOk())  # DONE
    #print(getPortCount(234))   # DONE
    #print(getPq(path))         # DONE
    #printMetrics(registryDict) # DONE

    metrics_files = "/home/miles/projects/ldm/var/logs/metrics.txt"

    top_cmd = registryDict["top"]
    
    #print(readTop(top_cmd))    # DONE
    #print(readFree())          # DONE


    #print(readVmstat())        # DONE
    
    # readMem()                  # DONE not used
    # ntpdate_cmd = registryDict["ntpdate_command"]
    # ntpserver = "0.us.pool.ntp.org"
    # print(_executeNtpDateCommand(ntpdate_cmd, 5, ntpserver))  # DONE

    ldmdConfPathname = "ldmd.conf"      #registryDict["ldmd_conf"]
    #print(readPqActConfFromLdmConf(ldmdConfPathname)) # DONE

    #ldmadmin_pqactHUP(envVarDict)   # DONE - can only test if pqact process(es) is(are) running
    #expression = readMem()

    begin       = 20210306
    end         =  20220306
    metrics_file= "toto.txt"
    eval("plotMetrics(begin, end, metrics_file, envVarDict)")

    pq_size = registryDict['pq_size']

    pq_path= registryDict['pq_path']

    if checkDiskSpace(pq_path, pq_size): 
        print(f"Enough space to create a queue in fast mode? Yes!")
    else:
        print(f"Enough space to create a queue in fast mode? No!")

