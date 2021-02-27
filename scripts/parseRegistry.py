
#
#
# Description: This Python module provides support to read the XML
# registry
#
#
#   @file:  parseRegistry.py
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

from xml.dom.minidom import parse
import xml.dom.minidom


class RegistryParser:

    registryEntries = {

        "delete_info_files":            {"delete-info-files": 0},
        "insertion_check_period":       {"insertion-check-interval": 0},
        "reconMode":                    {"reconciliation-mode": 0},
        "hostname":                     {"hostname": 0},
        # check-time
        "check_time":                   {"enabled": 0},   
        "check_time_limit":             {"limit": 0},  
        "warn_if_check_time_disabled":  {"warn-if-disabled": 0},  
        # ntp
        "command":                      {"command": 0}, 
        "time_servers":                 {"servers": 0}, # @time_servers = split(/\s+/, $time_servers);
        "ntpdate_timeout":              {"timeout": 0}, 
        # log
        "num_logs":                     {"count": 0},
        "log_file":                     {"file": 0},
        "log_rotate":                   {"rotate": 0},
        # metrics
        "num_metrics":                  {"count": 1},
        "metrics_file":                 {"file": 1},
        "metrics_files":                {"files": 0},
        "netstat":                      {"netstat-command": 0},
        "top":                          {"top-command": 0},
        # pqact
        "pqact_conf":                   {"config-path": 0},
        "pq_path":                      {"path": 0},
        "pq_size":                      {"size": 0},
        "pq_slots":                     {"slots": 0},
        # surf
        "surf_path":                    {"path": 1},
        "surf_size":                    {"size": 1},  #<size>2M</size>   5G, 3K : to convert
        # scour
        "scour_file":                   {"config-path": 2},
        #ldmd
        "ldmd_conf":                    {"config-path": 3},
        "ip_addr":                      {"ip-addr": 0},
        "max_clients":                  {"max-clients": 0},
        "max_latency":                  {"max-latency": 0},
        "port":                         {"port": 0},
        "offset":                       {"time-offset": 0}
    }


    def __init__(self):

        self.DOMTree = xml.dom.minidom.parse("registry.xml")        
        for entry, val in self.registryEntries.items():
        
            xmlElem = list(val.keys())[0]
            rank = list(val.values())[0]

            tagName = self.DOMTree.getElementsByTagName(xmlElem)[rank].firstChild.data
            #print(f"\t --> {entry}: {tagName}  ")
            
            self.registryEntries[entry]= tagName

            # special handling
            # 1,
            if entry == "pq_size" or entry == "surf_size":
                expandedSize = self.convertSize(self.registryEntries[entry])
                if expandedSize == -1:
                    print(f"Please check the registry. Size of {entry} is incorrect.")
                    exit(0)

                self.registryEntries[entry] = expandedSize

            # 2.
            if entry == "time_servers" :
                self.registryEntries[entry]= self.registryEntries[entry].split()

        # 3.
        # Check the hostname for a fully-qualified version.
        #     # More validation may be required
        if self.registryEntries['hostname'].startswith("."):
            HOSTNAME="HOSTNAME"
            errmsg = f"\n\tError: The LDM-hostname is not fully-qualified. \
                \n\tExecute the command 'regutil -s <hostname> regpath{{HOSTNAME}}' \
                \n\tto set the fully-qualified name of the host."
            print(errmsg)
            exit(0);


    # More validation may be required
    def convertSize(self, pq_size):

        str_len = len( pq_size )
        units = {"K": 10**3, "M": 10**6, "G": 10**9, "T": 10**12}

        if not pq_size[-1] in units.keys(): ## assume a number with no unit
            # check the number
            try:
                return int(float(pq_size))    
            except:
                print(f"Error in converting pq_size: {pq_size}")
                return -1
                
        # a unit exists
        unit = pq_size[-1]
        number = pq_size[str_len - 2]
        # check the number
        try:
            return int(float(number)*units[unit])    
        except:
            print(f"Error in converting pq_size: {pq_size}")
            return -1

    def getRegistryEntries(self):
        return self.registryEntries
