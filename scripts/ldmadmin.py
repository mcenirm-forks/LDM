#!/usr/bin/env python3

#
#
# Description: This Python script provides a command line interface to LDM
#  programs.
#
#
#   @file:  ldmadmin.py
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
#
# Files:
#
#  $LDMHOME/ldmd.pid         file containing process group ID
#  $LDMHOME/.ldmadmin.lck    lock file for operations that modify the state of
#                            the LDM system
#  $LDMHOME/.[0-9a-f]*.info  product-information of the last, successfuly-
#                            received data-product
#
###############################################################################

from os import system
import sys
import readline

from signal import signal, SIGINT
from sys 	import exit
from time 	import sleep

import parseCLI 		as ldmCmds
import parseRegistry 	as regPath
import environHandler

EXIT_MESSAGE='\n\tThank you for using ldmadmin...\n\n'


def bye(signal_received, frame):
	# Handle any cleanup here
	exitMessage()


def exitMessage():
	print(f"{EXIT_MESSAGE}")
	exit(0)


class LDMCommandsHandler:
	def __init__(self, ldmCommandsDict):
		self.ldmCommandsDict	= ldmCommandsDict
		self.ldmShortCmdsList	= []
		for cmd, optionList in ldmCommandsDict.items():
			self.ldmShortCmdsList.append(cmd)
	        
	def complete(self,userInput,state):
		results =  [cmd + " " for cmd in self.ldmShortCmdsList if cmd.startswith(userInput)] + [None]
		return results[state]

	def isValidCmd(self, cmd):		
		return cmd in self.ldmShortCmdsList

	def returnCmdCortege(self, cmd):
		return self.ldmCommandsDict[cmd][0]

	def execute(self, cmdToExecute):
		status = 0
		print(f"\n\tExecuting {cmdToExecute}\n")
		
		#nstatus = os.system(cmdToExecute)

		return status


def main():
	signal(SIGINT, bye)
	system('clear')

	regParserInstance = regPath.RegistryParser()

	registryEntries = regParserInstance.getRegistryEntries()
#	print(f"\n\t====> Registry XML: \n {registryEntries} \n")

	envHandlerInstance = environHandler.LDMenvironmentHandler()

	envVariables = envHandlerInstance.getEnvVarsDict()
#	print(f"\n\t====> Environment variables: \n {envVariables} \n")


	# tab completion:
	readline.parse_and_bind("tab: complete")
	dataInstance = ldmCmds.LDMadminData()
	ldmCommandsDict = dataInstance.getFullCommandsDict()
	LDMcommands = LDMCommandsHandler( ldmCommandsDict )
	readline.set_completer(LDMcommands.complete)

	nbArguments=len(sys.argv)
	if nbArguments == 1 or \
		nbArguments == 2 and (sys.argv[1] == "-h" or sys.argv[1] == "--help"):

# Interactive mode
		dataInstance.usage()
		print(f"\n\tInteractive mode (type 'quit' to exit)\n")
	
	else:
# Non-interactive mode (CLI mode)
		cmd=sys.argv[1]
		if not LDMcommands.isValidCmd(cmd):
			print(f"\n\tInvalid ldmadmin command: {cmd}\n")
			sleep(3)
			dataInstance.usage()
			exitMessage()

		# Here, cmd is a valid ldmadmin command:
		if cmd == "usage": 
			dataInstance.usage()

		
		if  nbArguments == 2: # command w/o options
			status = LDMcommands.execute(sys.argv[1])
		else:	
			cliDico = dataInstance.cliParserAddArguments(cmd)
			print(f"\n\nCLI dict: {cliDico}\n")

			cliString = dataInstance.buildCLIcommand(cmd, cliDico)
			status = LDMcommands.execute(cliString)





		# last line:
		exitMessage()

# Interactive mode
	cmd = input('ldmadmin> ')
	while not cmd == "quit":
		
		cmd=cmd.strip()
		if cmd == "usage": 
			dataInstance.usage()


		if cmd == "quit":
			exitMessage()

		if not LDMcommands.isValidCmd(cmd):
			print(f"Invalid ldmadmin command: {cmd}\n")
			cmd = input('ldmadmin> ')
			continue

		# Here, cmd is a valid ldmadmin command:
		print(f"{cmd} ---> {LDMcommands.returnCmdCortege(cmd)}")

		# namespace = dataInstance.cliParserAddArguments(cmd)
		# #print(f"\n\tnamespace: {namespace}\n")

		# cliString = dataInstance.buildCLIcommand(cmd, namespace)
		# status = LDMcommands.execute(cliString)



		# last line:
		cmd = input('ldmadmin> ')


	exitMessage()

if __name__ == '__main__':

	main()


