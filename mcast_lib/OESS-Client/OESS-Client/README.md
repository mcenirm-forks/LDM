Adds a circuit on the network using the OESS API function `provision_circuit`.
The circuit is created immediately and can be removed by `remove_circuit.py`.

Usage: provision.py wrkgrpName credential desc node1 interface1 vlanId1 node2 interface2 vlanId2 

Where:
wrkgrpName | ID of the workgroup (e.g., “UCAR-LDM”, “Virginia”)
credential | Pathname of YAML file containing AL2S OESS account credentials
desc       | Description of the circuit (e.g., “NEXRAD2 feed”) 
node1      | Name of AL2S switch at one endpoint (e.g., “sdn-sw.ashb.net.internet2.edu”)
interface1 | Specification of port on `node1` (e.g., “1/7”)
vlanId1    | VLAN number for `node`/`interface1` (e.g., “4000”)
node2      | Name of AL2S switch at other endpoint (e.g., “sdn-sw.pitt.net.internet2.edu”)
Interface2 | Specification of port on `node2` (e.g., “et-3/0/0”)
vlanId2    | VLAN number for `node2`/`interface2` (e.g., “4001”)

Output:
On success, the script writes the circuit ID to its standard output stream as a string.

Example:
$ python provision.py Virginia oess-acount.yaml NEXRAD2 \
sdn-sw.ashb.net.internet2.edu et-3/0/0 332 \
sdn-sw.pitt.net.internet2.edu et-8/0/0 332
__________________________________________________________________________

Removes a circuit on the network using the OESS API function ‘remove_circuit’. 
If the circuit has been removed successfully or is scheduled for removal from
the network.

Usage: remove.py wrkgrpName circuit-ID credential desc

Where:
wrkgrpName | ID of the workgroup (e.g., “UCAR-LDM”, “Virginia”)
circuit-ID | Circuit identifier returned by "provision.py"
credential | Pathname of YAML file containing AL2S OESS credentials
desc       | Description of the circuit (e.g., “NEXRAD2 feed”)

Example:
$ python remove.py <circuit-ID> Virginia oess-acount.yaml "NEXRAD2 feed"
__________________________________________________________________________

Modify a circuit with specific circuitId on the network using the OESS API
function `provision_circuit`.

edit.py wrkgrpName credential desc add|del node1 interface1 vlanId1 

Parameters:
wrkgrpName
ID of the workgroup (e.g., “UCAR-LDM”, “Virginia”)
credential
credential for AL2S OESS API account
desc
Description of the circuit (e.g., “NEXRAD2 feed”)
add|delete
The phase ‘add’ means add the endpoint into the circuit; the phase ‘delete’ means delete the existing endpoint in the circuit.
node1
Name of AL2S switch at one endpoint (e.g., “sdn-sw.ashb.net.internet2.edu”)
interface1
Specification of port on `node1` (e.g., “1/7”)
vlanId1
VLAN number for `node`/`interface1` (e.g., “4000”)

Example:
$ python edit.py Virginia oess-acount.yaml NEXRAD2 add sdn-sw.ashb.net.internet2.edu \ et-3/0/0 332