#! /bin/bash

# die(message)
die () {
	echo "Error: $1"
	exit 1
}

# timed_wait(timeout)
timed_wait () {
	local SECS=0
	while kill -0 $PID &> /dev/null && [ $SECS -lt $1 ]; do 
		sleep 1
		let SECS=SECS+1
	done
	kill -0 ${PID} &>/dev/null && return 1
	return 0
}

[ -f run/server.pid ] || die "no pid file - cannot stop."
PID=`cat run/server.pid`

# Attempt control-c
if ! kill -0 ${PID} &>/dev/null; then
	rm -f run/server.pid
	echo "Server not running but pid file exists. Will remove."
	exit 0
fi
echo "Killing process $PID"
kill -2 ${PID} &>/dev/null || die "kill SIGINT $PID failed"
timed_wait 5 || echo "$PID still running after 5 seconds after SIGINT. Will attempt SIGTERM."
kill -15 ${PID} &>/dev/null
timed_wait 5 || echo "$PID still running after 5 seconds after SIGTERM."
kill -9 ${PID} &>/dev/null
timed_wait 5 || die "Cannot terminate $PID."
rm -f run/server.pid
echo
exit 0
