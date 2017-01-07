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

binderFilterPolicyFile = "/data/local/tmp/bf.policy"
binderFilterContextValuesFile = "/sys/kernel/debug/binder_filter/context_values"
binderFilterEnablePrintBufferContents = "/sys/module/binder_filter/parameters/filter_print_buffer_contents"

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

def printHelp():
	print './binderfilter.py -p'
	sys.exit()

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

def printIpcBuffersOnce():
	p1 = subprocess.Popen(["adb", "shell", "cat", binderFilterEnablePrintBufferContents], stdout=subprocess.PIPE)
	output = p1.communicate()[0]
	if int(output) == BINDER_FILTER_DISABLE:
		print "Please enable IPC buffers: ./binderfilter.py --enable-ipc-buffers"
		sys.exit()

	cmd='adb shell dmesg | grep "BINDERFILTER"'
	call(cmd, shell=True)

# def getDmesg():
# 	p1 = subprocess.Popen(["adb", "shell", "dmesg"], stdout=subprocess.PIPE)
# 	p2 = subprocess.Popen(["grep", "BINDERFILTER"], stdin=p1.stdout, stdout=subprocess.PIPE)
# 	p3 = subprocess.Popen(["tail", "-r"], stdin=p2.stdout, stdout=subprocess.PIPE)
# 	return p3.communicate()[0]

def printIpcBuffersForever():
	p1 = subprocess.Popen(["adb", "shell", "cat", binderFilterEnablePrintBufferContents], stdout=subprocess.PIPE)
	output = p1.communicate()[0]
	if int(output) == BINDER_FILTER_DISABLE:
		print "Please enable IPC buffers: ./binderfilter.py --enable-ipc-buffers"
		sys.exit()

	# while True:
	# 	firstLoop = True
	# 	nextTime = 0
	# 	outputList = []
	# 	for line in getDmesg().splitlines():
	# 		currentTime = getTimeStampFromLine(line)

	# 		if firstLoop == True:
	# 			firstLoop = False
	# 			nextTime = currentTime

	# 		if currentTime <= firstTime:
	# 			break

	# 		outputList.insert(0, line)

	# 	for o in outputList:
	# 		print o

	# 	firstTime = nextTime

def main(argv):
	inputfile = ''
	outputfile = ''
	try:
		opts, args = getopt.getopt(argv,"hpfcaboi",["print-policy", "print-policy-formatted", "print-system-context", "print-log",
			"disable-ipc-buffers", "enable-ipc-buffers", "print-ipc-buffers-once", "print-ipc-buffers-forever"])
	except getopt.GetoptError:
		printHelp()
	for opt, arg in opts:
		if opt == '-h':
			printHelp()
		elif opt in ("-p", "--print-policy"):
			printPolicy(False)
		elif opt in ("-f", "--print-policy-formatted"):
			printPolicy(True)
		elif opt in ("-c", "--print-system-context"):
			printContextValues()
		elif opt in ("-a", "--disable-ipc-buffers"):
			togglePrintBufferContents(BINDER_FILTER_DISABLE)
		elif opt in ("-b", "--enable-ipc-buffers"):
			togglePrintBufferContents(BINDER_FILTER_ENABLE)
		elif opt in ("-o", "--print-ipc-buffers-once"):
			printIpcBuffersOnce()
		elif opt in ("-i", "--print-ipc-buffers-forever"):
			printIpcBuffersForever() 

if __name__ == "__main__":
	main(sys.argv[1:])