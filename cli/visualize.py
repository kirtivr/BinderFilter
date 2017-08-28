#!/usr/bin/python
# Kirti Vardhan Rathore

import sys
import binderutils as buu
import graphviz as gv
import argparse
import functools
import datetime
import urllib
import re
import time
import subprocess
from subprocess import Popen, PIPE
from datetime import timedelta
from threading import Thread
from argparse import RawTextHelpFormatter

def getSequenceDiagram( text, outputFile, style = 'default' ):
    request = {}
    request["message"] = text
    request["style"] = style
    request["apiVersion"] = "1"

    url = urllib.urlencode(request)
    print url
    f = urllib.urlopen("http://www.websequencediagrams.com/", url)
    line = f.readline()
    f.close()

    expr = re.compile("(\?(img|pdf|png|svg)=[a-zA-Z0-9]+)")
    m = expr.search(line)

    if m == None:
        print "Invalid response from server."
        return False

    urllib.urlretrieve("http://www.websequencediagrams.com/" + m.group(0),
            outputFile )

    return True
                
def printSequenceDiagram(sequences,procs):
    style = "rose"
    text = 'participant '+str(procs[0])+'\nparticipant /dev/binder\n'+'participant '+str(procs[1])+'\n'
    
    for seq in sequences:
        if seq['op'] == "BR_TRANSACTION":
            sender = '/dev/binder'
            target = seq["proc"]
        elif seq['op'] == "BR_REPLY":
            sender = '/dev/binder'
            target = seq['proc']
        elif seq['op'] == "BC_TRANSACTION":
            sender = seq["sender"]
            target = '/dev/binder'
        elif seq['op'] == "BC_REPLY":
            sender = seq["sender"]
            target = '/dev/binder'

        text = text + str(sender) + '->' + str(target) + ': '+ seq['op'] + '\n'
    
    pngFile = "vizgraphs/sequence.png"

    gotseq = getSequenceDiagram(text, pngFile, style)
    if gotseq:
        print 'Check vizgraphs/sequence.png for the sequence diagram!'

def add_nodes(graph, nodes, style):
    for n in nodes:
        if isinstance(n, tuple):
            graph.node(n[0], **n[1])
        else:
            graph.node(n)

    graph.node_attr.update(style)

    return graph


def add_edges(graph, edges):
    for e in edges:
        if e[2] == "BR_TRANSACTION":
            graph.edge(e[0], e[1], color='cyan', style='filled')
        elif e[2] == "BR_REPLY":
            graph.edge(e[0], e[1], color='cyan', style='dotted',arrowhead='open')
        elif e[2] == "BC_TRANSACTION":
            graph.edge(e[0], e[1], color='white', style='filled')
        elif e[2] == "BC_REPLY":
            graph.edge(e[0], e[1], color='white', style='dotted',arrowhead='open')
                                
    graph_style = {
        'label': 'Binder Call Graph',
        'fontsize': '8',
        'fontcolor': 'white',
        'bgcolor': '#333333',
        'rankdir': 'BT',
    }
    
    graph.graph_attr.update(graph_style)
        
    return graph

def visualize(digraph, info, nodes, edges, mode):
    node_style = {
        'fontname': 'Helvetica',
        'fontcolor': 'white',
        'color': 'white',
        'style': 'filled',
        'fillcolor': '#006699',
    }

    if info['op'] == "BR_TRANSACTION" or info['op'] == "BR_REPLY":
        nodes.append(info["fromProc"])
        nodes.append(info["proc"])
    
        if mode == 'abstract':
            if ((info["fromProc"],info["proc"],info['op']) not in edges):
                edges.append((info["fromProc"],info["proc"],info['op']))
        else:
            edges.append((info["fromProc"],info["proc"],info['op']))
                
        # render !
        add_edges(add_nodes(digraph(),nodes,node_style),edges).render("vizgraphs/graph")
                
    elif info['op'] == "BC_TRANSACTION" or info['op'] == "BC_REPLY":
        nodes.append(info["sender"])
        nodes.append(info["target"])
                
        if mode == 'abstract':
            if ((info["sender"],info["target"],info['op']) not in edges): 
                edges.append((info["sender"],info["target"],info['op']))
        else:
            edges.append((info["sender"],info["target"],info['op']))
                        
        # render !
        add_edges(add_nodes(digraph(),nodes,node_style),edges).render("vizgraphs/graph")
    else:
        return

#[ 2159.006957] binder: 188:276 BR_TRANSACTION 325830 14054:14054, cmd -2144833022size 100-0 ptr b6982028-b698208c
def translateLog(line, sttime, systime):
    if line == "":
        return None
    #print line
    timestamp = line[1:line.find(']')]
    timestamp = timestamp.strip()	# handle 1-4 digit timestamps
    timestamp = translateTimestamp(timestamp, sttime, systime)
    line = line[line.find(']')+2:]	# strip the timestamp

    # BINDER_DEBUG_TRANSACTION
    if "BR_TRANSACTION" in line:
        return translateBinderReturn(line, timestamp)
    elif "BR_REPLY" in line:
	return translateBinderReturn(line, timestamp)
    elif "BC_TRANSACTION" in line:
	return translateBinderCommandTransaction(line, timestamp)
    elif "BC_REPLY" in line:
	return translateBinderCommandReply(line, timestamp)

    return None

transactionDebugInfo = {}
def addToDebugInfo(trLog):
    global transactionDebugInfo
    trLog = trLog.strip()
    logLines = trLog.split('\n')

    for line in logLines:
        splitLine = re.split('\s+',line)
        if len(splitLine) > 1:
            debugIdRaw = splitLine[0]
            c = debugIdRaw.find(':')
            debugId = debugIdRaw[:c]
            if debugId not in transactionDebugInfo:
                proc1 = splitLine[3]
                c1 = proc1.find(":")
                p1 = proc1[:c1]
                t1 = proc1[c1+1:]
                # not needed as such 
                #proc2 = splitLine[5]
                #c2 = proc2.find(":")
                #p2 = proc2[:c2]
                #t2 = proc2[c2+1:]

                transactionDebugInfo[debugId] = (p1,t1)
        
def resolveCallForDebugId(debugId):
    #print transactionDebugInfo
    if transactionDebugInfo.has_key(debugId):
        return transactionDebugInfo[debugId]
    else:
        return -1

# BR_TRANSACTION
def translateBinderReturn(line, timestamp):
    splitLine = line.split(' ')
    pid = splitLine[1]
    c = pid.find(':')
    procPid = pid[:c]
    threadPid = pid[c+1:]
    fromPid = splitLine[4]
    c2 = fromPid.find(':')
    fromProcPid = fromPid[:c2]
    fromThreadPid = fromPid[c2+1:-1]
    debugId = splitLine[3]

    binderDict = {}
    if "BR_TRANSACTION" in line :
        binderDict['op'] = "BR_TRANSACTION"
    else :
        binderDict['op'] = "BR_REPLY"
    binderDict['pid'] = pid
    binderDict['procpid'] = procPid
    binderDict['proc'] = buu.getProcessNameFor(procPid)
    binderDict['threadPid'] = threadPid
    binderDict['debugId'] = debugId
    
    # If PID is 0, this is a one way async transaction
    # Info from corr. binder command can help us resolve the PID

    if fromProcPid == '0':
        resolvedInfo = resolveCallForDebugId(debugId)
        if resolvedInfo == -1:
            binderDict['fromPid'] = fromProcPid
            binderDict['fromProc'] = 'async RPC'
            binderDict['fromThreadPid'] = fromThreadPid
        else:
            binderDict['fromPid'] = resolvedInfo[0]
            binderDict['fromProc'] = str(buu.getProcessNameFor(resolvedInfo[0])) 
            binderDict['fromThreadPid'] = resolvedInfo[1]
    else:
        binderDict['fromPid'] = fromProcPid
        binderDict['fromProc'] = buu.getProcessNameFor(fromProcPid) 
        binderDict['fromThreadPid'] = fromThreadPid
      
    binderDict['timestamp'] = timestamp

    return binderDict
    
def translateBinderCommandReply(line, timestamp):
    splitLine = line.split(' ')
    sender = splitLine[1]
    senderPid = sender[:sender.find(':')]
    senderThread = sender[sender.find(':')+1:]
    debugId = splitLine[3]
    target = splitLine[5]
    targetPid = target[:target.find(':')]
    targetThread = target[target.find(':')+1:]
    binderDict = {}
    binderDict['op'] = "BC_REPLY"
    binderDict['sender'] = buu.getProcessNameFor(senderPid)
    binderDict['senderPid'] = senderPid
    binderDict['senderThread'] = senderThread
    binderDict['target'] = buu.getProcessNameFor(targetPid)
    binderDict['targetPid'] = targetPid
    binderDict['targetThread'] = targetThread
    binderDict['debugId'] = debugId
    binderDict['timestamp'] = timestamp

    return binderDict
    

def translateBinderCommandTransaction(line, timestamp):
    splitLine = line.split(' ')
    sender = splitLine[1]
    senderPid = sender[:sender.find(':')]
    senderThread = sender[sender.find(':')+1:]
    targetPid = splitLine[5]
    debugId = splitLine[3]

    binderDict = {}
    binderDict['op'] = "BC_TRANSACTION"
    binderDict['sender'] = buu.getProcessNameFor(senderPid)
    binderDict['senderPid'] = senderPid
    binderDict['senderThread'] = senderThread
    binderDict['targetPid'] = targetPid
    binderDict['target'] = buu.getProcessNameFor(targetPid)
    binderDict['debugId'] = debugId
    binderDict['timestamp'] = timestamp

    return binderDict

def isValidBinderOp(info):
    if info != None  and type(info) is dict:
        if info['op'] == "BR_TRANSACTION" or info['op'] == "BR_REPLY" or info['op'] == "BC_TRANSACTION" or info['op'] == "BC_REPLY":
            return True
        else:
            return False
    else:
        return False

# [122214.186086]   [seconds.milliseconds]
# time printed will be based on local system time (i.e. computer time, not android time)
def translateTimestamp(ts, startingTimestamp, startingSystemTime):
    secondsPassed = float(ts) - float(startingTimestamp)
    hts = (startingSystemTime + timedelta(seconds=secondsPassed)).time()
    #return str(hts)[:str(hts).find('.')+3]
    return hts

def getBinderLog(debugMask, debugArray):
    if debugMask == 0:
	debugMask = buu.generateDebugMask(debugArray)
            
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
        firstTime = buu.getTimeStampFromLine(output.splitlines()[0])
    else :
        firstTime = 0
        
    startingSystemTime = datetime.datetime.now()
    startingTimestamp = firstTime
    mostRecentTime = 0

    while True:
        s = buu.getDmesg()
	lines = s.splitlines()
                
        for line in lines:
	    if (buu.getTimeStampFromLine(line) > mostRecentTime):
                return translateLog(line, startingTimestamp, startingSystemTime)
                
            mostRecentTime = buu.getTimeStampFromLine(lines[-1])

def pollTRLog():
    # keep polling /sys/kernel/debug/binder/transaction_log
    while True:
        addToDebugInfo(buu.getTransactionLog())

def main(argv):
    buu.getRoot()
    
    parser = argparse.ArgumentParser(description='Android Binder IPC visualizer')

    parser.add_argument("-s", "--sequence-diag", action="store", dest="argSequence", 
                        nargs="*", help="Show a sequence diagram between any two applications. "
                        "Please enter the names of the two processes")
    
    parser.add_argument("-v","--visualize", action="store", dest="argVisualize",
                        nargs="*", help="Visualize binder transactions using graphviz." 
                        "pass true or abstract as modes, true gives the real, live picture"
                        "while abstract prunes duplicate edges between nodes to give a cleaner"
                        "picture")

    results = parser.parse_args()
    opts = results._get_kwargs()

    debugArray = []                
    debugMask = 1111111111111111 #default

    fail = True

    # to get /sys/kernel/debug/binder/transaction_log
    # in sync with dmesg logs ( dmesg logs are a bit behind )
    time.sleep(0.5)
    
    for opt in opts:
        if opt[0] == "argVisualize" and opt[1] is not None:
            fail = False
            digraph = functools.partial(gv.Digraph,format='svg')
            
            nodes = []
            edges = []
        
            if type(opt[1]) is list and len(opt[1]) > 0:
                mode = opt[1][0]
            else:
                mode = 'abstract'
            
            while True:
                nodes = []
                info = getBinderLog(debugMask, debugArray)
                if isValidBinderOp(info):
                    visualize(digraph,info,nodes,edges,mode)
                
        elif opt[0] == "argSequence" and opt[1] is not None:
            fail = False
            procs = opt[1]
            
            if not procs or len(procs) != 2:
                print "Please enter the names of the communicating programs. \n For ex: python viztransactions.py -s com.android.phone com.android.systemui"
                exit(1)
                
            pid1 = procs[0]
            pid2 = procs[1]

            if len(pid1) == 0 or len(pid2) == 0:
                print "One or both of the program names were not found. "
                exit(1)

            sequence=[]
            
            while True:
                info = getBinderLog(debugMask, debugArray)
                nodes = []
                if info and isValidBinderOp(info):
                    if info['op'] == "BR_TRANSACTION" or info['op'] == "BR_REPLY":
                        nodes.append(info["fromProc"])
                        nodes.append(info["proc"])
                    elif info['op'] == "BC_TRANSACTION" or info['op'] == "BC_REPLY":
                        nodes.append(info["sender"])
                        nodes.append(info["target"])

                    if nodes and set(nodes) == set(procs):
                        sequence.append(info)
                        if len(sequence) > 5:
                            # we are only printing 30 sequences. Feel free to remove the restriction if you would like
                            printSequenceDiagram(sequence[:30],procs)
    if fail:
        print 'Please use -v for call graph, -s for sequence diagram'

if __name__ == "__main__":
    try:
        thread = Thread(target = pollTRLog)
        thread.daemon = True
        thread.start()
        main(sys.argv[1:])
    except KeyboardInterrupt:
        print "You pressed Ctrl+C"
        sys.exit(1)
