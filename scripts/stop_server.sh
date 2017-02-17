#! /bin/bash

source $(dirname $0)/common_source.sh

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

usage() {
	echo "Usage: stop_server.sh service"
	if [ -e ${PROJROOT}/daemons/running -a "x`ls ${PROJROOT}/daemons/running/*.pid 2>/dev/null`" != "x" ]; then
		echo "  The following services are listed in the run cache:"
		for svc in ${PROJROOT}/daemons/running/*.pid; do
			PID="$(cat $svc)"
			svcnm="`echo $(basename $svc) | sed 's/\.pid$//g'`"
			if kill -0 $PID &>/dev/null; then
				echo "    $svcnm running"
			else
				echo "    $svcnm has a pid file but is not running"
			fi
		done
	else
		echo "  No services currently running."
	fi
	exit 0
}

[ "x$1" != "x" ] || usage
PIDFILE=${PROJROOT}/daemons/running/$1.pid

[ -f ${PIDFILE} ] || die "no pid file - cannot stop."
PID=`cat ${PIDFILE}`

# Attempt control-c
if ! kill -0 ${PID} &>/dev/null; then
	rm -f ${PIDFILE}
	echo "Server not running but pid file exists. Will remove."
	exit 0
fi
echo "Killing process $PID"
kill -2 ${PID} &>/dev/null || die "kill SIGINT $PID failed"
timed_wait 10 || echo "$PID still running after 10 seconds after SIGINT. Will attempt SIGTERM."
kill -15 ${PID} &>/dev/null
timed_wait 5 || echo "$PID still running after 5 seconds after SIGTERM."
kill -9 ${PID} &>/dev/null
timed_wait 5 || die "Cannot terminate $PID."
rm -f $PIDFILE
echo
exit 0
