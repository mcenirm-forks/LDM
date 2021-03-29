#!/usr/bin/env python3
#
#
# Description: This Python module provides support to parse the user's
# entered ldmadmin commands on the command line
#
#
#   @file:  parseCLI.py
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
import os
import argparse


class CLIParser:
    ldmPQDefaultPath='LDM Default: $LDMHOME/ldm/var/queues/ldm.pq'
    ldmPQSurfDefaultPath='pqsurf(1) default: $LDMHOME/ldm/var/queues/pqsurf.pq'

    ldmCommandsDict={
    	"start": ["[-v] [-x] [-m maxLatency] [-o offset] [-q q_path] [-M max_clients] [conf_file]",	"Starts the LDM"],
    	"stop":					["",								"Stops the LDM"],
        "restart":				["[-v] [-x] [-m maxLatency] [-o offset] [-q q_path] [-M max_clients] [conf_file]",	"Restarts a running LDM"],
        "mkqueue":				["[-v] [-x] [-c] [-f] [-q q_path]",	"Creates a product-queue"],
        "delqueue":				["[-q q_path]",						"Deletes a product-queue"],
        "mksurfqueue":			["[-v] [-x] [-c] [-f] [-q q_path]",	"Creates a product-queue for pqsurf(1)"],
        "delsurfqueue":			["[-q q_path]",						"Deletes a pqsurf(1) product-queue"],
        "newlog":				["[-n numlogs] [-l logfile]",		"Rotates a log file"],
        "scour":				["",		"Scours data directories"],
        "isrunning":			["",		"Exits status 0 if LDM is running else exit 1"],
        "checkinsertion":		["",		"Checks for recent insertion of data-product into product-queue"],
        "vetqueuesize":			["",		"Vets the size of the product-queue"],
        "pqactcheck":			["[-p pqact_conf] [conf_file]",		"Checks syntax of pqact(1) files"],
        "pqactHUP":				["",		"Sends HUP signal to pqact(1) program"],
        "queuecheck":			["",		"Checks for product-queue corruption"],
        "watch":				["[-f feedset]",					"Monitors incoming products"],
        "config":				["",		"Prints LDM configuration"],
        "log":					["",		"Pages through the LDM log file"],
        "tail":					["",		"Monitors the LDM log file"],
        "checktime":			["",		"Checks the system clock"],
        "clean":				["",		"Cleans up after an abnormal termination"],                                                 
        "printmetrics":			["",		"Prints LDM metrics"],
        "addmetrics":			["",		"Accumulates LDM metrics"],
        "plotmetrics":			["[-b begin] [-e end]",				"Plots LDM metrics"],
        "newmetrics":			["",		"Rotates the metrics files"],
        "updategempaktables":	["",		"Updates the GEMPAK tables"],
        "usage":				["",		"Prints this message"]
        
    }
    lockRequiringCmds = ["start", "restart", "stop", "mkqueue", "delqueue", "mksurfqueue", "delsurfqueue", "vetqueuesize", "check"]

    def __init__(self):

        # commands and their options
        
        self.ldmShortCmdsList       = []
        
        for cmd, optionList in self.ldmCommandsDict.items():
            self.ldmShortCmdsList.append(cmd)

        self.cliParser = argparse.ArgumentParser(
            prog='ldmadmin',
            description='''This file is the ldmadmin script that 
            is used to launch various programs that belong in the LDM package.''',
            usage='''%(prog)s command [options]\n''',
            epilog='''

            Thank you for using %(prog)s...

            '''
            )

    def getFullCommandsDict(self):
        return self.ldmCommandsDict


    def prettyPrintCommandsDict(self):
        print(f"\n--> LDM Commands:\n")
        for k, v in self.ldmCommandsDict.items():
            print(f"\t{k} \t{v}")


    def getCmdsList(self):
        return self.ldmShortCmdsList


    def isLockingRequired(self, cmd):
        if cmd in self.lockRequiringCmds:
            return True
        return False

    def cliParserAddArguments(self, cmd):

        self.cliParser.add_argument(cmd, help='', metavar='')
        
        if cmd == "start":            
            self.cliParser.add_argument('-v',               action='store_true', help='verbose', required=False)
            self.cliParser.add_argument('-x',               action='store_true', help='debug', required=False)
            self.cliParser.add_argument('-m maxLatency',    action="store", dest='m', type=int,  help='Maximum latency', metavar='', required=False)
            self.cliParser.add_argument('-o offset',        action="store", dest='o', type=int,  help='', metavar='', required=False)
            self.cliParser.add_argument('-q q_path',        action="store", dest='q', type=str,  default=os.path.expandvars('$LDMHOME/var/queues/ldm.pq'), help='', metavar='', required=False)
            self.cliParser.add_argument('-M max_clients',   action="store", dest='M', type=int,  help='', metavar='', required=False)
            self.cliParser.add_argument('conf_file',        nargs='?', type=None, default=os.path.expandvars('$LDMHOME/etc/ldmd.conf'), help='', metavar='')
    
        if cmd == "mkqueue":
            self.cliParser.add_argument('-v',       action='store_true', help='verbose', required=False)
            self.cliParser.add_argument('-x',       action='store_true', help='debug', required=False)
            self.cliParser.add_argument('-c',       action='store_true', help='', required=False)
            self.cliParser.add_argument('-f',       action='store_true', help='', required=False)
            self.cliParser.add_argument('-q q_path', action="store", dest='q', default=os.path.expandvars('$LDMHOME/var/queues/ldm.pq'), help='', metavar='', required=False)
        
        #(key ,val) = self.cliParser.parse_known_args()

        if cmd == "delqueue":
            self.cliParser.add_argument('-q q_path', action="store", dest='q', type=str, default=os.path.expandvars('$LDMHOME/var/queues/ldm.pq'), help='', metavar='', required=False)

        if cmd == "mksurfqueue":
            self.cliParser.add_argument('-v',       action='store_true', help='verbose', required=False)
            self.cliParser.add_argument('-x',       action='store_true', help='debug', required=False)
            self.cliParser.add_argument('-c',       action='store_true', help='', required=False)
            self.cliParser.add_argument('-f',       action='store_true', help='', required=False)
            self.cliParser.add_argument('-q q_path',action="store", dest='q', default=os.path.expandvars('$LDMHOME/var/queues/pqsurf.pq'), help='', metavar='', required=False)

        if cmd == "delsurfqueue":
            self.cliParser.add_argument('-q q_path', action="store", dest='q', type=str, default=os.path.expandvars('$LDMHOME/var/queues/pqsurf.pq'), help='', metavar='', required=False)

        if cmd == "newlog":
            self.cliParser.add_argument('-n numlogs', action="store", dest='n', default=7, type=int,    help='', metavar='', required=False)
            self.cliParser.add_argument('-l logfile', action="store", dest='l', type=str, default=os.path.expandvars('$LDMHOME/var/logs/ldmd.log'), help='', metavar='', required=False)     

        if cmd == "pqactcheck":
            self.cliParser.add_argument('-p pqact_conf', action="store", dest='p', type=str,  default=os.path.expandvars('$LDMHOME/etc/pqact.conf'), help='', metavar='', required=False)
            self.cliParser.add_argument('conf_file',     nargs='?', type=str,  default=os.path.expandvars('$LDMHOME/etc/ldmd.conf'), help='', metavar='')

        if cmd == "watch":
            self.cliParser.add_argument('-f feedset', action="store", dest='f', default='ANY',  help='', metavar='', required=False)
            self.cliParser.add_argument('-p pattern', action="store", dest='p', default='.*',   help='', metavar='', required=False)

        if cmd == "newlog":                                                        # begin: YYYYMMDD[.hh[mm[ss]]]
            self.cliParser.add_argument('-b begin', action="store", dest='b', default=19700101, type=float, help='', metavar='', required=False)
            self.cliParser.add_argument('-e end',   action="store", dest='e', default=30000101, type=float, help='', metavar='', required=False)
        
        # commands without arguments do not need to be parsed.
        #############################################################################

        args, config_file_argList = self.cliParser.parse_known_args()

        cliDico = vars(args)     # vars(): converts namespace to dict
        cliDico.pop(cmd)    # remove cmd from dico
        if len(config_file_argList) == 1:
            cliDico['conf_file'] = config_file_argList[0]
        
        #print(f"\n\targs dico: {cliDico}\n")

        return cliDico 
        

    def buildCLIcommand(self, cmd, namespaceDict):
        fullCommand=f"{cmd} "

        add_v = 1
        add_x = 0
        pqact_conf_option = 0
        pqact_conf = ""
        
        for key, val in namespaceDict.items():
            
            if key == 'v' and val == False:
                add_v = 0

            if key == 'x' and val == True:
                add_x = 1

            if key == 'p' and not val == None:
                
                default = os.path.expandvars('$LDMHOME/etc/pqact.conf')
                if default != val:
                    pqact_conf_option = 1
                    pqact_conf = val        
                else: 
                    pqact_conf = default

            if not val == None and not val == False:
                if val == True:
                    val = ""
                if key == "cmd":
                    continue

                if key == "conf_file":
                    fullCommand += f"{val} "                    
                    continue

                fullCommand += f"-{key} {val} "
        
        if add_v == 0 and add_x == 1:
            # option -x goes along with -v, add -v
            fullCommand += f"-v"
        
        # add to CLIdico: pqact_conf_option and its value
        namespaceDict['pqact_conf_option'] = pqact_conf_option
        namespaceDict['pqact_conf'] = pqact_conf
        
        #print(namespaceDict)
        return fullCommand



    def usage(self):

        text='''
    Usage: ldmadmin command [arg ...]

commands:
    start [-v] [-x] [-m maxLatency] [-o offset] [-q q_path] [-M max_clients]
        [conf_file]                          Starts the LDM
    stop                                     Stops the LDM
    restart [-v] [-x] [-m maxLatency] [-o offset] [-q q_path] [-M max_clients]
        [conf_file]                          Restarts a running LDM
    mkqueue [-v] [-x] [-c] [-f] [-q q_path]  Creates a product-queue
    delqueue [-q q_path]                     Deletes a product-queue
    mksurfqueue [-v] [-x] [-c] [-f] [-q q_path]
                                             Creates a product-queue for
                                                 pqsurf(1)
    delsurfqueue [-q q_path ]                Deletes a pqsurf(1) product-queue
    newlog [-n numlogs] [-l logfile]         Rotates a log file
    scour                                    Scours data directories
    isrunning                                Exits status 0 if LDM is running
                                                 else exit 1
    checkinsertion                           Checks for recent insertion of
                                                 data-product into product-queue
    vetqueuesize                             Vets the size of the product-queue
    pqactcheck [ldmd_conf]                   Checks syntax of pqact(1) files
    pqactcheck [-p pqact_conf]               Checks syntax of pqact(1) files
    pqactHUP                                 Sends HUP signal to pqact(1)
                                                 program
    queuecheck                               Checks for product-queue corruption
    watch [-f feedset] [-p pattern]          Monitors incoming products
    config                                   Prints LDM configuration
    log                                      Pages through the LDM log file
    tail                                     Monitors the LDM log file
    checktime                                Checks the system clock
    clean                                    Cleans up after an abnormal
                                                 termination
    printmetrics                             Prints LDM metrics
    addmetrics                               Accumulates LDM metrics
    plotmetrics [-b begin] [-e end]          Plots LDM metrics
    newmetrics                               Rotates the metrics files
    updategempaktables                       Updates the GEMPAK tables
    usage                                    Prints this message

options:
    -b begin        Begin time as YYYYMMDD[.hh[mm[ss]]]
    -c              Clobber an existing product-queue
    -e end          End time as YYYYMMDD[.hh[mm[ss]]]
    -f              Create queue "fast"
    -f feedset      Feed-set to use with command. Default: ANY
    -p pattern
    -l logfile      Pathname of logfile. Default: $LDMHOME/ldm/var/logs/ldmd.log
    -m maxLatency   Conditional data-request temporal-offset
    -M max_clients  Maximum number of active clients
    -n numlogs      Number of logs to rotate. Default: 7
    -o offset       Unconditional data-request temporal-offset
    -q q_path       Specify a product-queue path. LDM Default: $LDMHOME/ldm/var/queues/ldm.pq,
                    pqsurf(1) default: $LDMHOME/ldm/var/queues/pqsurf.pq
    -v              Turn on verbose mode
    -x              Turn on debug mode (includes verbose mode)

conf_file:
    LDM configuration file to use. Default: $LDMHOME/ldm/etc/ldmd.conf


    '''

        print(text)


if __name__ == "__main__":


    cliInst         = CLIParser()              # instance of CLIParser
    cmdsDico        = cliInst.getFullCommandsDict()
    
    print(cmdsDico)


