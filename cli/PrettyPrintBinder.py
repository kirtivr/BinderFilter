#!/usr/bin/python
# David Wu
# todo: add filters, 
# 		change for different kernel versions (i.e. 3.18 BR_TRANSACTION logging)
# 		
# line numbers from http://androidxref.com/kernel_3.4/xref/drivers/staging/android/binder.c


'''
-d see kernel debug messages (i.e. binder printks)
followed by the number for types of debug messages to see
i.e. -d1 -d9 would show BINDER_DEBUG_USER_ERROR and BINDER_DEBUG_TRANSACTION  
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
def translateLog(line,makeDict):
        '''

        Wireshark logging and graphviz visualization is currently enabled
        for BR_TRANSACTION, BR_REPLY, BC_TRANSACTION & BC_REPLY.

        '''

        if line == "":
		return ("discard","empty")
        
	timestamp = line[1:line.find(']')]
	timestamp = timestamp.strip()	# handle 1-4 digit timestamps
	timestamp = translateTimestamp(timestamp)
	line = line[line.find(']')+2:]	# strip the timestamp
        #print line
        
        # BINDER_DEBUG_OPEN_CLOSE
	if "binder_open" in line:
		return ("open",translateBinderOpen(line, timestamp, False))
	elif "binder_mmap" in line:
		return ("mmap",translateBinderMmap(line, timestamp, False))
	elif "binder_flush" in line:
		return ("flush",translateBinderFlush(line, timestamp, False))
	elif "binder_release" in line and "active" in line:
		return ("release",translateBinderRelease(line, timestamp, False))
	elif "open vm area" in line:
		return ("openvm",translateBinderOpenVma(line, timestamp, False))
	elif "close vm area" in line:
		return ("closevm",translateBinderCloseVma(line, timestamp, False))

	# BINDER_DEBUG_TRANSACTION
	elif "BR_TRANSACTION" in line and "cmd" in line:
		return ("BR_TRANSACTION",translateBinderReturn(line, timestamp, makeDict))
	elif "BR_REPLY" in line:
		return ("BR_REPLY",translateBinderReturn(line, timestamp, makeDict))
	elif "BC_TRANSACTION" in line:
		return ("BC_TRANSACTION",translateBinderCommandTransaction(line, timestamp, makeDict))
	elif "BC_REPLY" in line:
		return ("BC_REPLY",translateBinderCommandReply(line, timestamp, makeDict))
	elif "buffer release" in line:
		return ("BUFFER_RELEASE",translateBinderBufferRelease(line, timestamp, False))

	# BINDER_DEBUG_READ_WRITE
	elif "write" in line:
		return ("write",traslateBinderWrite(line, timestamp, False))
	elif "wrote" in line:
		return ("wrote",translateBinderWrote(line, timestamp, False))
	else:
		return ("discard","not found")


# binder.c#2937
# binder_open: 18298:18298
# binder_debug(BINDER_DEBUG_OPEN_CLOSE, "binder_open: %d:%d\n",
# 					current->group_leader->pid, current->pid);
def translateBinderOpen(line, timestamp, makeDict):
	c1 = line.find(':')+2
	c2 = line.find(':', c1)
	pid1 = line[c1 : c2]
	pid2 = line[c2+1:]
	name = getProcessNameFor(pid2)
        
        if makeDict:
                binderDict = {}
                binderDict.timestamp = timestamp
                binderDict.pidfrom = pid1
                binderDict.procfrom = getProcessNameFor(pid1)
                binderDict.pidto = pid2
                binderDict.procto = getProcessNameFor(pid2)

        print("[%s] binder_open: group leader pid %s, current pid %s (%s)" % (timestamp, pid1, pid2, name))

# binder.c#2848
# binder_mmap: 18298 ae942000-aea40000 (1016 K) vma 200071 pagep 79f
# binder_debug(BINDER_DEBUG_OPEN_CLOSE,
# 	     "binder_mmap: %d %lx-%lx (%ld K) vma %lx pagep %lx\n",
# 	     proc->pid, vma->vm_start, vma->vm_end,
# 	     (vma->vm_end - vma->vm_start) / SZ_1K, vma->vm_flags,
# 	     (unsigned long)pgprot_val(vma->vm_page_prot));
def translateBinderMmap(line, timestamp, makeDict):
	splitLine = line.split(' ')
	pid = splitLine[1]
	vma = splitLine[2]
	vmaStart = vma[:vma.find('-')]
	vmaEnd = vma[vma.find('-')+1:]
	size = splitLine[3][1:]
	flags = splitLine[6]
	prot = splitLine[8]
	name = getProcessNameFor(pid)

        if makeDict:
                binderDict = {}
                binderDict.op = "binder_mmap"
                binderDict.pid = pid
                binderDict.proc = getProcessNameFor(pid)
                binderDict.vma = vma
                binderDict.vmaStart = vmaStart
                binderDict.vmaEnd = vmaEnd
                binderDict.size = size
                binderDict.flags = flags
                binderDict.prot = prot
                binderDict.name = name
                return binderDict
        
	return ("[%s] binder_mmap: pid %s (%s) mapped addr %s-%s, size %s, flags %s, prot %s" % 
		  (timestamp, pid, name, vmaStart, vmaEnd, size, flags, prot))

# binder.c#2992	
# binder_flush: 18298 woke 2 threads
# binder_debug(BINDER_DEBUG_OPEN_CLOSE,
#     "binder_flush: %d woke %d threads\n", proc->pid, wake_count);
def translateBinderFlush(line, timestamp, makeDict):
	splitLine = line.split(' ')
	pid = splitLine[1]
	num = splitLine[3]

        if makeDict:
                binderDict = {}
                binderDict.op = "binder_flush"
                binderDict.pid = pid
                binderDict.proc = getProcessNameFor(pid)
                binderDict.num = num
                return binderDict
        
	return ("[%s] binder_flush: pid %s (%s) woke %s threads" % (timestamp, pid, getProcessNameFor(pid), num))

# binder.c#3120
# binder_release: 18298 threads 3, nodes 1 (ref 0), refs 2, active transactions 0, buffers 0, pages 1	
# binder_debug(BINDER_DEBUG_OPEN_CLOSE,
# 		     "binder_release: %d threads %d, nodes %d (ref %d), "
# 		     "refs %d, active transactions %d, buffers %d, pages %d\n",
# 		     proc->pid, threads, nodes, incoming_refs, outgoing_refs,
# 		     active_transactions, buffers, page_count);
def translateBinderRelease(line, timestamp, makeDict):
	splitLine = line.split(' ')
	pid = splitLine[1]
	threads = splitLine[3][:-1]
	nodes = splitLine[5]
	irefs = splitLine[7][:-2]
	orefs = splitLine[9][:-1]
	ats = splitLine[12][:-1]
	buffers = splitLine[14][:-1]
	pages = splitLine[16]

        if makeDict:
                binderDict = {}
                binderDict.op = "binder_release"
                binderDict.pid = pid
                binderDict.proc = getProcessNameFor(pid)
                binderDict.threads = threads
                binderDict.nodes = nodes
                binderDict.irefs = irefs
                binderDict.orefs = orefs
                binderDict.ats = ats
                binderDict.buffers = buffers
                binderDict.pages = pages
                return binderDict
        
	print("[%s] binder_release: pid %s (%s) released %s threads, %s nodes, %s incoming refs, %s outgoing refs, %s active transactions, %s buffers, %s pages" % 
		(timestamp, pid, getProcessNameFor(pid), threads, nodes, irefs, orefs, ats, buffers, pages))

# binder.c#2812
# binder_debug(BINDER_DEBUG_OPEN_CLOSE,
#      "binder: %d open vm area %lx-%lx (%ld K) vma %lx pagep %lx\n",
#      proc->pid, vma->vm_start, vma->vm_end,
#      (vma->vm_end - vma->vm_start) / SZ_1K, vma->vm_flags,
#      (unsigned long)pgprot_val(vma->vm_page_prot));
def translateBinderOpenVma(line, timestamp, makeDict):
	splitLine = line.split(' ')
	pid = splitLine[1]
	vma = splitLine[5]
	vmaStart = vma[:vma.find('-')]
	vmaEnd = vma[vma.find('-')+1:]
	size = splitLine[6][1:]
	flags = splitLine[9]
	prot = splitLine[11]

        if makeDict:
                binderDict = {}
                binderDict.op = "binder_openvm"
                binderDict.pid = pid
                binderDict.proc = getProcessNameFor(pid)
                binderDict.vma = vma
                binderDict.vmaStart = vmaStart
                binderDict.vmaEnd = vmaEnd
                binderDict.size = size
                binderDict.flags = flags
                binderDict.prot = prot
                return binderDict
        
	print("[%s] binder: pid %s (%s) opened vm area addr %s-%s, size %s, flags %s, prot %s" %
	 (timestamp, pid, getProcessNameFor(pid), vmaStart, vmaEnd, size, flags, prot))

# binder.c#2822
# binder: 12098 close vm area ae942000-aea40000 (1016 K) vma 2220051 pagep 79f
# binder_debug(BINDER_DEBUG_OPEN_CLOSE,
#      "binder: %d close vm area %lx-%lx (%ld K) vma %lx pagep %lx\n",
#      proc->pid, vma->vm_start, vma->vm_end,
#      (vma->vm_end - vma->vm_start) / SZ_1K, vma->vm_flags,
#      (unsigned long)pgprot_val(vma->vm_page_prot));
def translateBinderCloseVma(line, timestamp, makeDict):
	splitLine = line.split(' ')
	pid = splitLine[1]
	vma = splitLine[5]
	vmaStart = vma[:vma.find('-')]
	vmaEnd = vma[vma.find('-')+1:]
	size = splitLine[6][1:]
	flags = splitLine[9]
	prot = splitLine[11]

        if makeDict:
                binderDict = {}
               # binderDict'op'] = "binder_closevm"
               # binderDict['pid'] = pid
                binderDict.proc = getProcessNameFor(pid)
                binderDict.vma = vma
                binderDict.vmaStart = vmaStart
                binderDict.vmaEnd = vmaEnd
                binderDict.size = size
                binderDict.flags = flags
                binderDict.prot = prot
                return binderDict
        
	return ("[%s] binder: pid %s (%s) closed vm area addr %s-%s, size %s, flags %s, prot %s" % 
		(timestamp, pid, getProcessNameFor(pid), vmaStart, vmaEnd, size, flags, prot))

# binder.c#2496
# binder: 188:276 BR_TRANSACTION 325830 14054:14054, cmd -2144833022size 100-0 ptr b6982028-b698208c
# binder_debug(BINDER_DEBUG_TRANSACTION,
# 			     "binder: %d:%d %s %d %d:%d, cmd %d"
# 			     "size %zd-%zd ptr %p-%p\n",
# 			     proc->pid, thread->pid,
# 			     (cmd == BR_TRANSACTION) ? "BR_TRANSACTION" : "BR_REPLY",
# 			     t->debug_id, t->from ? t->from->proc->pid : 0,
# 			     t->from ? t->from->pid : 0, cmd,
# 			     t->buffer->data_size, t->buffer->offsets_size,
# 			     tr.data.ptr.buffer, tr.data.ptr.offsets);
def translateBinderReturn(line, timestamp, makeDict):
	splitLine = line.split(' ')
	pid = splitLine[1]
	c = pid.find(':')
	procPid = pid[:c]
	threadPid = pid[c+1:]

	cmd = splitLine[2]
	transactionDebugId = splitLine[3]

	fromPid = splitLine[4]
	c2 = fromPid.find(':')
	fromProcPid = fromPid[:c2]
	fromThreadPid = fromPid[c2+1:-1]

	cmdUInt = splitLine[6][:-4]			# kernel 3.4 specific

	bufferSize = splitLine[7]
	bufferDataSize = bufferSize[:bufferSize.find('-')]
	bufferOffsetsSize = bufferSize[bufferSize.find('-')+1:]
	
	bufferAddresses = splitLine[9]
	bufferDataAddress = bufferAddresses[:bufferAddresses.find('-')]
	bufferOffsetsAddress = bufferAddresses[bufferAddresses.find('-')+1:]

	fromString = "process pid " + fromProcPid + " (" + getProcessNameFor(fromProcPid) + "), thread pid " + fromThreadPid

        if fromProcPid == "0":
		fromString = "n/a"

        if makeDict:
                binderDict = {}
                binderDict['op'] = "BR_TRANSACTION"
                binderDict['pid'] = pid
                binderDict['procpid'] = procPid
                binderDict['proc'] = getProcessNameFor(procPid)
                binderDict['threadPid'] = threadPid
                binderDict['cmd'] = cmd
                binderDict['transactionDebugId'] = transactionDebugId
                binderDict['fromPid'] = fromPid
                binderDict['fromProcPid'] = fromProcPid
                binderDict['fromProc'] = getProcessNameFor(fromProcPid) 
                binderDict['fromThreadPid'] = fromThreadPid
                binderDict['cmdUInt'] = cmdUInt
                binderDict['bufferSize'] = bufferSize
                binderDict['bufferDataSize'] = bufferDataSize
                binderDict['bufferOffsetsSize'] = bufferOffsetsSize
                binderDict['bufferAddresses'] = bufferAddresses
                binderDict['bufferDataAddress'] = bufferDataAddress
                binderDict['bufferOffsetsAddress'] = bufferOffsetsAddress
                binderDict['fromString'] = fromString
                return binderDict
        
	return ("[%s] binder_return %s: process pid %s (%s), thread pid %s, from %s, \
transaction id %s, command value %s, data address %s, data size %s, offsets address %s, offsets size %s" % 
		(timestamp, cmd, procPid, getProcessNameFor(procPid), threadPid, fromString, transactionDebugId, 
			cmdUInt, bufferDataAddress, bufferDataSize, bufferOffsetsAddress, bufferOffsetsSize))

# binder.c#1542
# binder: 188:8898 BC_REPLY 1449663 -> 635:1046, data   (null)-  (null) size 0-0
# binder: 635:25898 BC_REPLY 8134681 -> 25641:25641, data 94364740-  (null) size 8-0
# binder_debug(BINDER_DEBUG_TRANSACTION,
# 			     "binder: %d:%d BC_REPLY %d -> %d:%d, "
# 			     "data %p-%p size %zd-%zd\n",
# 			     proc->pid, thread->pid, t->debug_id,
# 			     target_proc->pid, target_thread->pid,
# 			     tr->data.ptr.buffer, tr->data.ptr.offsets,
# 			     tr->data_size, tr->offsets_size);
def translateBinderCommandReply(line, timestamp, makeDict):
	splitLine = line.split(' ')
	sender = splitLine[1]
	senderPid = sender[:sender.find(':')]
	senderThread = sender[sender.find(':')+1:]

	debugId = splitLine[3]

	target = splitLine[5]
	targetPid = target[:target.find(':')]
	targetThread = target[target.find(':')+1:]

	addrs = line[line.find('data') : line.find('size')]
	bufferAddr = addrs[addrs.find(' ') : addrs.find('-')].strip()
	offsetsAddr = addrs[addrs.find('-')+1:].strip()

	if "null" in bufferAddr:
		bufferAddr = "null"
	if "null" in offsetsAddr:
		offsetsAddr = "null"

	sizes = line[line.find('size'):]
	bufferSize = sizes[sizes.find(' ') : sizes.find('-')].strip()
	offsetsSize = sizes[sizes.find('-')+1:].strip()

	extra = translateBinderCommandExtras(line, line.find('size')+1+len(sizes))

        
        if makeDict:
                binderDict = {}
                binderDict['op'] = "BC_REPLY"
                binderDict['sender'] = getProcessNameFor(senderPid)
                binderDict['senderPid'] = senderPid
                binderDict['senderThread'] = senderThread
                binderDict['debugId'] = debugId
                binderDict['target'] = getProcessNameFor(targetPid)
                binderDict['targetPid'] = targetPid
                binderDict['targetThread'] = targetThread
                binderDict['addrs'] = addrs
                binderDict['bufferAddr'] = bufferAddr
                binderDict['offsetsAddr'] = offsetsAddr
                binderDict['sizes'] = sizes
                binderDict['bufferSize'] = bufferSize
                binderDict['offsetsSize'] = offsetsSize
                binderDict['extra'] = extra
                return binderDict
        
	return ("[%s] binder_command BC_REPLY: process pid %s (%s), thread pid %s -> process pid %s (%s), thread pid %s \
transaction id %s, data address %s, data size %s, offsets address %s, offsets size %s %s" % 
		(timestamp, senderPid, getProcessNameFor(senderPid), senderThread, targetPid, getProcessNameFor(targetPid),
		targetThread, debugId, bufferAddr, bufferSize, offsetsAddr, offsetsSize, extra))

# binder.c#1550
# binder: 635:653 BC_TRANSACTION 1449664 -> 188 - node 6351, data 9cb20400-  (null) size 80-0
# binder_debug(BINDER_DEBUG_TRANSACTION,
# 			     "binder: %d:%d BC_TRANSACTION %d -> "
# 			     "%d - node %d, data %p-%p size %zd-%zd\n",
# 			     proc->pid, thread->pid, t->debug_id,
# 			     target_proc->pid, target_node->debug_id,
# 			     tr->data.ptr.buffer, tr->data.ptr.offsets,
# 			     tr->data_size, tr->offsets_size);
def translateBinderCommandTransaction(line, timestamp, makeDict):
	splitLine = line.split(' ')
	sender = splitLine[1]
	senderPid = sender[:sender.find(':')]
	senderThread = sender[sender.find(':')+1:]

	debugId = splitLine[3]

	targetPid = splitLine[5]
	targetNodeDebugId = splitLine[8]

	addrs = line[line.find('data') : line.find('size')]
	bufferAddr = addrs[addrs.find(' ') : addrs.find('-')].strip()
	offsetsAddr = addrs[addrs.find('-')+1:].strip()

	if "null" in bufferAddr:
		bufferAddr = "null"
	if "null" in offsetsAddr:
		offsetsAddr = "null"

	sizes = line[line.find('size'):]
	bufferSize = sizes[sizes.find(' ') : sizes.find('-')].strip()
	offsetsSize = sizes[sizes.find('-')+1:].strip()

	extra = translateBinderCommandExtras(line, line.find('size')+1+len(sizes))

        if makeDict:
                binderDict = {}
                binderDict['op'] = "BC_TRANSACTION"
                binderDict['sender'] = getProcessNameFor(senderPid)
                binderDict['senderPid'] = senderPid
                binderDict['senderThread'] = senderThread
                binderDict['debugId'] = debugId
                binderDict['targetNodeDebugId'] = targetNodeDebugId
                binderDict['targetPid'] = targetPid
                binderDict['target'] = getProcessNameFor(targetPid)
                binderDict['addrs'] = addrs
                binderDict['bufferAddr'] = bufferAddr
                binderDict['offsetsAddr'] = offsetsAddr
                binderDict['sizes'] = sizes
                binderDict['bufferSize'] = bufferSize
                binderDict['offsetsSize'] = offsetsSize
                binderDict['extra'] = extra
                return binderDict
        
	return ("[%s] binder_command BC_TRANSACTION: process pid %s (%s), thread pid %s -> process pid %s (%s), node id %s \
transaction id %s, data address %s, data size %s, offsets address %s, offsets size %s %s" % 
		(timestamp, senderPid, getProcessNameFor(senderPid), senderThread, targetPid, getProcessNameFor(targetPid),
		targetNodeDebugId, debugId, bufferAddr, bufferSize, offsetsAddr, offsetsSize, extra))

# binder_debug(BINDER_DEBUG_TRANSACTION,
#      "        node %d u%p -> ref %d desc %d\n",
#      node->debug_id, node->ptr, ref->debug_id,
#      ref->desc);
# binder_debug(BINDER_DEBUG_TRANSACTION,
#      "        ref %d desc %d -> node %d u%p\n",
#      ref->debug_id, ref->desc, ref->node->debug_id,
#      ref->node->ptr);
# binder_debug(BINDER_DEBUG_TRANSACTION,
#      "        ref %d desc %d -> ref %d desc %d (node %d)\n",
#      ref->debug_id, ref->desc, new_ref->debug_id,
#      new_ref->desc, ref->node->debug_id);
def translateBinderCommandExtras(line, end):
	extra = ""
	pos = line.find('node', end)
	pos2 = line.find('ref', end)
	if pos2 != -1 and pos2 < pos:
		pos = pos2

	if pos != -1:
		return line[pos:]
		#print "here"
		time.sleep(5)
	else:
		return ""

# binder.c:1332
# binder: 14054 buffer release 325831, size 0-0, failed at   (null)
# binder_debug(BINDER_DEBUG_TRANSACTION,
#		     "binder: %d buffer release %d, size %zd-%zd, failed at %p\n",
#		     proc->pid, buffer->debug_id,
#		     buffer->data_size, buffer->offsets_size, failed_at);
# binder_debug(BINDER_DEBUG_TRANSACTION, "        fd %ld\n", fp->handle);
# binder_debug(BINDER_DEBUG_TRANSACTION, "        ref %d desc %d (node %d)\n",
#      ref->debug_id, ref->desc, ref->node->debug_id);
# binder_debug(BINDER_DEBUG_TRANSACTION, "        node %d u%p\n",
#      node->debug_id, node->ptr);
def translateBinderBufferRelease(line, timestamp, makeDict):
	splitLine = line.split(' ')
	pid = splitLine[1]
	debugId = splitLine[4][:-1]
	size = splitLine[6]
	sizeData = size[:size.find('-')]
	sizeOffsets = size[size.find('-')+1:-1]
	failedAt = line[line.find('at')+2:]
	if "null" in failedAt:
		failedAt = ""
	else:
		failedAt = ", " + failedAt

	extra = ""
	end = line.find('at') + 2
	pos = line.find('fd', end)
	pos2 = line.find('ref', end)
	if pos != -1 and pos2 < pos:
		pos = pos2
	pos2 = line.find('node', end)
	if pos != -1 and pos2 < pos:
		pos = pos2
	if pos != -1:
		extra = line[pos:]
		print "here"
		time.sleep(5)

        if makeDict:
                binderDict = {}
                binderDict['op'] = "binder_buffer_release"
                binderDict['pid'] = pid
                binderDict['sizeData'] = sizeData
                binderDict['sizeOffsets'] = sizeOffsets
                binderDict['debugId'] = debugId
                binderDict['size'] = sizeData
                binderDict['sizeOffsets'] = sizeOffsets
                binderDict['extra'] = extra
                return binderDict
        return ("[%s] binder: process pid %s (%s) buffer release id %s, data size %s, offsets size %s %s %s" %
	 (timestamp, pid, getProcessNameFor(pid), debugId, sizeData, sizeOffsets, failedAt, extra))

# binder.c#2707
# binder: 9489:9489 write 44 at acb0aa00, read 256 at acb0a500
# binder_debug(BINDER_DEBUG_READ_WRITE,
#    "binder: %d:%d write %ld at %08lx, read %ld at %08lx\n",
#     proc->pid, thread->pid, bwr.write_size, bwr.write_buffer,
#     bwr.read_size, bwr.read_buffer);
def traslateBinderWrite(line, timestamp, makeDict):
	splitLine = line.split(' ')
	pid = splitLine[1]
	procPid = pid[:pid.find(':')]
	threadPid = pid[pid.find(':')+1:]

	writeSize = splitLine[3]
	readSize = splitLine[7]

	writeAddr = splitLine[5]
	readAddr =  splitLine[9]

        if makeDict:
                binderDict = {}
                binderDict.op = "binder_write"
                binderDict.pid = pid
                binderDict.proc = getProcessNameFor(pid)
                binderDict.threadpid = threadpid
                binderDict.writesize = writeSize
                binderDict.readSize = readSize
                binderDict.writeAddr = writeAddr
                binderDict.readAddr = readAddr
                return binder_dict
	return ("[%s] binder: process pid %s (%s), thread pid %s, writing %s bytes at addr %s reading %s bytes at addr %s" %
	 (timestamp, procPid, getProcessNameFor(procPid), threadPid, writeSize, writeAddr, readSize, readAddr))

# binder.c#2733
# binder: 635:646 wrote 8 of 8, read return 48 of 256
# binder_debug(BINDER_DEBUG_READ_WRITE,
#     "binder: %d:%d wrote %ld of %ld, read return %ld of %ld\n",
#     proc->pid, thread->pid, bwr.write_consumed, bwr.write_size,
#     bwr.read_consumed, bwr.read_size);
def translateBinderWrote(line, timestamp, makeDict):
	splitLine = line.split(' ')
	pid = splitLine[1]
	procPid = pid[:pid.find(':')]
	threadPid = pid[pid.find(':')+1:]

	writeConsumed = splitLine[3]
	writeSize = splitLine[5][:-1]

	readConsumed = splitLine[8]
	readSize = splitLine[10]
        
        if makeDict:
                binderDict = {}
                binderDict.op = "binder_wrote"
                binderDict.pid = pid
                binderDict.proc = getProcessNameFor(pid)
                binderDict.threadpid = threadpid
                binderDict.writesize = writeSize
                binderDict.readSize = readSize
                binderDict.writeConsumed = writeConsumed
                binderDict.readConsumed = readConsumed
                return binder_dict
        
	return ("[%s] binder: process pid %s (%s), thread pid %s, wrote %s of %s bytes, read %s of %s bytes" %
	 (timestamp, procPid, getProcessNameFor(procPid), threadPid, writeConsumed, writeSize, readConsumed, readSize))


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
	p2 = Popen(["grep", "-v", "BINDERFILTER"], stdin=p1.stdout, stdout=PIPE)
        p3 = Popen(["grep", "binder"], stdin=p2.stdout, stdout=PIPE)
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
		val = subprocess.check_output("adb shell \"ls /data\" ",shell=True)
	except subprocess.CalledProcessError:
		sys.exit()
        
def generateDebugMask(l):
	debugMask = 0
	for i in l:
		debugMask += 1 << i

	return debugMask

def PrettyPrint(debugMask, debugArray, printForever, returnDontPrint, visualize=False):

	if debugMask == 0:
		debugMask = generateDebugMask(debugArray)

	systemChecks()

        # set the kernel module parameter for binder_debug() statements
	cmd='adb shell \"echo \'' + str(debugMask) + '\' > /sys/module/binder/parameters/debug_mask \"'
	subprocess.call(cmd, shell=True)
        
	# set the kernel log level
        cmd='adb shell \"echo 7 > /proc/sys/kernel/printk\"'
	subprocess.call(cmd, shell=True)

        # failsage
        cmd='adb shell \"dmesg -n 7\"'
	subprocess.call(cmd, shell=True)
        
        # printk's have been replaced with seq_printfs
	p1 = Popen(["adb", "shell", "dmesg"], stdout=PIPE)
	p2 = Popen(["grep", "-v", "BINDERFILTER"], stdin=p1.stdout, stdout=PIPE)
        p3 = Popen(["grep", "binder"], stdin=p2.stdout, stdout=PIPE)
        output = p3.communicate()[0]

        if output:
                firstTime = getTimeStampFromLine(output.splitlines()[0])
	else :
                firstTime = 0
        
	global startingSystemTime, startingTimestamp
	startingSystemTime = datetime.datetime.now()
	startingTimestamp = firstTime
       
	if printForever == False:
		for line in getDmesg().splitlines():
                        translateLog(line, False)
		sys.exit()

	mostRecentTime = 0
        #print getDmesg()
        #print '+++++++++++++++++++++++++++++++++++++++++++++++++'
        f = open('dmesg_logs','w')
        while True:
                s = getDmesg()
                f.write(s)
		lines = s.splitlines()
                
                for line in lines:
			if (getTimeStampFromLine(line) > mostRecentTime):
                                if returnDontPrint or visualize:
                                        return translateLog(line,True)
                                else:
                                        print translateLog(line,False)[1]
                                        
		                mostRecentTime = getTimeStampFromLine(lines[-1])
