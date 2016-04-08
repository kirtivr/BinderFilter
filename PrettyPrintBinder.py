#!/usr/bin/python
# David Wu
# todo: add filters
# line numbers from http://androidxref.com/kernel_3.4/xref/drivers/staging/android/binder.c


'''
-k see kernel debug messages (i.e. binder printks)
followed by the number for types of debug messages to see
i.e. -k 1 9 would show BINDER_DEBUG_USER_ERROR and BINDER_DEBUG_TRANSACTION  
 a see all BINDER_DEBUG messages
 0 see BINDER_DEBUG_USER_ERROR
 1 see BINDER_DEBUG_FAILED_TRANSACTION 
 2 see BINDER_DEBUG_DEAD_TRANSACTION 
 3 see BINDER_DEBUG_OPEN_CLOSE 
 4 see BINDER_DEBUG_DEAD_BINDER     
 5 see BINDER_DEBUG_DEATH_NOTIFICATION
 6 see BINDER_DEBUG_READ_WRITE
 7 see BINDER_DEBUG_USER_REFS
 8 see BINDER_DEBUG_THREADS
 9 see BINDER_DEBUG_TRANSACTION
 10 see BINDER_DEBUG_TRANSACTION_COMPLETE
 11 see BINDER_DEBUG_FREE_BUFFER
 12 see BINDER_DEBUG_INTERNAL_REFS
 13 see BINDER_DEBUG_BUFFER_ALLOC
 14 see BINDER_DEBUG_PRIORITY_CAP
 15 see BINDER_DEBUG_BUFFER_ALLOC_ASYNC
'''

import os, sys, getopt, time
import subprocess
from subprocess import Popen, PIPE
import datetime
from datetime import timedelta

# set at the beginning of running, used to print human readable timestamps
startingSystemTime = ""
startingTimestamp = ""

#[ 2159.006957] binder: 188:276 BR_TRANSACTION 325830 14054:14054, cmd -2144833022size 100-0 ptr b6982028-b698208c
def translateLog(line):
	if line == "":
		return

	timestamp = line[1:line.find(']')]
	timestamp = timestamp.strip()	# handle 1-4 digit timestamps

	line = line[line.find(']')+2:]	# strip the timestamp

	if "binder_open" in line:
		translateBinderOpen(line, timestamp)
	elif "binder_mmap" in line:
		print "binder_mmap"
	else:
		print "not found"


# binder.c#2937
# [122214.186086] binder_open: 18298:18298
# binder_debug(BINDER_DEBUG_OPEN_CLOSE, "binder_open: %d:%d\n",
# 					current->group_leader->pid, current->pid);
def translateBinderOpen(line, timestamp):
	c1 = line.find(':')+2
	c2 = line.find(':', c1)
	pid1 = line[c1 : c2]
	pid2 = line[c2+1:]
	name = getProcessNameFor(pid2)
	htime = translateTimestamp(timestamp)

	print("[%s] binder_open: group leader pid %s, current pid %s (%s)" % (htime, pid1, pid2, name))

# binder.c#2848
# [122214.186238] binder_mmap: 18298 ae942000-aea40000 (1016 K) vma 200071 pagep 79f
# binder_debug(BINDER_DEBUG_OPEN_CLOSE,
# 	     "binder_mmap: %d %lx-%lx (%ld K) vma %lx pagep %lx\n",
# 	     proc->pid, vma->vm_start, vma->vm_end,
# 	     (vma->vm_end - vma->vm_start) / SZ_1K, vma->vm_flags,
# 	     (unsigned long)pgprot_val(vma->vm_page_prot));


# binder.c#2992	
# [122214.199605] binder_flush: 18298 woke 2 threads
# binder_debug(BINDER_DEBUG_OPEN_CLOSE,
#     "binder_flush: %d woke %d threads\n", proc->pid, wake_count);

# binder.c#3120
# [122214.426229] binder_release: 18298 threads 3, nodes 1 (ref 0), refs 2, active transactions 0, buffers 0, pages 1	
# binder_debug(BINDER_DEBUG_OPEN_CLOSE,
# 		     "binder_release: %d threads %d, nodes %d (ref %d), "
# 		     "refs %d, active transactions %d, buffers %d, pages %d\n",
# 		     proc->pid, threads, nodes, incoming_refs, outgoing_refs,
# 		     active_transactions, buffers, page_count);

# binder.c#2812
# binder_debug(BINDER_DEBUG_OPEN_CLOSE,
#      "binder: %d open vm area %lx-%lx (%ld K) vma %lx pagep %lx\n",
#      proc->pid, vma->vm_start, vma->vm_end,
#      (vma->vm_end - vma->vm_start) / SZ_1K, vma->vm_flags,
#      (unsigned long)pgprot_val(vma->vm_page_prot));

# binder.c#2822
# [147595.627917] binder: 12098 close vm area ae942000-aea40000 (1016 K) vma 2220051 pagep 79f
# binder_debug(BINDER_DEBUG_OPEN_CLOSE,
#      "binder: %d close vm area %lx-%lx (%ld K) vma %lx pagep %lx\n",
#      proc->pid, vma->vm_start, vma->vm_end,
#      (vma->vm_end - vma->vm_start) / SZ_1K, vma->vm_flags,
#      (unsigned long)pgprot_val(vma->vm_page_prot));

# binder.c#2496
# [ 2159.006957] binder: 188:276 BR_TRANSACTION 325830 14054:14054, cmd -2144833022size 100-0 ptr b6982028-b698208c
# binder_debug(BINDER_DEBUG_TRANSACTION,
# 			     "binder: %d:%d %s %d %d:%d, cmd %d"
# 			     "size %zd-%zd ptr %p-%p\n",
# 			     proc->pid, thread->pid,
# 			     (cmd == BR_TRANSACTION) ? "BR_TRANSACTION" :
# 			     "BR_REPLY",
# 			     t->debug_id, t->from ? t->from->proc->pid : 0,
# 			     t->from ? t->from->pid : 0, cmd,
# 			     t->buffer->data_size, t->buffer->offsets_size,
# 			     tr.data.ptr.buffer, tr.data.ptr.offsets);


# [122214.186086]   [seconds.milliseconds]
# time printed will be based on local system time (i.e. computer time, not android time)
def translateTimestamp(ts):
	secondsPassed = float(ts) - float(startingTimestamp)
	hts = (startingSystemTime + timedelta(seconds=secondsPassed)).time()
	#return str(hts)[:str(hts).find('.')+3]
	return hts

def getProcessNameFor(pid):
	val = subprocess.check_output(["adb", "shell", "ps", "-p", str(pid)])
	val = val[val.find('\n')+1:]
	val = val[val.rfind(' ')+1:]
	val = val.rstrip()
	if val == "":
		return "process exited"
	return val

# might be able to do some of the shell commands in python equivalents to speed it up
def getDmesg():
	p1 = Popen(["adb", "shell", "dmesg"], stdout=PIPE)
	p2 = Popen(["grep", "binder"], stdin=p1.stdout, stdout=PIPE)
	p3 = Popen(["tail", "-r"], stdin=p2.stdout, stdout=PIPE)
	return p3.communicate()[0]

def getTimeStampFromLine(l):
	a = l.find('[')
	b = l.find(']', a)
	return l[a+1:b]

def systemChecks():
	# check for kernel version (and also adb shell access)
	val=""
	try: 
		val = subprocess.check_output(["adb", "shell", "cat", "/proc/version"])
	except subprocess.CalledProcessError:
		sys.exit()

	version = val[len("Linux version "):val.find('-')]
	if int(version[0]) < 3 or (int(version[2:][0:version[2:].find('.')]) < 4):
		print "Linux kernel version", version, "is older than 3.4.0, logging may not be accurate!!"

	try: 
		val = subprocess.check_output(["adb", "shell", "su", "-c", "ls", "/data"])
	except subprocess.CalledProcessError:
		sys.exit()

	if "su: not found" in val:
		print "No root access!"
		sys.exit()

def generateDebugMask(l):
	debugMask = 0
	for i in l:
		debugMask += 1 << i

	return debugMask

def usage():
	print 'usage: PrettyPrintBinder.py -k <levels>'

def main(argv):
	debugArray = []
	debugMask = 0
	try:
		opts, args = getopt.getopt(argv,"hk:")
	except getopt.GetoptError:
		usage()
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			usage()
			sys.exit()
  		elif opt in ("-k"):	
  			if arg == 'a':
  				debugMask = 1111111111111111
  				break
  			if int(arg) < 0 or int(arg) > 15:
  				print "bad argument to k!"
  				sys.exit()

			debugArray.append(int(arg))
		else:
			usage()
			sys.exit()

	if debugMask == 0:
		debugMask = generateDebugMask(debugArray)

	systemChecks()

	# set the kernel module parameter for binder_debug() statements
	cmd='adb shell \"su -c echo ' + str(debugMask) + ' \'> /sys/module/binder/parameters/debug_mask\'\"'
	subprocess.call(cmd, shell=True)

	p1 = Popen(["adb", "shell", "dmesg"], stdout=PIPE)
	p2 = Popen(["grep", "binder"], stdin=p1.stdout, stdout=PIPE)
	p3 = Popen(["tail", "-r", "-n", "1"], stdin=p2.stdout, stdout=PIPE)
	firstLine = p3.communicate()[0]
	firstTime = getTimeStampFromLine(firstLine)
	
	global startingSystemTime, startingTimestamp
	startingSystemTime = datetime.datetime.now()
	startingTimestamp = firstTime

	# read dmesg from the most recent line until last line printed
	while True:
		firstLoop = True
		nextTime = 0
		outputList = []
		for line in getDmesg().splitlines():
			currentTime = getTimeStampFromLine(line)

			if firstLoop == True:
				firstLoop = False
				nextTime = currentTime
				#print "set next time as", nextTime

			if currentTime <= firstTime:
				break

			outputList.insert(0, line)

		for o in outputList:
			print o
			translateLog(o)

		firstTime = nextTime


if __name__ == "__main__":
   	main(sys.argv[1:])





