import sys
import binderutils as buu
import graphviz as gv
import argparse
import functools
import datetime
import urllib
import re
import subprocess
from datetime import timedelta

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
                
def printSequenceDiagram(sequences):
    style = "qsd"
    text = ''

    for seq in sequences:
        if seq['op'] == "BR_TRANSACTION":
            sender = 'binder'
            target = seq["fromProc"]
        elif seq['op'] == "BR_REPLY":
            sender = 'binder'
            target = seq['fromProc']
        elif seq['op'] == "BC_TRANSACTION":
            sender = seq["sender"]
            target = 'binder'
        elif seq['op'] == "BC_REPLY":
            sender = seq["sender"]
            target = 'binder'

        text = text + str(sender) + '->' + str(target) + ': '+ seq['op'] + '\n'

    print text
    
    pngFile = "sequence.png"

    gotseq = getSequenceDiagram(text, pngFile, style)
    if gotseq:
        print 'Check sequence.png for the sequence diagram!'

def add_nodes(graph, nodes, style):
    for n in nodes:
        if isinstance(n, tuple):
            graph.node(n[0], **n[1])
        else:
            graph.node(n)

    graph.node_attr.update(style)

    return graph


def add_edges(graph, edges):
    #print edges
    for e in edges:
     #   print e
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
        add_edges(add_nodes(digraph(),nodes,node_style),edges).render("graph")
                
    elif info['op'] == "BC_TRANSACTION" or info['op'] == "BC_REPLY":
        nodes.append(info["sender"])
        nodes.append(info["target"])
                
        if mode == 'abstract':
            if ((info["sender"],info["target"],info['op']) not in edges): 
                edges.append((info["sender"],info["target"],info['op']))
        else:
            edges.append((info["sender"],info["target"],info['op']))
                        
        # render !
        add_edges(add_nodes(digraph(),nodes,node_style),edges).render("graph")
    else:
        return

#[ 2159.006957] binder: 188:276 BR_TRANSACTION 325830 14054:14054, cmd -2144833022size 100-0 ptr b6982028-b698208c
def translateLog(line, sttime, systime):
    if line == "":
        return None
    
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
    binderDict = {}
    if "BR_TRANSACTION" in line :
        binderDict['op'] = "BR_TRANSACTION"
    else :
        binderDict['op'] = "BR_REPLY"
    binderDict['pid'] = pid
    binderDict['procpid'] = procPid
    binderDict['proc'] = buu.getProcessNameFor(procPid)
    binderDict['threadPid'] = threadPid
    binderDict['fromPid'] = fromPid
    binderDict['fromProcPid'] = fromProcPid
    binderDict['fromProc'] = buu.getProcessNameFor(fromProcPid) 
    binderDict['fromThreadPid'] = fromThreadPid
    binderDict['timestamp'] = timestamp
        
    return binderDict
    
def translateBinderCommandReply(line, timestamp):
    splitLine = line.split(' ')
    sender = splitLine[1]
    senderPid = sender[:sender.find(':')]
    senderThread = sender[sender.find(':')+1:]

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
    binderDict['timestamp'] = timestamp
    
    return binderDict
    

def translateBinderCommandTransaction(line, timestamp):
    splitLine = line.split(' ')
    sender = splitLine[1]
    senderPid = sender[:sender.find(':')]
    senderThread = sender[sender.find(':')+1:]
    targetPid = splitLine[5]

    binderDict = {}
    binderDict['op'] = "BC_TRANSACTION"
    binderDict['sender'] = buu.getProcessNameFor(senderPid)
    binderDict['senderPid'] = senderPid
    binderDict['senderThread'] = senderThread
    binderDict['targetPid'] = targetPid
    binderDict['target'] = buu.getProcessNameFor(targetPid)
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

def main(argv):
    # demo
    if False:
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

            if True:
                with open('dmesg_logs','r') as dmesg_logs:
                    s = dmesg_logs.read()
                    lines = s.splitlines()
            
                    if lines:
                        firstTime = buu.getTimeStampFromLine(lines[0])
	            else :
                        firstTime = 0

	            startingSystemTime = datetime.datetime.now()
                    startingTimestamp = firstTime

                    for line in lines :
                        info = translateLog(line, startingTimestamp, startingSystemTime)
                        if isValidBinderOp(info):
                            visualize(digraph,info,nodes,edges,mode)
                
            else:
                while True:
                    info = getBinderLog(debugMask, debugArray)
                    print info
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
    
            if True:
                with open('dmesg_logs','r') as dmesg_logs:
                    s = dmesg_logs.read()
                    lines = s.splitlines()
            
                    if lines:
                        firstTime = buu.getTimeStampFromLine(lines[0])
	            else :
                        firstTime = 0
                    
	            startingSystemTime = datetime.datetime.now()
                    startingTimestamp = firstTime
                    sequence = []

                    for line in lines :
                        info = translateLog(line, startingTimestamp, startingSystemTime)
                        nodes = []
                        
                        if info:
                            if info['op'] == "BR_TRANSACTION" or info['op'] == "BR_REPLY":
                                nodes.append(info["fromProc"])
                                nodes.append(info["proc"])
                            elif info['op'] == "BC_TRANSACTION" or info['op'] == "BC_REPLY":
                                nodes.append(info["sender"])
                                nodes.append(info["target"])

                            if set(nodes) == set(procs):
                                
                                sequence.append(info)
                            
                    if sequence:
                        # we are only printing a 100 sequences since more than that and cloudflare kicks in
                        if len(sequence) > 100:
                            printSequenceDiagram(sequence[:100])
                        else:
                            printSequenceDiagram(sequence)
                
            else:
                while True:
                    info = getBinderLog(debugMask, debugArray)
                    if isValidBinderOp(info):
                        printSequenceDiagram(opt[1])

    if fail:
        print 'Please use -v for call graph, -s for sequence diagram'
if __name__ == "__main__":
    main(sys.argv[1:])
