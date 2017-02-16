#!/bin/bash

EXTPATH="$(dirname $0)/.."
PROJPATH="$EXTPATH/.."
ESRLPATH="$EXTPATH/easysrl"
VERSION="0.1.0"

die () {
	echo "Error: $1"
	exit 1
}

[ -e ${ESRLPATH}/build/libs/easysrl-${VERSION}.jar ] || die "$ESRLPATH/build/libs/easysrl-$VERSION.jar missing, run gradle build"
[ -e ${PROJPATH}/build/libs/ie-${VERSION}.jar ] || die "$PROJPATH/build/libs/ie-$VERSION.jar missing, run gradle build"

java -jar ${ESRLPATH}/build/libs/easysrl-0.1.0-standalone.jar --model /Users/paul/EasySRL/model/text --daemon
