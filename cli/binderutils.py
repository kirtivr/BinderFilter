
import sys, time
import subprocess
from subprocess import Popen, PIPE
import datetime

def getRoot():
    try:
        ret = subprocess.check_output("adb root",shell=True)
    except subprocess.CalledProcessError as e:
        print e.output
        print 'Please check if you have a rooted device connected'
        sys.exit(0)

    try:
	val = subprocess.check_output("adb shell \"ls /data\" ",shell=True)
    except subprocess.CalledProcessError:
        print 'You do not have adb shell access'
        sys.exit()


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

def getProcessNameFor(pid):
    if False:
        val = subprocess.check_output(["adb", "shell", "ps", "-p", str(pid)])
        val = val[val.find('\n')+1:]
        val = val[val.rfind(' ')+1:]
        val = val.rstrip()
        if val == "":
	    return "process exited"
        return val
    else:
        return str(pid)
    
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

def generateDebugMask(l):
    debugMask = 0
    for i in l:
	debugMask += 1 << i

    return debugMask
