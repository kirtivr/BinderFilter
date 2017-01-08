#!/usr/bin/python

# David Wu
# Command line BinderFilter
# 
# Set policy: block, modify, specify app and arbitrary strings
# Parse logging output: both existing Binder logs (pretty print) and IPC messages
# Set NFQUEUE handlers
#

# todo: make sure setting policy checks if binder-filter-block-messages = 1

import sys, getopt
from subprocess import call
import subprocess
import PrettyPrintBinder
import argparse
from argparse import RawTextHelpFormatter

binderFilterPolicyFile = "/data/local/tmp/bf.policy"
binderFilterContextValuesFile = "/sys/kernel/debug/binder_filter/context_values"
binderFilterEnablePrintBufferContents = "/sys/module/binder_filter/parameters/filter_print_buffer_contents"
binderFilterEnable = "/sys/module/binder_filter/parameters/filter_enable"
binderFilterBlockAndModifyMessages = "/sys/module/binder_filter/parameters/filter_block_messages"

BINDER_FILTER_DISABLE = 0
BINDER_FILTER_ENABLE = 1

BLOCK_ACTION = 1
UNBLOCK_ACTION = 2
MODIFY_ACTION = 3
UNMODIFY_ACTION = 4

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

CONTEXT_STATE_ON = 1
CONTEXT_STATE_OFF = 2
CONTEXT_STATE_UNKNOWN = 3

CONTEXT_TYPE_INT = 1
CONTEXT_TYPE_STRING = 2

debugLevels = """
[BINDER_DEBUG_USER_ERROR = 0]
[BINDER_DEBUG_FAILED_TRANSACTION = 1]
[BINDER_DEBUG_DEAD_TRANSACTION = 2]
[BINDER_DEBUG_OPEN_CLOSE = 3]
[BINDER_DEBUG_DEAD_BINDER = 4]
[BINDER_DEBUG_DEATH_NOTIFICATION = 5]
[BINDER_DEBUG_READ_WRITE = 6]     
[BINDER_DEBUG_USER_REFS = 7]
[BINDER_DEBUG_THREADS = 8]
[BINDER_DEBUG_TRANSACTION = 9]
[BINDER_DEBUG_TRANSACTION_COMPLETE = 10]
[BINDER_DEBUG_FREE_BUFFER = 11]
[BINDER_DEBUG_INTERNAL_REFS = 12]
[BINDER_DEBUG_BUFFER_ALLOC = 13]
[BINDER_DEBUG_PRIORITY_CAP = 14]
[BINDER_DEBUG_BUFFER_ALLOC_ASYNC = 15]
"""

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
		if int(items[3]) != CONTEXT_NONE:
			print "Context: " + getStringForContext(items[3])
			print "Context type: " + getStringForContextType(items[4])
			print "Context value: " + getStringForContextValue(items[5])
			if int(items[2]) == MODIFY_ACTION:
				print "Modify data: " + items[6]
		if int(items[2]) == MODIFY_ACTION:
			print "Modify data: " + items[4]

def getStringForAction(action):
	if int(action) == BLOCK_ACTION:
		return "Block"
	elif int(action) == UNBLOCK_ACTION:
		return "Unblock"
	elif int(action) == MODIFY_ACTION:
		return "Modify"
	elif int(action) == UNMODIFY_ACTION:
		return "Unmodify"
	else:
		return "Unsupported action"

def getStringForContext(context):
	if int(context) == CONTEXT_NONE:
		return "None"
	elif int(context) == CONTEXT_WIFI_STATE:
		return "Wifi state"
	elif int(context) == CONTEXT_WIFI_SSID:
		return "Wifi SSID"
	elif int(context) == CONTEXT_WIFI_NEARBY:
		return "Wifi nearby"
	elif int(context) == CONTEXT_BT_STATE:
		return "Bluetooth state"
	elif int(context) == CONTEXT_BT_CONNECTED_DEVICE:
		return "Bluetooth conencted device"
	elif int(context) == CONTEXT_BT_NEARBY_DEVICE:
		return "Bluetooth nearby device"
	elif int(context) == CONTEXT_LOCATION:
		return "Location"
	elif int(context) == CONTEXT_APP_INSTALLED:
		return "Application installed"
	elif int(context) == CONTEXT_APP_RUNNING:
		return "Application running"
	elif int(context) == CONTEXT_DATE_DAY:
		return "Date"
	else:
		return "Unsupported context"

def getStringForContextType(contextType):
	if int(contextType) == CONTEXT_TYPE_INT:
		return "Integer"
	elif int(contextType) == CONTEXT_TYPE_STRING:
		return "String"
	else:
		return "Unsupported context type"

def getStringForContextValue(contextValue):
	if int(contextValue) == CONTEXT_STATE_ON:
		return "On"
	elif int(contextValue) == CONTEXT_STATE_OFF:
		return "Off"
	elif int(contextValue) == CONTEXT_STATE_UNKNOWN:
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
	package = output.split('\n')[1]
	package = str.split(package)[1].replace('}','')
	return package

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

def main(argv):

	parser = argparse.ArgumentParser(description='Android Binder IPC hook and parser.')
	
	parser.add_argument("-p", "--print-policy", action="store_true", dest="argPrintPolicy",
		 default="False", help="Print current BinderFilter policy")

	parser.add_argument("-f", "--print-policy-formatted", action="store_true", dest="argPrintPolicyFormatted",
		 default="False", help="Print current BinderFilter policy nicely")

	parser.add_argument("-c", "--print-system-context", action="store_true", dest="argPrintContext",
		 default="False", help="Print current system context values")

	parser.add_argument("-a", "--disable-ipc-buffers", action="store_true", dest="argDisablePrintBuffer",
		 default="False", help="Disable BinderFilter parsing and printing of IPC buffer contents")

	parser.add_argument("-b", "--enable-ipc-buffers", action="store_true", dest="argEnablePrintBuffer",
		 default="False", help="Enable BinderFilter parsing and printing of IPC buffer contents. This is computationally expensive.")

	parser.add_argument("-o", "--print-ipc-buffers-once", action="store_true", dest="argPrintBuffersOnce",
		 default="False", help="Print Android IPC buffer contents")

	parser.add_argument("-i", "--print-ipc-buffers-forever", action="store_true", dest="argPrintBuffersForever",
		 default="False", help="Print Android IPC buffer contents forever")

	parser.add_argument("-d", '--print-logs-once', action="store", dest="levelOnce", 
		nargs="*", help="Print Binder system logs. Optional argument for the specific level of Kernel debug level. " + debugLevels)
	
	parser.add_argument("-e", '--print-logs-forever', action="store", dest="levelForever", 
		nargs="*", help="See --print-logs-once")

	parser.add_argument("-y", "--disable-binder-filter", action="store_true", dest="argDisableFilter",
		 default="False", help="Disable BinderFilter completely")

	parser.add_argument("-z", "--enable-binder-filter", action="store_true", dest="argEnableFilter",
		 default="True", help="Enable BinderFilter (This is required for any functionality")

	parser.add_argument("-w", "--disable-block-and-modify-messages", action="store_true", dest="argDisableBlock",
		 default="False", help="Disable BinderFilter from blocking and modifying IPC messages. BinderFilter can still parse and log IPC messages if --enable-ipc-buffers is set")

	parser.add_argument("-x", "--enable-block-and-modify-messages", action="store_true", dest="argEnableBlock",
		 default="True", help="Enable BinderFilter to block and modify IPC messages")

	results = parser.parse_args()
	opts = results._get_kwargs()

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
							parser.print_help()
							sys.exit()
						debugArray.append(int(level))

				printBinderLog(debugMask, debugArray, opt[0] == "levelForever")


if __name__ == "__main__":
	main(sys.argv[1:])