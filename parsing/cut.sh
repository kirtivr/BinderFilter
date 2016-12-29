#!/bin/bash

# usage: __cut string1 string2 string3
# finds the shortest string between string1 and string2 in string3
# string1 can be empty, __cut finds the first string before string2 in string3
# string2 can be empty, __cut finds the first string after string1 in string3
# saves the resulting string in $CUT_STRING

# global storing return value of __pos()
POSITION=-1

# global storing string cut
CUT_STRING=""

# returns the first position of string b in string a, -1 if does not exist
# params: $1 overall string
#         $2 substring to find in $1
#         $3 position to start at
__pos() {
	overallString=$1

	if [[ $3 -gt 0 ]]; then
		overallString=${overallString:$3}
	fi

	x="${overallString%%$2*}"
    if [[ $x = $overallString ]]; then 
    	POSITION=-1
    else 
    	POSITION=${#x}
	    if [[ $3 -gt 0 ]]; then
			let "POSITION = $POSITION + $3"
		fi
    fi
}

# async from 637:660 to 187:0 node 7653 handle 19 size 80:0
# returns string between two strings, preceding and trailing spaces stripped
# params: $1 - first string
#         $2 - second string
#         $3 - overall string
__cut() {
	if [ -z "$1" ] && [ -z "$2" ]; then
		echo "Two null arguments!";
		return 1;
	fi

	# get position of string a
	__pos "$3" "$1" 0
	firstPos_a=$POSITION
	let "nextPos = $firstPos_a + ${#1}" # next position is char after length of 1st string

	# echo "a: $1"
	# echo "b: $2"
	# echo "c: $3"
	# echo "first position of a is $firstPos_a"
	# echo "nextPos to search for is $nextPos"

	# first argument null means find the first instance 
	if [ -z "$1" ]; then
		firstPos_a=0
	fi

	# get position of string b
	__pos "$3" "$2" $nextPos
	firstPos_b=$POSITION

	# echo "first position of b is $firstPos_b"

	# second argument null means find the last instance
	if [ -z "$2" ]; then
		let "firstPos_b = ${#3} + 1"
	fi

	#echo "first position of $2 is" $firstPos_b

	if [ $firstPos_a -gt $firstPos_b ]; then
		echo "error, $1 is after $2"
		return 1
	fi

	finalPos_a=$firstPos_a
	while [ 1 ]; do
		if [ -z "$1" ]; then
			break;
		fi

		__pos "$3" "$1" $nextPos
		if [ $POSITION -eq -1 ]; then
			break
		fi

		secondPos_a=$POSITION

		# echo "second position of $1 is " $secondPos_a

		if [ $secondPos_a -eq -1 ]; then
			break
		fi

		if [ $secondPos_a -gt $firstPos_b ]; then
			break
		fi

		# else, the next position of a exists, and is less than position of b
		finalPos_a=$secondPos_a
		let "nextPos = $secondPos_a + ${#1} + 1"

		#echo "final position of $1 is " $finalPos_a
	done
	
	#echo "final position of $1 is " $finalPos_a

	# return the string between the final position of a and b
	let "finalPos_a = finalPos_a + ${#1}"
	let "len = firstPos_b - finalPos_a"
	#echo ${3:finalPos_a:len}

	CUT_STRING=${3:finalPos_a:len}

	#cut out any spaces from the first and last char, if exist
	if [ "${CUT_STRING:0:1}" == " " ]; then
		CUT_STRING=${CUT_STRING:1:${#CUT_STRING}-1}
	fi

	if [ "${CUT_STRING:${#CUT_STRING}-1:1}" == " " ]; then
		CUT_STRING=${CUT_STRING:0:${#CUT_STRING}-1}
	fi
}

# __cut '' 'from' 'async from 637:660 to 187:0 node 7653 handle 19 size 80:0'
# echo $CUT_STRING
# __cut "1" "6" "12123444456"
# echo $CUT_STRING
# __cut '2' '' "123"
# echo $CUT_STRING


