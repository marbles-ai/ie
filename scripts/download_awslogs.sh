#!/usr/bin/env bash

die () {
    usage "$SCRIPTNAME [copypath [copy path...]]"
	echo "Error: $1"
	exit 1
}

# Get project root absolute path
SCRIPTNAME=$(basename $0)
pushd $(dirname $0) &> /dev/null
cd ..
PROJROOT=`pwd`
popd &> /dev/null

mkdir -p ${PROJROOT}/build/awslogs_download
pushd ${PROJROOT}/build/awslogs_download > /dev/null

FILES="awslogs-agent-setup.py AgentDependencies.tar.gz"

for i in $FILES; do
	[ -e $i ] || curl https://s3.amazonaws.com//aws-cloudwatch/downloads/latest/$i -O || die "download $i"
done

popd > /dev/null

while [ "x$1" != "x" ]; do
    cp ${PROJROOT}/build/awslogs_download/* $1 || die "copying to $1"
    shift
done
