import os
from parseRegistry import RegistryParser
from environHandler import LDMenvironmentHandler
import psutil
import time

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



###############################################################################
# check if the LDM is running.  return 0 if running, -1 if not.
###############################################################################

def isRunning(reg, envir, ldmpingFlag):    

    ldmhome = os.environ.get("LDMHOME", None)

    if ldmhome == None:
        print(f"LDMHOME is not set. Bailing out...")
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

def checkLdm():

    status   = 0
    pid_file = env['pid_file']
    ip_addr  = env['ip_addr']

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


###############################################################################
# stop the LDM server
###############################################################################

def stopLdm(reg, envVar):

    status = 0;                     # default success

    # check if LDM is running: 0: running, -1: NOT running
    status = isRunning(reg, envVar, True)

    if status != 0:
        print("The LDM server is NOT running or its process-ID is 'unavailable'")
    
    else:
        
        # kill the server and associated processes
        print("Stopping the LDM server...\n")
        rpc_pid = envVar['pid']

        kill_rpc_pid_cmd = f"kill {rpc_pid}"
        print(f"StopLdm(): kill RPC pid:  {kill_rpc_pid_cmd}\n");
        os.system( kill_rpc_pid_cmd );

        # we may need to sleep to make sure that the port is deregistered
        while isRunning(reg, envVar, True) == 0: 
            time.sleep(1);
        
        pid_file     = envVar['pid_file']
        pid_filePath = Path(pid_file)
        if 0 == status:
            # remove product-information files that are older than the LDM pid-file.
            removeOldProdInfoFiles(envVar, pid_file)

            # get rid of the pid file
            print(f"\n\tUnlinking pid file: {pid_filePath}\n")
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

    isRunning(registryDict, envVarDict, True)

    envHandler.prettyPrintEnvVars()
    regHandler.prettyPrintRegistry()

    # new log rotation
    #newLog(registryDict)

    # LDM stop
    stopLdm(registryDict, envVarDict)
