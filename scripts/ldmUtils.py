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
    
    
    print(f"\n")



# Returns
#       0       Success. Nothing wrong or it's too soon to tell.
#       1       The queue is too small or the maximum-latency parameter is
#               too large.
#       2       Major failure.
# sub vetQueueSize
# {
#     my $status = 2;                     # default major failure
#     my $etime = getElapsedTimeOfServer();

#     if ($etime < $max_latency) {
#         $status = 0;                    # too soon to tell
#     }
#     else {
#         chomp(my $line = `pqmon -S -q $pq_path`);

#         if ($?) {
#             errmsg("vetQueueSize(): pqmon(1) failure");
#             $status = 2;                # major failure
#         }
#         else {
#             my @params = split(/\s+/, $line);
#             my $isFull = $params[0];
#             my $ageOldest = $params[7];
#             my $minVirtResTime = $params[9];
#             my $mvrtSize = $params[10];
#             my $mvrtSlots = $params[11];

#             if (!$isFull || $minVirtResTime < 0 
#                     || $minVirtResTime >= $max_latency
#                     || $mvrtSize <= 0 || $mvrtSlots <= 0) {
#                 $status = 0;            # reconciliation not yet needed
#             }
#             else {
#                 my $increaseQueue = "increase queue";
#                 my $decreaseMaxLatency = "decrease maximum latency";
#                 my $doNothing = "do nothing";

#                 errmsg("vetQueueSize(): The maximum acceptable latency ".
#                     "(registry parameter \"regpath{MAX_LATENCY}\": ".
#                     "$max_latency seconds) is greater ".
#                     "than the observed minimum virtual residence time of ".
#                     "data-products in the queue ($minVirtResTime seconds).  ".
#                     "This will hinder detection of duplicate data-products.");

#                 print "The value of the ".
#                     "\"regpath{RECONCILIATION_MODE}\" registry-parameter is ".
#                     "\"$reconMode\"\n";

#                 if ($reconMode eq $increaseQueue) {
#                     my @newParams = computeNewQueueSize($minVirtResTime, 
#                             $ageOldest, $mvrtSize, $mvrtSlots);
#                     my $newByteCount = $newParams[0];
#                     my $newSlotCount = $newParams[1];
#                     my $newQueuePath = "$pq_path.new";

#                     errmsg("vetQueueSize(): Increasing the capacity of the ".
#                             "queue to $newByteCount bytes and $newSlotCount ".
#                             "slots...");

#                     if (system("pqcreate -c -S $newSlotCount -s $newByteCount ".
#                             "-q $newQueuePath")) {
#                         errmsg("vetQueueSize(): Couldn't create new queue: ".
#                             "$newQueuePath");
#                         $status = 2;            # major failure
#                     }
#                     else {
#                         my $restartNeeded;

#                         $status = 0;            # success so far

#                         if (!isRunning($pid_file, $ip_addr)) {
#                             $restartNeeded = 0;
#                         }
#                         else {
#                             if (stop_ldm()) {
#                                 $status = 2;        # major failure
#                             }
#                             else {
#                                 $restartNeeded = 1;
#                             }
#                         }
#                         if (0 == $status) {
#                             if (grow($pq_path, $newQueuePath)) {
#                                 $status = 2;        # major failure
#                             }
#                             else {
#                                 print "Saving new queue parameters...\n";
#                                 if (saveQueuePar($newByteCount,
#                                             $newSlotCount)) {
#                                     $status = 2;    # major failure
#                                 }
#                             }

#                             if ($restartNeeded) {
#                                 print "Restarting the LDM...\n";
#                                 if (start_ldm()) {
#                                     errmsg("vetQueueSize(): ".
#                                         "Couldn't restart the LDM");
#                                     $status = 2;    # major failure
#                                 }
#                             }
#                         }               # LDM stopped
#                     }                   # new queue created

#                     system("pqutil -C");# reset queue metrics
#                 }                       # mode is increase queue
#                 elsif ($reconMode eq $decreaseMaxLatency) {
#                     if (0 >= $minVirtResTime) {
#                         # Use age of oldest product, instead
#                         $minVirtResTime = $ageOldest;
#                     }
#                     $minVirtResTime = 1 if (0 >= $minVirtResTime);
#                     my $newMaxLatency = $minVirtResTime;
#                     my $newTimeOffset = $newMaxLatency;

#                     errmsg("vetQueueSize(): Decreasing the maximum acceptable ".
#                         "latency and the time-offset of requests (registry ".
#                         "parameters \"regpath{MAX_LATENCY}\" and ".
#                         "\"regpath{TIME_OFFSET}\") to $newTimeOffset ".
#                         "seconds...");

#                     print "Saving new time parameters...\n";
#                     if (saveTimePar($newTimeOffset, $newMaxLatency)) {
#                         $status = 2;    # major failure
#                     }
#                     else {
#                         if (!isRunning($pid_file, $ip_addr)) {
#                             $status = 0;# success
#                         }
#                         else {
#                             print "Restarting the LDM...\n";
#                             if (stop_ldm()) {
#                                 errmsg("vetQueueSize(): Couldn't stop LDM");
#                                 $status = 2;        # major failure
#                             }
#                             else {
#                                 if (start_ldm()) {
#                                     errmsg("vetQueueSize(): ".
#                                             "Couldn't start LDM");
#                                     $status = 2;    # major failure
#                                 }
#                                 else {
#                                     $status = 0     # success
#                                 }
#                             }           # LDM stopped
#                         }               # LDM is running
#                     }                   # new time parameters saved

#                     system("pqutil -C");# reset queue metrics
#                 }                       # mode is decrease max latency
#                 elsif ($reconMode eq $doNothing) {
#                     my @newParams = computeNewQueueSize($minVirtResTime,
#                             $ageOldest, $mvrtSize, $mvrtSlots);
#                     my $newByteCount = $newParams[0];
#                     my $newSlotCount = $newParams[1];
#                     errmsg("vetQueueSize(): The queue should be $newByteCount ".
#                         "bytes in size with $newSlotCount slots or the ".
#                         "maximum-latency parameter should be decreased to ".
#                         "$minVirtResTime seconds. You should set ".
#                         "registry-parameter \"regpath{RECONCILIATION_MODE}\" ".
#                         "to \"$increaseQueue\" or \"$decreaseMaxLatency\" or ".
#                         "manually adjust the relevant registry parameters and ".
#                         "recreate the queue.");
#                     $status = 1;        # small queue or big max-latency
#                 }
#                 else {
#                     errmsg("Unknown reconciliation mode: \"$reconMode\"");
#                     $status = 2;        # major failure
#                 }
#             }                           # reconciliation needed
#         }                               # pqmon(1) success
#     }                                   # queue has reached equilibrium

#     return $status;sub vetQueueSize
# {
#     my $status = 2;                     # default major failure
#     my $etime = getElapsedTimeOfServer();

#     if ($etime < $max_latency) {
#         $status = 0;                    # too soon to tell
#     }
#     else {
#         chomp(my $line = `pqmon -S -q $pq_path`);

#         if ($?) {
#             errmsg("vetQueueSize(): pqmon(1) failure");
#             $status = 2;                # major failure
#         }
#         else {
#             my @params = split(/\s+/, $line);
#             my $isFull = $params[0];
#             my $ageOldest = $params[7];
#             my $minVirtResTime = $params[9];
#             my $mvrtSize = $params[10];
#             my $mvrtSlots = $params[11];

#             if (!$isFull || $minVirtResTime < 0 
#                     || $minVirtResTime >= $max_latency
#                     || $mvrtSize <= 0 || $mvrtSlots <= 0) {
#                 $status = 0;            # reconciliation not yet needed
#             }
#             else {
#                 my $increaseQueue = "increase queue";
#                 my $decreaseMaxLatency = "decrease maximum latency";
#                 my $doNothing = "do nothing";

#                 errmsg("vetQueueSize(): The maximum acceptable latency ".
#                     "(registry parameter \"regpath{MAX_LATENCY}\": ".
#                     "$max_latency seconds) is greater ".
#                     "than the observed minimum virtual residence time of ".
#                     "data-products in the queue ($minVirtResTime seconds).  ".
#                     "This will hinder detection of duplicate data-products.");

#                 print "The value of the ".
#                     "\"regpath{RECONCILIATION_MODE}\" registry-parameter is ".
#                     "\"$reconMode\"\n";

#                 if ($reconMode eq $increaseQueue) {
#                     my @newParams = computeNewQueueSize($minVirtResTime, 
#                             $ageOldest, $mvrtSize, $mvrtSlots);
#                     my $newByteCount = $newParams[0];
#                     my $newSlotCount = $newParams[1];
#                     my $newQueuePath = "$pq_path.new";

#                     errmsg("vetQueueSize(): Increasing the capacity of the ".
#                             "queue to $newByteCount bytes and $newSlotCount ".
#                             "slots...");

#                     if (system("pqcreate -c -S $newSlotCount -s $newByteCount ".
#                             "-q $newQueuePath")) {
#                         errmsg("vetQueueSize(): Couldn't create new queue: ".
#                             "$newQueuePath");
#                         $status = 2;            # major failure
#                     }
#                     else {
#                         my $restartNeeded;

#                         $status = 0;            # success so far

#                         if (!isRunning($pid_file, $ip_addr)) {
#                             $restartNeeded = 0;
#                         }
#                         else {
#                             if (stop_ldm()) {
#                                 $status = 2;        # major failure
#                             }
#                             else {
#                                 $restartNeeded = 1;
#                             }
#                         }
#                         if (0 == $status) {
#                             if (grow($pq_path, $newQueuePath)) {
#                                 $status = 2;        # major failure
#                             }
#                             else {
#                                 print "Saving new queue parameters...\n";
#                                 if (saveQueuePar($newByteCount,
#                                             $newSlotCount)) {
#                                     $status = 2;    # major failure
#                                 }
#                             }

#                             if ($restartNeeded) {
#                                 print "Restarting the LDM...\n";
#                                 if (start_ldm()) {
#                                     errmsg("vetQueueSize(): ".
#                                         "Couldn't restart the LDM");
#                                     $status = 2;    # major failure
#                                 }
#                             }
#                         }               # LDM stopped
#                     }                   # new queue created

#                     system("pqutil -C");# reset queue metrics
#                 }                       # mode is increase queue
#                 elsif ($reconMode eq $decreaseMaxLatency) {
#                     if (0 >= $minVirtResTime) {
#                         # Use age of oldest product, instead
#                         $minVirtResTime = $ageOldest;
#                     }
#                     $minVirtResTime = 1 if (0 >= $minVirtResTime);
#                     my $newMaxLatency = $minVirtResTime;
#                     my $newTimeOffset = $newMaxLatency;

#                     errmsg("vetQueueSize(): Decreasing the maximum acceptable ".
#                         "latency and the time-offset of requests (registry ".
#                         "parameters \"regpath{MAX_LATENCY}\" and ".
#                         "\"regpath{TIME_OFFSET}\") to $newTimeOffset ".
#                         "seconds...");

#                     print "Saving new time parameters...\n";
#                     if (saveTimePar($newTimeOffset, $newMaxLatency)) {
#                         $status = 2;    # major failure
#                     }
#                     else {
#                         if (!isRunning($pid_file, $ip_addr)) {
#                             $status = 0;# success
#                         }
#                         else {
#                             print "Restarting the LDM...\n";
#                             if (stop_ldm()) {
#                                 errmsg("vetQueueSize(): Couldn't stop LDM");
#                                 $status = 2;        # major failure
#                             }
#                             else {
#                                 if (start_ldm()) {
#                                     errmsg("vetQueueSize(): ".
#                                             "Couldn't start LDM");
#                                     $status = 2;    # major failure
#                                 }
#                                 else {
#                                     $status = 0     # success
#                                 }
#                             }           # LDM stopped
#                         }               # LDM is running
#                     }                   # new time parameters saved

#                     system("pqutil -C");# reset queue metrics
#                 }                       # mode is decrease max latency
#                 elsif ($reconMode eq $doNothing) {
#                     my @newParams = computeNewQueueSize($minVirtResTime,
#                             $ageOldest, $mvrtSize, $mvrtSlots);
#                     my $newByteCount = $newParams[0];
#                     my $newSlotCount = $newParams[1];
#                     errmsg("vetQueueSize(): The queue should be $newByteCount ".
#                         "bytes in size with $newSlotCount slots or the ".
#                         "maximum-latency parameter should be decreased to ".
#                         "$minVirtResTime seconds. You should set ".
#                         "registry-parameter \"regpath{RECONCILIATION_MODE}\" ".
#                         "to \"$increaseQueue\" or \"$decreaseMaxLatency\" or ".
#                         "manually adjust the relevant registry parameters and ".
#                         "recreate the queue.");
#                     $status = 1;        # small queue or big max-latency
#                 }
#                 else {
#                     errmsg("Unknown reconciliation mode: \"$reconMode\"");
#                     $status = 2;        # major failure
#                 }
#             }                           # reconciliation needed
#         }                               # pqmon(1) success
#     }                                   # queue has reached equilibrium

#     return $status;
# }
# }



###############################################################################
# check if the LDM is running.  return 0 if running, -1 if not.
###############################################################################

def isRunning(reg, envir, ldmpingFlag):    

    print(f"\n - Checking if LDM is running...")
    ldmhome = os.environ.get("LDMHOME", None)

    if ldmhome == None:
        print(f"\n\tLDMHOME is not set. Bailing out...\n")
        exit(-1)

    # Ensure that the utilities of this version are favored
    os.environ['PATH'] = ldmhome + "/bin:" + ldmhome + "/util:" + os.environ['PATH']

    # Retrieve ldmd process id (if running):
    pidFilename  = envir['pid_file']
    ip_addr      = reg['ip_addr']
    pid = 0
    with open(pidFilename, 'r') as pidFile:
        pid = pidFile.read().replace('\n','')

    pid     = int(pid)
    running = -1
    envir['pid'] = None
    if psutil.pid_exists(pid):
        #print(f"\n\tprocess with pid { pid } exists!\n")
        envir['pid'] = pid
        running = 0
        

    # The following test is incompatible with the use of a proxy
    if running != 0 and ldmpingFlag:

        cmd_line = "ldmping -l- -i 0"
        if not ip_addr == "0.0.0.0":
            cmd_line = f"{ cmd_line }  { reg['ip_addr'] }"
        
        cmd_line = f"{ cmd_line } > /dev/null 2>&1"
        running = os.system( cmd_line )
        if running == 0:
            envir['ldmd_running'] = True
        else: 
            envir['ldmd_running'] = False

    return running


###############################################################################
# Check that a data-product has been inserted into the product-queue
###############################################################################

def executePqMon(pq_path):

    failure = 0
    pqmon_cmd_line = f"pqmon -S -q {pq_path}  2>&1"

    try:
        #print(pqmon_cmd_line)
        process_output = subprocess.check_output( pqmon_cmd_line, shell=True )
    
        pqmon_output  = process_output.decode()[:-1]
    
        return failure, pqmon_output

    except:
        print(f"Error: '{pqmon_cmd_line}' FAILED!")
        failure = -1
        return failure, ""


def check_insertion(reg):

    status = 0

    pq_path = "/home/miles/projects/ldm/var/queues/ldm.pq"
    status, pq = executePqMon(pq_path)
    if status == -11:
        print("check_insertion(): pqmon(1) failure")
        return status

    print(f"pqmon: {pq}")

    age= pq.split()[8]
    print(f"Age: {age}")
    insertion_check_period = reg["insertion_check_period"]

    if age > insertion_check_period:
        print(f"\ncheck_insertion(): The last data-product was inserted {age} seconds ago, \
                \nwhich is greater than the registry - parameter 'regpath" + "{INSERTION_CHECK_INTERVAL}" + "'")
        status = -1

    return status


###############################################################################
# rotate the specified log file, keeping $numlog files
###############################################################################

def newLog(reg):

    status = 1;      # default failure

    # Rotate the log file
    newlog_cmd = f"newlog {reg['log_file']} {reg['num_logs']}"
    status = system(newlog_cmd);

    if status != 0:
        print("new_log(): log rotation failed");
    else:
        # Refresh logging
        refresh_logging_cmd = f"refresh_logging"
        status = system(refresh_logging_cmd);
        if status != 0:
            print("new_log(): Couldn't refresh LDM logging");
        else:
            status = 0;        # success
    
    return status;


def getMTime(aPath):

    mtime = Path(aPath).stat().st_mtime
    return int(mtime) 


###############################################################################
# Remove product-information files that are older than the LDM pid-file.
###############################################################################

def removeOldProdInfoFiles(env, pid_file):

    mtime = getMTime(pid_file)
    
    for file in glob.glob('.*.info'):
        file_mTime = getMTime(file)

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
    if not isRunning(pid_file, ip_addr):
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

    return status;


def executeNtpDateCommand(ntpdate_cmd, timeout, ntpServer):

    ntpdate_ls_cmd = f"ls {ntpdate_cmd}  2>&1>/dev/null"
    # Check the ntpdate command
    try:
        proc = subprocess.check_output(ntpdate_ls_cmd, shell=True )

    except Exception as e:
        print(f"ERROR: 'ntpdate' command: {ntpdate_cmd} could not be found! ")
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
    

def getRegVariables(reg):

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


def isCheckTimeEnabled(time, warning_disabled, regUtil_cmd):
    failure = 0
    if time == 0:        
        if warn_disabled == 1:
            print("\n")
            print("WARNING: The checking of the system clock is disabled.")
            print("You might loose data if the clock is off.  To enable this ")
            print("checking, execute the command {regUtil_cmd}")
        failure = 1

    return failure



def areNTPServersAvailable( number_of_servers):
    failure = 0
    if number_of_servers == 0: 
        ntpdate_servers_xpath = f"/check-time/ntpdate/servers"
        warning = f"\nWARNING: No time-servers are specified by the registry \
                    \nparameter '{ntpdate_servers_xpath}'. Consequently, the \
                    \nsystem clock can't be checked and you might loose data if it's off."
        print(warning)
        failure = 1

    return failure
###############################################################################
# Check the system clock
###############################################################################

def checkTime(reg):

    
    failure = 0;

    ntpdate_servers, ntpdate_cmd,\
    ntpdate_timeout, number_of_servers,\
    check_time, check_time_limit,\
    warn_if_check_time_disabled,\
    ntpdate_cmd_xpath, regUtil_cmd =  getRegVariables(reg)

    failure = isCheckTimeEnabled(check_time, warn_if_check_time_disabled, regUtil_cmd)
    if failure == 1:
        return failure
 
    failure = areNTPServersAvailable( number_of_servers)
    if failure == 1:
        return failure

    
    offset = -10000
    nbServs = number_of_servers

    while nbServs > 0:
        i = randrange( nbServs )
        timeServer = ntpdate_servers[i]

        # execute ntpdate on available servers    
        print(f"\n\tChecking time from NTP server: {timeServer}")
        status, offset = executeNtpDateCommand(ntpdate_cmd, ntpdate_timeout, timeServer)
        print(f"\tOffset: {offset}\n")

        if status == -1:
            error = f"\nCouldn't execute the command '{ntpdate_cmd}'. \
                    \nExecute the command '{ntpdate_cmd_xpath}' to set the pathname of \
                    \nthe ntpdate(1) utility to 'path'."
            print(error)

        else:
            if status == -2:
                error = f"\nCouldn't get time from time-server at {timeServer} using the ntpdate(1) \
                        \nutility, {ntpdate_cmd}\". \
                        \nIf the utility is valid and this happens often, then remove {timeServer} \
                        \nfrom registry parameter regpath" + "{NTPDATE_SERVERS}" + "'."

                print(error)
                nbServs -= 1
                # remove this time server from list:
                ntpdate_servers.remove(timeServer)

                # check if no more valid server remain to try out:
                if len(ntpdate_servers) == 0:
                    error = f"\nThere were no valid time servers that could be used to get time from. \
                                \nPlease check the registry parameter 'regutil regpath" + "{NTPDATE_SERVERS}" + "'."
                    print(error)
                    exit(-1)

                # continue with remaining servers
                #print(ntpdate_servers)
                continue

            else:
               
                if abs(offset) > check_time_limit:
                    error = f"\nThe system clock is more than {check_time_limit} seconds off, \
                                \nwhich is specified by registry parameter 'regpath" + "{CHECK_TIME_LIMIT}" + "'."
                    print(error)

                else:
                    failure = 0;
                
                break


            # print(f"Offset: {offset}")

    
    if failure == 1:

        checkTime_cmd = "\"regutil -u 0 regpath{CHECK_TIME}\""
        print(f"\nYou should either fix the problem (recommended) or disable\
                \ntime-checking by executing the command {checkTime_cmd} (not recommended)." )
    
    return failure


###############################################################################
# stop the LDM server
###############################################################################

def stopLdm(reg, envVar):

    status = 0                     # default success
    kill_status = 0

    # check if LDM is running: 0: running, -1: NOT running
    status = isRunning(reg, envVar, True)

    if status != 0:
        print("\nThe LDM server is NOT running or its process-ID is 'unavailable'")
    
    else:
        
        # kill the server and associated processes
        print(" - Stopping the LDM server...\n")
        rpc_pid = envVar['pid']

        kill_rpc_pid_cmd = f"kill {rpc_pid}"
        print(f"\tstopLdm(): kill RPC pid:  {kill_rpc_pid_cmd}\n");
        kill_status = os.system( kill_rpc_pid_cmd );

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

#    envHandler.prettyPrintEnvVars()
#    regHandler.prettyPrintRegistry()

    # new log rotation: TO-CHECK
    # newLog(registryDict)

    # LDM stop: DONE
    # stopLdm(registryDict, envVarDict)

    # LDM start : TO-DO
    # startLdm(registryDict, envVarDict)

    # LDM check
    #checkLdm(envVarDict)

    # print("checkTime:")
    # checkTime(registryDict)
    # print("checkTime: DONE")


    status = check_insertion(registryDict)
    if status == -1:
        print("check_insertion() failed!")
