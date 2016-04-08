#!/bin/bash
# references from http://androidxref.com/kernel_3.4/xref/drivers/staging/android/binder.c

source cut.sh

HTIME=""
_gethumantimefor() {
	# rounds to the second (htime = floor(ktime))
	# [122214.186086]   [seconds.milliseconds]

	# for linux
	#echo "ts: $ts, uptime: $uptime, s: $s"
	#HTIME=$(date -d"70-1-1 + $ts sec - $uptime sec + $s sec" +"%F %T")

	__cut "[" "." "$1"
	local kernel_s=$CUT_STRING

	local u=$(adb shell cat '/proc/uptime' | cut -d' ' -f1 | tr -d '\r')
	__cut "" "." "$u"
	local uptime_s=$CUT_STRING
	local now_s=$(adb shell date +%s | tr -d '\r')

	let "seconds = $now_s - $uptime_s + $kernel_s"
	
	HTIME=$(date -j -r $seconds +%H:%M | tr -d '\r')
	#HTIME=$(date -j -r $seconds | tr -d '\r')

	#echo $HTIME
}

PROCESS_NAME=""
_getprocessnamefor() {
	local result=`adb shell ps -p $1 | grep $1 | tr -s ' ' | cut -d' ' -f13`
	if [ -z "$result" ]; then
		PROCESS_NAME="process exited"
	else
		PROCESS_NAME="$result"
	fi

	PROCESS_NAME=$(echo $PROCESS_NAME | tr -d '\r')
}

: '
binder.c#2937
[122214.186086] binder_open: 18298:18298
binder_debug(BINDER_DEBUG_OPEN_CLOSE, "binder_open: %d:%d\n",
 					current->group_leader->pid, current->pid);
'
_binder_open() {
	__cut "binder_open:" ":" "$1"
	local a=$CUT_STRING
	__cut ":" "" "$1"
	local b=$CUT_STRING
	b=$(echo $b | tr -d '\r')

	_getprocessnamefor $b
	_gethumantimefor "$1"
	echo "[$HTIME] binder_open: group leader pid $a, current pid $b ($PROCESS_NAME)"
}

: '
binder.c#2848
[122214.186238] binder_mmap: 18298 ae942000-aea40000 (1016 K) vma 200071 pagep 79f
binder_debug(BINDER_DEBUG_OPEN_CLOSE,
	     "binder_mmap: %d %lx-%lx (%ld K) vma %lx pagep %lx\n",
	     proc->pid, vma->vm_start, vma->vm_end,
	     (vma->vm_end - vma->vm_start) / SZ_1K, vma->vm_flags,
	     (unsigned long)pgprot_val(vma->vm_page_prot));
'
_binder_mmap() {
	# you need this in case the timestamp is in the format [  681.788085]
	# as the cut command relies on there not being a space between [ and 681
	__cut "." "" "$1"
	condensed=$CUT_STRING		

	local pid=$(echo $condensed | cut -d' ' -f3 | tr -d '\r')
	
	local vma=$(echo $condensed | cut -d' ' -f4 | tr -d '\r')
	__cut "" "-" "$vma"
	local vma_start=$CUT_STRING
	__cut "-" "" "$vma"
	local vma_end=$CUT_STRING

	__cut "(" ")" "$1"
	local size=$CUT_STRING

	__cut "vma" "pagep" "$1"
	local flags=$CUT_STRING

	__cut "pagep" "" "$1"
	local prot=$CUT_STRING

	_getprocessnamefor $pid
	_gethumantimefor "$1"
	echo "[$HTIME] binder_mmap: pid $pid ($PROCESS_NAME) mapped addr $vma_start-$vma_end, \
size $size, flags $flags, prot $prot"
}

: '
binder.c#2992	
[122214.199605] binder_flush: 18298 woke 2 threads
binder_debug(BINDER_DEBUG_OPEN_CLOSE,
    "binder_flush: %d woke %d threads\n", proc->pid, wake_count);
'
_binder_flush() {
	__cut "." "" "$1"
	condensed=$CUT_STRING

	local pid=$(echo $condensed | cut -d' ' -f3 | tr -d '\r')
	local num=$(echo $condensed | cut -d' ' -f5 | tr -d '\r')
	_getprocessnamefor $pid
	_gethumantimefor "$1"

	echo "[$HTIME] binder_flush: pid $pid ($PROCESS_NAME) woke $num threads"
}

: '
binder.c#3120
[122214.426229] binder_release: 18298 threads 3, nodes 1 (ref 0), refs 2, active transactions 0, buffers 0, pages 1	
binder_debug(BINDER_DEBUG_OPEN_CLOSE,
		     "binder_release: %d threads %d, nodes %d (ref %d), "
		     "refs %d, active transactions %d, buffers %d, pages %d\n",
		     proc->pid, threads, nodes, incoming_refs, outgoing_refs,
		     active_transactions, buffers, page_count);
'
_binder_release_open_close() {
	__cut "." "" "$1"
	condensed=$CUT_STRING

	local pid=$(echo $condensed | cut -d' ' -f3 | tr -d ', \r')
	local threads=$(echo $condensed | cut -d' ' -f5 | tr -d ', \r')
	local nodes=$(echo $condensed | cut -d' ' -f7 | tr -d ', \r')
	local irefs=$(echo $condensed | cut -d' ' -f9 | tr -d '), \r')
	local orefs=$(echo $condensed | cut -d' ' -f11 | tr -d ', \r')
	local ats=$(echo $condensed | cut -d' ' -f14 | tr -d ', \r')
	local bufs=$(echo $condensed | cut -d' ' -f16 | tr -d ', \r')
	local pages=$(echo $condensed | cut -d' ' -f18 | tr -d ', \r')

	_getprocessnamefor $pid
	_gethumantimefor "$1"
	echo "[$HTIME] binder_release: pid $pid ($PROCESS_NAME) released $threads threads, \
$nodes nodes, $irefs incoming refs, $orefs outgoing refs, $ats active transactions, \
$bufs buffers, $pages pages"
}

: '
binder.c#2822
[147595.627917] binder: 12098 close vm area ae942000-aea40000 (1016 K) vma 2220051 pagep 79f
binder_debug(BINDER_DEBUG_OPEN_CLOSE,
     "binder: %d close vm area %lx-%lx (%ld K) vma %lx pagep %lx\n",
     proc->pid, vma->vm_start, vma->vm_end,
     (vma->vm_end - vma->vm_start) / SZ_1K, vma->vm_flags,
     (unsigned long)pgprot_val(vma->vm_page_prot));
'
_binder_close_vm() {
	__cut ":" "close" "$1"
	local pid=$CUT_STRING

	__cut "area" "(" "$1"	
	local vma=$CUT_STRING
	__cut "" "-" "$vma"
	local vma_start=$CUT_STRING
	__cut "-" "" "$vma"
	local vma_end=$CUT_STRING

	__cut "(" ")" "$1"
	local size=$CUT_STRING

	__cut "vma" "pagep" "$1"
	local flags=$CUT_STRING

	__cut "pagep" "" "$1"
	local prot=$CUT_STRING

	_getprocessnamefor $pid
	_gethumantimefor "$1"
	echo "[$HTIME] binder: pid $pid ($PROCESS_NAME) closed vm area addr $vma_start-$vma_end, \
size $size, flags $flags, prot $prot"
}

: '
binder.c#2812
binder_debug(BINDER_DEBUG_OPEN_CLOSE,
     "binder: %d open vm area %lx-%lx (%ld K) vma %lx pagep %lx\n",
     proc->pid, vma->vm_start, vma->vm_end,
     (vma->vm_end - vma->vm_start) / SZ_1K, vma->vm_flags,
     (unsigned long)pgprot_val(vma->vm_page_prot));
'
_binder_open_vm() {
	__cut ":" "open" "$1"
	local pid=$CUT_STRING

	__cut "area" "(" "$1"	
	local vma=$CUT_STRING
	__cut "" "-" "$vma"
	local vma_start=$CUT_STRING
	__cut "-" "" "$vma"
	local vma_end=$CUT_STRING

	__cut "(" ")" "$1"
	local size=$CUT_STRING

	__cut "vma" "pagep" "$1"
	local flags=$CUT_STRING

	__cut "pagep" "" "$1"
	local prot=$CUT_STRING

	_getprocessnamefor $pid
	_gethumantimefor "$1"
	echo "[$HTIME] binder: pid $pid ($PROCESS_NAME) opened vm area addr $vma_start-$vma_end, \
size $size, flags $flags, prot $prot"
}

: '
binder.c#2496
[ 2159.006957] binder: 188:276 BR_TRANSACTION 325830 14054:14054, cmd -2144833022size 100-0 ptr b6982028-b698208c
binder_debug(BINDER_DEBUG_TRANSACTION,
			     "binder: %d:%d %s %d %d:%d, cmd %d"
			     "size %zd-%zd ptr %p-%p\n",
			     proc->pid, thread->pid,
			     (cmd == BR_TRANSACTION) ? "BR_TRANSACTION" :
			     "BR_REPLY",
			     t->debug_id, t->from ? t->from->proc->pid : 0,
			     t->from ? t->from->pid : 0, cmd,
			     t->buffer->data_size, t->buffer->offsets_size,
			     tr.data.ptr.buffer, tr.data.ptr.offsets);
'
# _binder_br_transaction() {

# }

# params: $1- binder log statement
translate_binder() {
	if [ -z "$1" ]; then
		echo "bad argument to translate_binder!"
		exit 1
	fi

	# BINDER_DEBUG_OPEN_CLOSE
	if [[ "$1" =~ .*binder_open.* ]]; then
		_binder_open "$1"
	elif [[ "$1" =~ .*binder_mmap.* ]]; then
		_binder_mmap "$1"
	elif [[ "$1" =~ .*binder_flush.* ]]; then
		_binder_flush "$1"
	elif [[ "$1" =~ .*binder_release.*active.* ]]; then
		_binder_release_open_close "$1"
	elif [[ "$1" =~ .*close.*vm.*area.* ]]; then
	 	_binder_close_vm "$1"
	elif [[ "$1" =~ .*open.*vm.*area.* ]]; then
		_binder_open_vm "$1"
	# BINDER_DEBUG_TRANSACTION
	# elif [[ "$1" =~ .*BR_TRANSACTION.* ]]; then
	#  	_binder_br_transaction "$1"
	# elif [[ "$1" =~ ]]; then
	# 	_binder_ "$1"
	# elif [[ "$1" =~ ]]; then
	# 	_binder_ "$1"
	# elif [[ "$1" =~ ]]; then
	# 	_binder_ "$1"
	# elif [[ "$1" =~ ]]; then
	# 	_binder_ "$1"
	# elif [[ "$1" =~ ]]; then
	# 	_binder_ "$1"
	# elif [[ "$1" =~ ]]; then
	# 	_binder_ "$1"
	# elif [[ "$1" =~ ]]; then
	# 	_binder_ "$1"
	else
		echo "not found"
		#sleep 1
	fi	
	
}



