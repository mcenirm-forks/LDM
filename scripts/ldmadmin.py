#!/usr/bin/env python3

###############################################################################
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

import parseCLI 		as parseCli
import parseRegistry 	as parseReg
import environHandler	as envHdler

EXIT_MESSAGE='\n\tThank you for using ldmadmin...\n\n'


def bye(signal_received, frame):
	# Handle any cleanup here
	exitMessage()


def exitMessage():
	print(f"{EXIT_MESSAGE}")
	exit(0)


class LDMCommandsHandler:
	def __init__(self, cmdsDico):
		self.cmdsDico	= cmdsDico
		self.ldmShortCmdsList	= []
		for cmd, optionList in cmdsDico.items():
			self.ldmShortCmdsList.append(cmd)
	        
	def complete(self,userInput,state):
		results =  [cmd + " " for cmd in self.ldmShortCmdsList if cmd.startswith(userInput)] + [None]
		return results[state]

	def isValidCmd(self, cmd):		
		return cmd in self.ldmShortCmdsList

	def returnCmdCortege(self, cmd):
		return self.cmdsDico[cmd][0]

	def displayRegistryAndEnv(self, registryEntries, envVariables):
		print(f"\n\t====> Registry XML: \n {registryEntries} \n")
		print(f"\n\t====> Environment variables: \n {envVariables} \n")


	def execute(self, cmdToExecute, toLockOrNot, evnt):
		status = 0
		
		if toLockOrNot == True:
			if evnt.getLock() == -1:
				print(f"Could not get lock for '{cmdToExecute}' to execute properly!")
				status = -1
				return status

			print(f"\n\tExecuting in Locked Mode : {cmdToExecute}\n")
			evnt.releaseLock()

		else:
			
			print(f"\n\tExecuting in NON Locked Mode : {cmdToExecute}\n")
			status = os.system(cmdToExecute)

		return status


def main():
	signal(SIGINT, bye)
	system('clear')
	debug = False

	registryEntries = parseReg.RegistryParser().getRegistryEntries()
	evnt = envHdler.LDMenvironmentHandler()


	# tab completion:
	readline.parse_and_bind("tab: complete")
	cliInst 		= parseCli.CLIParser()				# instance of CLIParser
	cmdsDico 		= cliInst.getFullCommandsDict()
	LDMcommands 	= LDMCommandsHandler( cmdsDico )	# instance of 'this'
	

	checkTime(cmdsDico)

	exit(0)

	if debug:
		LDMcommands.displayRegistryAndEnv(registryEntries, evnt.getEnvVarsDict())

	readline.set_completer(LDMcommands.complete)



	nbArguments=len(sys.argv)
	if nbArguments == 1 or \
		nbArguments == 2 and (sys.argv[1] == "-h" or sys.argv[1] == "--help"):

# Interactive mode
		cliInst.usage()
		print(f"\n\tInteractive mode (type 'quit' to exit). Not implemented yet.\n")
	

	else:


# Non-interactive mode (CLI mode)
		cmd=sys.argv[1]
		lockOrNotFlag 	= cliInst.isLockingRequired(cmd)
		
		if not LDMcommands.isValidCmd(cmd):
			print(f"\n\tInvalid ldmadmin command: {cmd}\n")
			sleep(3)
			cliInst.usage()
			exitMessage()

		# Here, cmd is a valid ldmadmin command:
		if cmd == "usage": 
			cliInst.usage()

		
		# if  nbArguments == 2: # command w/o options
		# 	status 			= LDMcommands.execute(cmd, lockOrNotFlag, evnt)
		# else:	
		cliDico 		= cliInst.cliParserAddArguments(cmd)
		print(f"\n\nCLI dict: {cliDico}\n")

		cliString 		= cliInst.buildCLIcommand(cmd, cliDico)
		status 			= LDMcommands.execute(cliString, lockOrNotFlag, evnt)





		# last line:
		exitMessage()

# Interactive mode
	if None:
		cmd = input('ldmadmin> ')
		while not cmd == "quit":
			
			cmd=cmd.strip()
			if cmd == "usage": 
				cliInst.usage()


			if cmd == "quit":
				exitMessage()

			if not LDMcommands.isValidCmd(cmd):
				print(f"Invalid ldmadmin command: {cmd}\n")
				cmd = input('ldmadmin> ')
				continue

			# Here, cmd is a valid ldmadmin command:
			print(f"{cmd} ---> {LDMcommands.returnCmdCortege(cmd)}")

			# namespace = cliInst.cliParserAddArguments(cmd)
			# #print(f"\n\tnamespace: {namespace}\n")

			# cliString = cliInst.buildCLIcommand(cmd, namespace)
			# status = LDMcommands.execute(cmd, cliString, evnt)



			# last line:
			cmd = input('ldmadmin> ')


	exitMessage()

if __name__ == '__main__':

	main()


