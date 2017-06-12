#! /bin/bash

# Get project root absolute path
pushd `dirname $0` 2>/dev/null >/dev/null
SCRIPTROOT=`pwd`
popd 2>/dev/null 1>/dev/null


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

cleanup () {
    rm -f $PIDFILE
    echo
    exit 0
}

usage() {
	echo "Usage: mservice.sh /path/to/service start|stop|refresh|check [service options]"
	exit 0
}


stop() {
    [ -f ${PIDFILE} ] || die "no pid file - cannot stop."
    PID=`cat ${PIDFILE}`

    # Attempt control-c
    if ! kill -0 ${PID} &>/dev/null; then
        rm -f ${PIDFILE}
        echo "Server not running but pid file exists. Will remove."
        exit 0
    fi
    echo "Terminating process $PID"
    kill -15 ${PID} &>/dev/null
    # Calling TERM twice fixes non-critical race condition when waiting in python service.
    timed_wait 5
    kill -15 ${PID} &>/dev/null
    timed_wait 25 && cleanup || echo "$PID still running after 30 seconds. Will attempt SIGINT."
    kill -2 ${PID} &>/dev/null
    timed_wait 10 && cleanup || echo "$PID still running after 40 seconds. Will attempt SIGKILL."
    kill -9 ${PID} &>/dev/null
    timed_wait 5 && cleanup || die "Cannot terminate $PID."
    exit 0
}


start() {
    if [ -f ${PIDFILE} ]; then
        PID=`cat ${PIDFILE}`
        if kill -0 ${PID} &>/dev/null; then
            die "Service is already running."
        fi
    fi
    pushd $DAEMONROOT 2>/dev/null >/dev/null
    ./$DAEMON -d -p $PIDFILE $*
    popd 2>/dev/null 1>/dev/null
    exit 0
}


refresh() {
    [ -f ${PIDFILE} ] || die "no pid file - cannot refresh."
    PID=`cat ${PIDFILE}`
    if ! kill -0 ${PID} &>/dev/null; then
        echo "Server not running but pid file exists. Call with stop to remove."
        exit 0
    fi
    # Send a HUP
    kill -1 ${PID} &>/dev/null
    exit 0
}


check() {
    if [ -e $PIDFILE ]; then
        PID="$(cat $PIDFILE)"
        if kill -0 $PID &>/dev/null; then
            echo "  $SVCNAME running"
        else
            echo "  $SVCNAME has a pid file but is not running"
        fi
	else
		echo "  $SVCNAME not running."
	fi
	exit 0
}

[ "x$1" != "x" ] || usage
[ "x$2" != "x" ] || usage
[ -e "$1" ] || die "$1 does not exist"
pushd `dirname $1` 2>/dev/null >/dev/null
DAEMONROOT=`pwd`
popd 2>/dev/null 1>/dev/null
DAEMON=`basename $1`
SVCNAME="`basename $1 | sed 's/\.[a-zA-Z0-9]*$//g'`"

if [ "x$UID" == "x0" ]; then
    PIDFILE="/var/run/${SVCNAME}.pid"
    echo "Using root credentials - pidfile is $PIDFILE"
else
    PIDFILE="${DAEMONROOT}/run/${SVCNAME}.pid"
    echo "Using local credentials - pidfile is $PIDFILE"
fi

CMD=$2
shift 2

case "$CMD" in
    "start")
        start $*
        ;;
    "stop"):
        stop
        ;;
    "refresh")
        refresh
        ;;
    "check")
        check
        ;;
    "*")
        usage
        ;;
esac

