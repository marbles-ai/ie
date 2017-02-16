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
[ -e ${EXTPATH}/build/libs/ext-${VERSION}.jar ] || die "$EXTPATH/build/libs/ext-$VERSION.jar missing, run gradle build"

java -Djava.library.path=${ESRLPATH}/lib -classpath ${ESRLPATH}/build/libs/easysrl-0.1.0.jar:${PROJPATH}/build/libs/ie-${VERSION}.jar:${EXTPATH}/build/libs/ext-${VERSION}.jar ai.marbles.easysrl.EasySRLDaemon
