#!/bin/bash
#
# to do: linux timestamps to human readable
#			local vars in functions?
#			why can't we find processes in ps?

: '
options:

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
'


source cut.sh
source translate.sh
BINDER_DEBUG_FLAG=0

usage() {
	echo "usage!"
}

while getopts “hk:” OPTION
do
     case $OPTION in
         h)
             usage
             exit 1
             ;;
         k)
			 BINDER_DEBUG_FLAG=1
             DEBUG_ARRAY+=("$OPTARG")
             if ! [[ "$OPTARG" =~ [0-9]|[0-1][0-5] ]]; then
             	echo "bad argument to -k!"
             	exit 1
             fi
             ;;
         ?)
             usage
             exit
             ;;
     esac
done
shift $((OPTIND -1))

#echo "The whole list of values is '${DEBUG_ARRAY[@]}'"

for val in "${DEBUG_ARRAY[@]}"; do
    if [ "$val" ==  "a" ]; then
    	DEBUG_MASK=1111111111111111
    	break
    else
    	let "DEBUG_MASK += 1 << $val"
    fi
done

#echo $DEBUG_MASK

# check for kernel version (and also adb shell access)
version=`adb shell cat /proc/version`

if [ -z "$version" ]; then
	exit 1
fi 

# check for root access
su_access=`adb shell "su -c 'ls /data'"`
if [[ "$su_access" == *"su: not found"* ]]; then
	echo "no root access!"
	exit 1
fi

__cut "version" "-" "$version"

if [ $CUT_STRING != "3.4.0" ]; then
	echo "Linux kernel version is not 3.4.0 (most recent), logging may not be accurate!"
fi

# printing binder_debug() (printk()) statements user requested
if [ $BINDER_DEBUG_FLAG == 1 ]; then
	adb shell "su -c echo $DEBUG_MASK '> /sys/module/binder/parameters/debug_mask'"

	starting_line=`adb shell dmesg | grep binder | (tac 2> /dev/null || tail -r) | head -n 1`
	__cut [ ] "$starting_line"
	starting_time=$CUT_STRING

	#echo "starting time: " $starting_time

	while true; do
		# read dmesg from the most recent line until last line printed
		output_array=()
		next_time=
		first_loop=0
		while read line; do
			__cut [ ] "$line"
			current_time=$CUT_STRING

			if [ $first_loop -eq 0 ]; then
				first_loop=1
				next_time=$current_time
				#echo "set next time as" $next_time ""
			fi

			if (( "${current_time//.}" <= "${starting_time//.}" )); then
				#echo "current time: " $current_time ", prev printed time: " $starting_time
				break
			fi

			output_array+=("$line")
		done <<< "`adb shell dmesg | grep binder | (tac 2> /dev/null || tail -r)`"

		# reverse output
		num_output=${#output_array[@]}
		while [ $num_output -gt 0 ]; do
			let "i = $num_output - 1"
			let "num_output = $num_output - 1"
			
			echo "${output_array[$i]}"
			translate_binder "${output_array[$i]}"
		done

		starting_time=$next_time
	done

fi

