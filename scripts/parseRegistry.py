
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

# Third party imports
from xml.dom.minidom import parse
import xml.dom.minidom
import re

from xml.etree.ElementTree import ElementTree, dump


# Singleton Pattern

class RegistryParser(object):
    _instance = None

    registryEntries = {

        "delete_info_files":            {"delete-info-files":           0},
        "insertion_check_period":       {"insertion-check-interval":    0},
        "reconMode":                    {"reconciliation-mode":         0},
        "hostname":                     {"hostname":                    0},
        # check-time
        "check_time_enabled":           {"enabled":                     0},   
        "check_time_limit":             {"limit":                       0},  
        "warn_if_check_time_disabled":  {"warn-if-disabled":            0},  
        # ntp
        "ntpdate_command":              {"command":                     0}, 
        "ntpdate_servers":              {"servers":                     0}, 
        "ntpdate_timeout":              {"timeout":                     0}, 
        # log
        "num_logs":                     {"count":                       0},
        "log_file":                     {"file":                        0},
        "log_rotate":                   {"rotate":                      0},
        # metrics
        "num_metrics":                  {"count":                       1},
        "metrics_file":                 {"file":                        1},
        "metrics_files":                {"files":                       0},
        "netstat":                      {"netstat-command":             0},
        "top":                          {"top-command":                 0},
        # pqact
        "pqact_conf":                   {"config-path":                 0},
        # queue
        "pq_path":                      {"path":                        0},
        "pq_size":                      {"size":                        0},
        "pq_slots":                     {"slots":                       0},
        # surf
        "surf_path":                    {"path":                        1},
        "surf_size":                    {"size":                        1},  #<size>2M</size>   5G, 3K : to convert
        # scour
        "scour_file":                   {"config-path":                 2},
        #ldmd
        "ldmd_conf":                    {"config-path":                 3},
        "ip_addr":                      {"ip-addr":                     0},
        "max_clients":                  {"max-clients":                 0},
        "max_latency":                  {"max-latency":                 0},
        "port":                         {"port":                        0},
        "server_time_offset":           {"time-offset":                 0},
        # fmtp
        "oess_pathname":                {"oess-pathname":               0},
        "fmtp_retx_timeout":            {"fmtp-retx-timeout":           0}

    }



    def __new__(self, ldmhome):

        if self._instance is None:
            #print('Creating ParseRegistry singleton:')
            self._instance = super(RegistryParser, self).__new__(self)
            # Put any initialization here.

            self.registry_xml = f"{ldmhome}/etc/registry.xml"
            self.registry_xml = "registry.xml"           # <<<<--- remove in production
            self.DOMTree = xml.dom.minidom.parse(self.registry_xml)   
            #print(self.registryEntries)  
            
            missingXmlElements = list()

            for entry, val in self.registryEntries.items():
                #print(f"ParseRegistry: {entry}, {val}")
                xmlElem = list(val.keys())[0]
                rank = list(val.values())[0]

                try:
                    tagName = self.DOMTree.getElementsByTagName(xmlElem)[rank].firstChild.data
                    #print(f"\t --> {entry}: {tagName}  ")
                except Exception as e:
                        print(f"\tPlease check XML element: {xmlElem} ")
                        missingXmlElements.append(xmlElem)
                        continue

                self.registryEntries[entry]= tagName

                # 2. Validate the ip_addr. Set default to 0.0.0.0
                regex = "^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
                ipAddress = tagName
                if entry == "ip_addr" and not re.search(regex, ipAddress):
                    print(f"\n\tWARNING: ip_addr ({ipAddress}) is incorrected! Defaulted to '0.0.0.0'\n")
                    self.registryEntries[entry]= "0.0.0.0"             

                # 3.
                if entry == "ntpdate_servers" :
                    self.registryEntries[entry]= self.registryEntries[entry].split()


            # Check for missing atrributes values.
            if missingXmlElements:
                print(f"\n\n\tMissing attributes values in the registry.xml:\n{missingXmlElements}\n")
                print("\tPlease fix the relevant attributes and retry. Exiting!...\n")
                exit(0)

            
            self.computeProductQueueElementsDefault(self)

            # Convert surfqueue size 
            pqsurfSize      = self.registryEntries["surf_size"]
            expandedSize    = self.convertSize(self, pqsurfSize)
            if expandedSize == -1:
                print(f"\tPlease check the registry. Format of 'surfqueue_size' is incorrect.\n")
                exit(0)

            self.registryEntries["surf_size"] = expandedSize


            # 5. Convert all other numeral strings to numbers:
            self.stringToInt(self)

            # 6.
            # Check the hostname for a fully-qualified version.
            # More validation may be required
            if self.registryEntries['hostname'].startswith("."):
                HOSTNAME="HOSTNAME"
                errmsg = f"\n\tError: The LDM-hostname is not fully-qualified. \
                    \n\tExecute the command 'regutil -s <hostname> regpath" + "{HOSTNAME} \
                    \n\tto set the fully-qualified name of the host."
                print(errmsg)
                exit(0);


        return self._instance
        

    def stringToInt(self):

        relevantEntries = [
            "delete_info_files",
            "insertion_check_period",
            "check_time_enabled",
            "check_time_limit",
            "warn_if_check_time_disabled",
            "ntpdate_timeout",
            "num_logs",
            "log_rotate",
            "num_metrics",
            "max_clients",
            "max_latency",
            "port",
            "server_time_offset",
            "fmtp_retx_timeout"
        ]
        
        for attr in relevantEntries: 
            try:
                self.registryEntries[attr]           = int(self.registryEntries[attr])
            except Exception as e:
                print(e)

        
    # More validation may be required
    def convertSize(self, q_size):

        str_len = len( q_size )
        units = {"K": 10**3, "M": 10**6, "G": 10**9, "T": 10**12}

        if not q_size[-1] in units.keys(): ## assume a number with no unit
            # check the number
            try:
                return int(float(q_size))    
            except:
                print(f"\n\n\tError in converting pq_size: {q_size}")
                return -1
                
        # a unit exists
        unit    = q_size[-1]
        number  = q_size[:-1]

        # check the number
        try:
            return int(float(number)*units[unit])    
        except:
            print(f"Error in converting q_size: {q_size}")
            return -1



    def computeProductQueueElementsDefault(self):
            
        reg         = self.registryEntries
        pq_size     = reg['pq_size']  
        pq_slots    = reg['pq_slots']             

        #
        # 1. NO more than one element can be set as "default"
        #
        if pq_size == "default" and pq_slots == "default":
            print(f"\n\tPlease check the queue XML elements: (slots, size). Not ALL elements can be 'default'. \n")
            exit(0)

        if pq_size == "default":
            pq_size = "2G"      # an arbitrary default
        pq_size = self.convertSize(self, pq_size)
        if pq_size == -1:
            print(f"\tPlease check the registry. Format of {pq_size} is incorrect.\n")
            exit(0)

        self.registryEntries['pq_size'] = pq_size

        if pq_slots == "default":
            pq_slots = "35714"

        pq_slots = self.convertSize(self, pq_slots)
        if pq_slots == -1:
            print(f"\tPlease check the registry. Format of {pq_slots} is incorrect.\n")
            exit(0)

        self.registryEntries['pq_slots'] = pq_slots


    #def modifyRegistry(self, registryDom, newSize, newSlots):
    def modifyRegistry(self, registryDom, element, newValue):
              
        try:
            tagName    = registryDom.getElementsByTagName(element)[0]
            self.replaceText(tagName, newValue)

            with open(self.registry_xml, "w") as registryHandle:
                print(registryDom.toxml(), file=registryHandle)

        except Exception as e:
            print(e)
            errmsg(f"Could not replace size and slots values into registry: {self.registry_xml}")


    # Replace an XLM element's value. Called from modifyRegstry()
    def replaceText(self, node, newText):
        if node.firstChild.nodeType != node.TEXT_NODE:
            raise Exception("Node does not contain text")

        node.firstChild.replaceWholeText(newText)


    def getRegistryEntries(self):
        return self.registryEntries


    def prettyPrintRegistry(self):
        print(f"\n--> Registry items:\n")
        for k, v in self.registryEntries.items():
            print(f"\t{k} \t{v}")



if __name__ == "__main__":

    ldmhome = "/home/miles/projects/ldm"

    c = RegistryParser(ldmhome)
    c.prettyPrintRegistry()
    
    newMaxLatency = 3600
    c.modifyRegistry(c.DOMTree,  "max-latency", newMaxLatency)

    newTimeOffset = 3600
    c.modifyRegistry(c.DOMTree,  "time-offset", newTimeOffset)

    newSize = "2G"
    c.modifyRegistry(c.DOMTree, "size", newSize)

    newSlots = 34000
    c.modifyRegistry(c.DOMTree, "slots", newSlots)