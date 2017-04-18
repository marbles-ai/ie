#!/bin/bash

source $(dirname $0)/common_source.sh

usage() {
cat << EOF
start_server.sh [options] service-name
  -D: debug, just print what will be executed.

EOF
exit 0
}

# Process command line options
DEBUG_ON=0
SERVICE=
while getopts ":d" OPTION; do
case $OPTION in
d ) DEBUG_ON=1;;
* ) usage;;
esac
done
shift $((OPTIND-1))   
[ "x$1" != "" ] || die "missing service name $*"
SERVICE="$1"
shift
[ "x$SERVICE" != "x" ] && [ -f $PROJROOT/daemons/$SERVICE ] || die "bad service name $SERVICE"
PIDFILE=$PROJROOT/daemons/running/$SERVICE.pid
LOGFILE=$PROJROOT/daemons/log/$(create_logfile_name $SERVICE)
mkdir -p $PROJROOT/daemons/running > /dev/null
mkdir -p $PROJROOT/daemons/log > /dev/null

# Check if we are running
[ -e $PIDFILE ] && kill -0 `cat $PIDFILE` &>/dev/null && die "stop server first"
rm -f $PIDFILE > /dev/null

echo "====================================================="
echo "Running service $SERVICE"
echo "  To stop run stop_server.sh $SERVICE"
echo "  The pid will be saved at $PIDFILE"
[ $DEBUG_ON -eq 0 ] && $PROJROOT/daemons/$SERVICE $PIDFILE $LOGFILE $*
[ $DEBUG_ON -ne 0 ] && echo "$PROJROOT/daemons/$SERVICE $PIDFILE $LOGFILE $*"
exit 0

