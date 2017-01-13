#!/usr/bin/python

# David Wu
# Command line BinderFilter
# 
# Set policy: block, modify, specify app and arbitrary strings
# Parse logging output: both existing Binder logs (pretty print) and IPC messages
# Set NFQUEUE handlers
#

import sys, getopt
from subprocess import call
import subprocess
import PrettyPrintBinder
import argparse
from argparse import RawTextHelpFormatter
from enum import Enum
import struct

binderFilterPolicyFile = "/data/local/tmp/bf.policy"
binderFilterContextValuesFile = "/sys/kernel/debug/binder_filter/context_values"
binderFilterEnablePrintBufferContents = "/sys/module/binder_filter/parameters/filter_print_buffer_contents"
binderFilterEnable = "/sys/module/binder_filter/parameters/filter_enable"
binderFilterBlockAndModifyMessages = "/sys/module/binder_filter/parameters/filter_block_messages"

BINDER_FILTER_DISABLE = 0
BINDER_FILTER_ENABLE = 1

class Actions(Enum):
	BLOCK_ACTION = 1
	UNBLOCK_ACTION = 2
	MODIFY_ACTION = 3
	UNMODIFY_ACTION = 4

class Contexts(Enum):
	CONTEXT_NONE = 0
	CONTEXT_WIFI_STATE = 1
	CONTEXT_WIFI_SSID = 2
	CONTEXT_WIFI_NEARBY = 3
	CONTEXT_BT_STATE = 4
	CONTEXT_BT_CONNECTED_DEVICE = 5
	CONTEXT_BT_NEARBY_DEVICE = 6
	CONTEXT_LOCATION = 7
	CONTEXT_APP_INSTALLED = 8
	CONTEXT_APP_RUNNING = 9
	CONTEXT_DATE_DAY = 10

class ContextIntValues(Enum):
	CONTEXT_STATE_ON = 1
	CONTEXT_STATE_OFF = 2
	CONTEXT_STATE_UNKNOWN = 3

class ContextTypes(Enum):
	CONTEXT_TYPE_INT = 1
	CONTEXT_TYPE_STRING = 2

class BinderDebugLevels(Enum):
	BINDER_DEBUG_USER_ERROR = 0
	BINDER_DEBUG_FAILED_TRANSACTION = 1
	BINDER_DEBUG_DEAD_TRANSACTION = 2
	BINDER_DEBUG_OPEN_CLOSE = 3
	BINDER_DEBUG_DEAD_BINDER = 4
	BINDER_DEBUG_DEATH_NOTIFICATION = 5
	BINDER_DEBUG_READ_WRITE = 6
	BINDER_DEBUG_USER_REFS = 7
	BINDER_DEBUG_THREADS = 8
	BINDER_DEBUG_TRANSACTION = 9
	BINDER_DEBUG_TRANSACTION_COMPLETE = 10
	BINDER_DEBUG_FREE_BUFFER = 11
	BINDER_DEBUG_INTERNAL_REFS = 12
	BINDER_DEBUG_BUFFER_ALLOC = 13
	BINDER_DEBUG_PRIORITY_CAP = 14
	BINDER_DEBUG_BUFFER_ALLOC_ASYNC = 15

def printPolicy(format):
	output = subprocess.Popen(["adb", "shell", "su -c \'", "cat", binderFilterPolicyFile, "\'"], stdout=subprocess.PIPE).communicate()[0]

	if format is False:
		print output
		return

	printFormatPolicyFile(output)

# message:uid:action_code:context:(context_type:context_val:)(data:)
def printFormatPolicyFile(file):
	lines = file.splitlines()
	for line in lines:
		items = line.split(":")
		print
		print items[0]
		print "UID: " + items[1]
		print "Package: " + getPackageNameForUid(items[1])
		print "Action: " + getStringForAction(items[2])
		if int(items[3]) != Contexts.CONTEXT_NONE:
			print "Context: " + getStringForContext(items[3])
			print "Context type: " + getStringForContextType(items[4])
			print "Context value: " + getStringForContextValue(items[5])
			if int(items[2]) == Actions.MODIFY_ACTION:
				print "Modify data: " + items[6]
		if int(items[2]) == Actions.MODIFY_ACTION:
			print "Modify data: " + items[4]

def getStringForAction(action):
	if int(action) == Actions.BLOCK_ACTION:
		return "Block"
	elif int(action) == Actions.UNBLOCK_ACTION:
		return "Unblock"
	elif int(action) == Actions.MODIFY_ACTION:
		return "Modify"
	elif int(action) == Actions.UNMODIFY_ACTION:
		return "Unmodify"
	else:
		return "Unsupported action"

def getStringForContext(context):
	if int(context) == Contexts.CONTEXT_NONE:
		return "None"
	elif int(context) == Contexts.CONTEXT_WIFI_STATE:
		return "Wifi state"
	elif int(context) == Contexts.CONTEXT_WIFI_SSID:
		return "Wifi SSID"
	elif int(context) == Contexts.CONTEXT_WIFI_NEARBY:
		return "Wifi nearby"
	elif int(context) == Contexts.CONTEXT_BT_STATE:
		return "Bluetooth state"
	elif int(context) == Contexts.CONTEXT_BT_CONNECTED_DEVICE:
		return "Bluetooth conencted device"
	elif int(context) == Contexts.CONTEXT_BT_NEARBY_DEVICE:
		return "Bluetooth nearby device"
	elif int(context) == Contexts.CONTEXT_LOCATION:
		return "Location"
	elif int(context) == Contexts.CONTEXT_APP_INSTALLED:
		return "Application installed"
	elif int(context) == Contexts.CONTEXT_APP_RUNNING:
		return "Application running"
	elif int(context) == Contexts.CONTEXT_DATE_DAY:
		return "Date"
	else:
		return "Unsupported context"

def getStringForContextType(contextType):
	if int(contextType) == ContextTypes.CONTEXT_TYPE_INT:
		return "Integer"
	elif int(contextType) == ContextTypes.CONTEXT_TYPE_STRING:
		return "String"
	else:
		return "Unsupported context type"

def getStringForContextValue(contextValue):
	if int(contextValue) == ContextIntValues.CONTEXT_STATE_ON:
		return "On"
	elif int(contextValue) == ContextIntValues.CONTEXT_STATE_OFF:
		return "Off"
	elif int(contextValue) == ContextIntValues.CONTEXT_STATE_UNKNOWN:
		return "Unknown"
	else:
		return "Unsupported context value"

def printContextValues():
	cmd='adb shell \"su -c \'cat ' + binderFilterContextValuesFile + '\'\"'
	call(cmd, shell=True)

#adb shell "dumpsys package | grep -A1 'userId=10082'"
def getPackageNameForUid(uid):
	p1 = subprocess.Popen(["adb", "shell", "dumpsys", "package", "|" , "grep", "-A1", "\'userId=" + str(uid) + "\'"], stdout=subprocess.PIPE)
	output = p1.communicate()[0]

	if output.count('\n') < 2:
		return "Package not found for uid " + uid

	package = output.split('\n')[1]
	package = str.split(package)[1].replace('}','')
	return package

def getUidStringsForPackages(package):
	p1 = subprocess.Popen(["adb", "shell", "dumpsys", "package", "|" , "grep", "-A1", package, "|", "grep", "-B1" , "userId"], stdout=subprocess.PIPE)
	output = p1.communicate()[0]
	return output

def printPermissions():
	cmd='adb shell \"su -c \'pm list permissions\'\"'
	call(cmd, shell=True)
	cmd='cat permissions.txt'
	call(cmd, shell=True)

def printApplications():
	cmd='adb shell \"su -c \'pm list package\'\"'
	call(cmd, shell=True)

def printCommands():
	cmd='cat commandArgs.txt'
	call(cmd, shell=True)

def togglePrintBufferContents(action):
	cmd='adb shell \"su -c \'echo ' + str(action) + ' > ' + binderFilterEnablePrintBufferContents + '\'\"'
	call(cmd, shell=True)

def toggleFilterEnable(action):
	cmd='adb shell \"su -c \'echo ' + str(action) + ' > ' + binderFilterEnable + '\'\"'
	call(cmd, shell=True)

def toggleBlockAndModifyMessages(action):
	cmd='adb shell \"su -c \'echo ' + str(action) + ' > ' + binderFilterBlockAndModifyMessages + '\'\"'
	call(cmd, shell=True)

def checkIpcBuffersAndFilterEnabled():
	p1 = subprocess.Popen(["adb", "shell", "cat", binderFilterEnablePrintBufferContents], stdout=subprocess.PIPE)
	output = p1.communicate()[0]
	if int(output) != BINDER_FILTER_ENABLE:
		print "Please enable IPC buffers: ./binderfilter.py --enable-ipc-buffers"
		sys.exit()
	checkFilterEnabled()

def checkFilterEnabled():
	p2 = subprocess.Popen(["adb", "shell", "cat", binderFilterEnable], stdout=subprocess.PIPE)
	output = p2.communicate()[0]
	if int(output) != BINDER_FILTER_ENABLE:
		print "Please enable BinderFilter: ./binderfilter.py --enable-binder-filter"
		sys.exit()

def checkBlockingEnabled():
	p2 = subprocess.Popen(["adb", "shell", "cat", binderFilterBlockAndModifyMessages], stdout=subprocess.PIPE)
	output = p2.communicate()[0]
	if int(output) != BINDER_FILTER_ENABLE:
		print "Please enable BinderFilter blocking and modifying: ./binderfilter.py --enable-block-and-modify-messages"
		sys.exit()

def printIpcBuffersOnce():
	checkIpcBuffersAndFilterEnabled()
	cmd='adb shell dmesg | grep "BINDERFILTER"'
	call(cmd, shell=True)

def getDmesg():
	p1 = subprocess.Popen(["adb", "shell", "dmesg"], stdout=subprocess.PIPE)
	p2 = subprocess.Popen(["grep", "BINDERFILTER"], stdin=p1.stdout, stdout=subprocess.PIPE)
	return p2.communicate()[0]

# [20348.733001] BINDERFILTER: uid: 1000
def getTime(line):
	a = line.find('[')
	b = line.find(']', a)
	return line[a+1:b]

def printIpcBuffersForever():
	checkIpcBuffersAndFilterEnabled()

	mostRecentTime = 0
	while True:
		lines = getDmesg().splitlines()

		for line in getDmesg().splitlines():
			if (getTime(line) > mostRecentTime):
				print line

		mostRecentTime = getTime(lines[-1])

def printBinderLog(mask, array, forever):
	checkFilterEnabled()
	PrettyPrintBinder.PrettyPrint(mask, array, forever)

# byte[8] values of latitude,longitude separated by '.' in string form
# translated for binderfilter to use in the kernel
# 43.704979, -72.287458 becomes
# 243.174.122.192.60.218.69.64.79.62.61.182.101.18.82.192.
def getGpsStringForBinderFilter(latitude, longitude):
	bLat = bytearray(struct.pack("d", float(latitude)))
	bLong = bytearray(struct.pack("d", float(longitude)))

	combinedByteArrayString = ""

	for d in bLat:
		combinedByteArrayString += str(d) + '.'
	for d in bLong:
		combinedByteArrayString += str(d) + '.'

	print combinedByteArrayString


# message:uid:action_code:context:(context_type:context_val:)(data:)
def setPolicy(results, opts):
	message = results.message
	uid = results.uid
	action = results.action
	modifyData = results.modifyData
	context = results.context
	contextType = results.contextType
	contextValue = results.contextValue

	# print
	# print("message: ", message)
	# print("uid: ", uid)
	# print("action: ", action)
	# print("modifyData: ", modifyData)
	# print("context: ", context)
	# print("contextType: ", contextType)
	# print("contextValue: ", contextValue)

	validate(message, uid, action, modifyData, context, contextType, contextValue)

	filterline = str(message)+':'+str(uid)+':'+str(action)+':'+str(context)+':'
	if int(context) != Contexts.CONTEXT_NONE.value:
		filterline += str(contextType)+':'+str(contextValue)+':'
	if int(action) == Actions.MODIFY_ACTION.value:
		filterline += str(modifyData)+':'

	checkAndCreateMiddleware()

	# call middleware with filterline data
	# adb shell su -c './data/local/tmp/middleware -a 2 -u 10082 -m test -c 2 -t 2 -v TheKrustyKrab'
	cmd = 'adb shell \"su -c \'/data/local/tmp/middleware -a ' + str(action) + ' -u ' + str(uid) + ' -m ' + str(message) + ' -c ' + str(context)
	if modifyData is not None:
		cmd += ' -d ' + str(modifyData)
	if int(context) != Contexts.CONTEXT_NONE.value:
		cmd += ' -t ' + str(contextType)
		cmd += ' -v ' + str(contextValue)
	cmd += '\'\"'

	# print cmd
	print filterline

	call(cmd, shell=True)
	verifyFilterApplied(filterline, int(action))

def checkAndCreateMiddleware():
	if checkMiddlewareDoesNotExist() is True:
		cmd='chmod +x ccAndMove.sh; ./ccAndMove.sh'
		call(cmd, shell=True)

	if checkMiddlewareDoesNotExist() is True:
		print "Cannot compile and move Android middleware. Please see documentation/cross-compiling/cross_compiling_c_for_android.txt for cross compiling instructions."
		sys.exit()

def checkMiddlewareDoesNotExist():
	p1 = subprocess.Popen(["adb", "shell", "su", "-c", "\'if", "[", "!", "-f", "/data/local/tmp/middleware", "];", 
							"then", "echo", "dne;", "fi\'"], stdout=subprocess.PIPE)
	output = p1.communicate()[0]
	return "dne" in output

def verifyFilterApplied(filterline, action):
	output = subprocess.Popen(["adb", "shell", "su -c \'", "cat", binderFilterPolicyFile, "\'"], stdout=subprocess.PIPE).communicate()[0]
	if len(output) == 0:
		firstLine = ""
	else:
		firstLine = output.splitlines()[0]

	if action == Actions.UNBLOCK_ACTION.value or action == Actions.UNMODIFY_ACTION.value:
		if firstLine == filterline:
			print "Fatal error: Policy could not be successfully un-applied!"
			print "Policy remained: " + filterline
			sys.exit()
		return

	if firstLine != filterline:
		print "Fatal error: Policy could not be successfully applied!"
		print "Policy expected: " + filterline
		print "\tbut was: " + firstLine
		sys.exit()

def validate(message, uid, action, modifyData, context, contextType, contextValue):
	if message is None or uid is None or action is None:
		print "--message-contains, --uid, and --action must be set."
		sys.exit()

	if context is not None and int(context) != Contexts.CONTEXT_NONE.value and (contextType is None or contextValue is None):
		print "--context-type and --context-value must be set if --context is not CONTEXT_NONE"
		sys.exit()

	if int(action) == Actions.MODIFY_ACTION.value and modifyData is None:
		print "--modify-data must be set if action is modify."
		sys.exit()

	if len(str(message)) >= 1024:
		print "strlen(message) should not exceed 1024."
		sys.exit()

	if "Package not found" in getPackageNameForUid(uid):
		print getPackageNameForUid(uid)
		sys.exit()

	if int(action) not in [e.value for e in Actions]:
		print "Action value not found. Use the --print-command-args flag to see possible values."
		sys.exit()

	if len(str(modifyData)) >= 1024:
		print "strlen(modifyData) should not exceed 1024."
		sys.exit()

	if int(context) not in [e.value for e in Contexts]:
		print "Context not found. Use the --print-command-args flag to see possible values."
		sys.exit()

	if int(context) != Contexts.CONTEXT_NONE.value:
		if int(contextType) not in [e.value for e in ContextTypes]:
			print "Context type not found. Use the --print-command-args flag to see possible values."
			sys.exit()

		if int(contextType) == ContextTypes.CONTEXT_TYPE_INT.value:
			try:
				badContextValue = False
				value = int(contextValue)
			except ValueError:
			    badContextValue = True
			if badContextValue or (int(contextValue) not in [e.value for e in ContextIntValues]):
				print "Context int value not found. Use the --print-command-args flag to see possible values."
				sys.exit()

		if len(str(contextValue)) >= 1024:
			print "strlen(contextValue) should not exceed 1024."
			sys.exit()

	checkFilterEnabled()
	checkBlockingEnabled()

def main(argv):

	parser = argparse.ArgumentParser(description='Android Binder IPC hook and parser.')

	parser.add_argument("-s", "--set-policy", action="store_true", dest="argSetPolicy",
		 default="False", help="Set BinderFilter policy. Required: --message-contains, --uid, --action.")

	parser.add_argument("-m", "--message-contains", action="store", dest="message",
		 help="Set BinderFilter policy: Message to filter on. I.e. \"android.permission.CAMERA\". To modify arbitrary strings, prepend this message with binderfilter.arbitrary.x where x is the string. See the github docs for more information")

	parser.add_argument("-u", "--uid", action="store", dest="uid",
		 help="Set BinderFilter policy: Uid to filter on. I.e. \"10082\". Find corresponding Uid for packagename with --get-uid-for [name]")
	
	parser.add_argument("-a", "--action", action="store", dest="action",
		 help="Set BinderFilter policy: Action to perform. 0: Block,1: Unblock, 2: Modify, 3: Unmodify")

	parser.add_argument("--modify-data", action="store", dest="modifyData",
		 help="Set BinderFilter policy: data to modify message with. Required if --action=3")

	parser.add_argument("--context", action="store", dest="context", default=0,
		 help="Set BinderFilter policy: context. Default to CONTEXT_NONE. Use the --print-command-args flag to see possible values.")

	parser.add_argument("--context-type", action="store", dest="contextType",
		 help="Set BinderFilter policy: context type. Required if --context is not CONTEXT_NONE. 1: integer, 2: string")

	parser.add_argument("--context-value", action="store", dest="contextValue",
		 help="Set BinderFilter policy: context value. Required if --context is not CONTEXT_NONE. If --context-type=1, use 1: ON, 2: OFF")

	parser.add_argument("-p", "--print-policy", action="store_true", dest="argPrintPolicy",
		 default="False", help="Print current BinderFilter policy")

	parser.add_argument("-f", "--print-policy-formatted", action="store_true", dest="argPrintPolicyFormatted",
		 default="False", help="Print current BinderFilter policy nicely")

	parser.add_argument("-c", "--print-system-context", action="store_true", dest="argPrintContext",
		 default="False", help="Print current system context values")

	parser.add_argument("-q", "--disable-ipc-buffers", action="store_true", dest="argDisablePrintBuffer",
		 default="False", help="Disable BinderFilter parsing and printing of IPC buffer contents")

	parser.add_argument("-b", "--enable-ipc-buffers", action="store_true", dest="argEnablePrintBuffer",
		 default="False", help="Enable BinderFilter parsing and printing of IPC buffer contents. This is computationally expensive.")

	parser.add_argument("-o", "--print-ipc-buffers-once", action="store_true", dest="argPrintBuffersOnce",
		 default="False", help="Print Android IPC buffer contents")

	parser.add_argument("-i", "--print-ipc-buffers-forever", action="store_true", dest="argPrintBuffersForever",
		 default="False", help="Print Android IPC buffer contents forever")

	parser.add_argument("-d", '--print-logs-once', action="store", dest="levelOnce", 
		nargs="*", help="Print Binder system logs. Optional argument for the specific level of Kernel debug level. Use the --print-command-args flag to see possible values.")
	
	parser.add_argument("-e", '--print-logs-forever', action="store", dest="levelForever", 
		nargs="*", help="See --print-logs-once")

	parser.add_argument("-g", "--get-uid-for", action="store", dest="packageName",
		help="Get UID for an application (string contains)")

	parser.add_argument("-j", "--print-permissions", action="store_true", dest="argPrintPermissoins",
		help="Print all Android system permissions from the packagemanager")

	parser.add_argument("-k", "--print-applications", action="store_true", dest="argPrintApplications",
		help="Print all Android applications installed")

	parser.add_argument("-w", "--disable-block-and-modify-messages", action="store_true", dest="argDisableBlock",
		 default="False", help="Disable BinderFilter from blocking and modifying IPC messages. BinderFilter can still parse and log IPC messages if --enable-ipc-buffers is set")

	parser.add_argument("-x", "--enable-block-and-modify-messages", action="store_true", dest="argEnableBlock",
		 default="True", help="Enable BinderFilter to block and modify IPC messages")

	parser.add_argument("-y", "--disable-binder-filter", action="store_true", dest="argDisableFilter",
		 default="False", help="Disable BinderFilter completely")

	parser.add_argument("-z", "--enable-binder-filter", action="store_true", dest="argEnableFilter",
		 default="True", help="Enable BinderFilter (This is required for any functionality")

	parser.add_argument("--get-gps-bytes", action="store_true", dest="argGetGpsBytes",
		 default="False", help="Get BinderFilter translations of latitude, longitude coordinates. Use with --latitude [LAT] --longitude [LONG]")

	parser.add_argument("--latitude", action="store", dest="latitude", help="Latitude. I.e. 43.704979")

	parser.add_argument("--longitude", action="store", dest="longitude", help="Longitude. I.e. -72.287458")

	parser.add_argument("--print-command-args", action="store_true", dest="argPrintCommands",
		 default="True", help="Print command argument values for --context and --print-logs-once.")

	results = parser.parse_args()
	opts = results._get_kwargs()

	if results.argSetPolicy is True:
		setPolicy(results, opts)
	if results.argPrintPolicy is True:
		printPolicy(False)
	if results.argPrintPolicyFormatted is True:
		printPolicy(True)
	if results.argPrintContext is True:
		printContextValues()
	if results.argDisablePrintBuffer is True:
		togglePrintBufferContents(BINDER_FILTER_DISABLE)
	if results.argEnablePrintBuffer is True:
		togglePrintBufferContents(BINDER_FILTER_ENABLE)
	if results.argPrintBuffersOnce is True:
		printIpcBuffersOnce()
	if results.argPrintBuffersForever is True:
		printIpcBuffersForever() 
	if results.argDisableFilter is True:
		toggleFilterEnable(BINDER_FILTER_DISABLE)
	if results.argEnableFilter is True:
		toggleFilterEnable(BINDER_FILTER_ENABLE)
	if results.argDisableBlock is True:
		toggleBlockAndModifyMessages(BINDER_FILTER_DISABLE)
	if results.argEnableBlock is True:
		toggleBlockAndModifyMessages(BINDER_FILTER_ENABLE)
	if results.argPrintPermissoins is True:
		printPermissions()
	if results.argPrintApplications is True:
		printApplications()
	if results.argGetGpsBytes is True:
		getGpsStringForBinderFilter(results.latitude, results.longitude)
	if results.argPrintCommands is True:
		printCommands()

	debugArray = []
	for opt in opts:
		if opt[0] == "levelOnce" or opt[0] == "levelForever":
			if opt[1] is not None: 		# None means the flag was not set
				if not opt[1]:			# not means args to --print-logs-once or --print-logs-forever were empty
					debugMask = 1111111111111111
				else:
					debugMask = 0
					for level in opt[1]:
						if int(level) < 0 or int(level) > 15:
							print "Bad debug level argument!"
							sys.exit()
						debugArray.append(int(level))

				printBinderLog(debugMask, debugArray, opt[0] == "levelForever")
		elif opt[0] == "packageName" and opt[1] is not None:
			print getUidStringsForPackages(opt[1])


if __name__ == "__main__":
	main(sys.argv[1:])