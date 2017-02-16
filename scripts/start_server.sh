#!/bin/bash

die () {
	echo "Error: $1"
	exit 1
}

usage() {
cat << EOF
start_server.sh [options] -c cmd [args ...]
  -d: debug, just print what will be executed.
  -S <bash script>: source this script in start_server before running cmd.

EOF
exit 0
}

# Get Lucida root path
pushd $(dirname $0) &> /dev/null
cd ..
LUCIDAROOT=`pwd`
popd &> /dev/null
RUNDIR=`pwd`

# Process command line options
SERVER_DBG=0
SERVER_SRC=
while getopts ":dS:" OPTION; do
case $OPTION in
d ) SERVER_DBG=1;;
S ) SERVER_SRC=$OPTARG;;
h ) usage;;
* ) usage;;
esac
done
shift $((OPTIND-1))   
[ "x$1" != "" ] || die "missing cmd $*"

# Check if we are running
[ -e ${RUNDIR}/run/server.pid ] && kill -0 `cat ${RUNDIR}/run/server.pid` &>/dev/null && die "stop server first"
mkdir -p ${RUNDIR}/running

[ "x$SERVER_SRC" == "x" ] || source ${SERVER_SRC} || die "cannot source $SERVER_SRC"
echo "====================================================="
echo "Running server '$*'"
echo "  To stop run stop_server.sh in the current directory"
echo "  The pid will be saved at `pwd`/run/server.pid"
[ ${SERVER_DBG} -eq 0 ] && $* &
PID="$!"
# Use RUNDIR incase source script changed working dir
[ ${SERVER_DBG} -eq 0 ] && echo "$PID" > ${RUNDIR}/run/server.pid
#wait $PID
[ ${SERVER_DBG} -ne 0 ] && echo "while kill -0 \$PID &> /dev/null; do sleep 1; done"
[ ${SERVER_DBG} -eq 0 ] && while kill -0 ${PID} &> /dev/null; do sleep 1; done
[ ${SERVER_DBG} -ne 0 ] && echo "rm -f ${RUNDIR}/run/server.pid &>/dev/null"
[ ${SERVER_DBG} -eq 0 ] && rm -f ${RUNDIR}/run/server.pid &>/dev/null
exit 0
