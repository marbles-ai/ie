#!/bin/sh
#
# Usage build-tool.sh <project> <action>
# See Makefile for details on how to add local build dependencies.
#
# Copyright (c) 2016, Paul Glendenning
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# (1) Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
# (2) Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
# (3) Neither the name of the author nor the names of other contributors may be
#     used to endorse or promote products derived from this software without
#     specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

die () {
	[ "x$1" == "x" ] || echo "Error: build-action=$ACTION - $1"
	exit 1
}

abspath () {
	if [ "x$1" == "x" ]; then
		pwd
	else
		pushd "$1" 2>/dev/null >/dev/null
		pwd
		popd 2>/dev/null >/dev/null
	fi
}

ROOTPATH="$(abspath $(dirname $0))"
SCRIPTNAME="$(basename $0)"
# Remove trailing / from 1st arg
BUILDPATH="$ROOTPATH/`echo $1 | sed 's/\/$//g'`"
ACTION="$2.sh"

[ "x$1" == "x" ] && die "$SCRIPTNAME expects a project name(1) - $1"
[ "x$2" == "x" ] && die "$SCRIPTNAME expects an action"

if [ -e $BUILDPATH/common.sh ]; then
	echo "Loading $BUILDPATH/common.sh"
	pushd $BUILDPATH >/dev/null
	source ./common.sh
	popd >/dev/null
fi

if [ -e $BUILDPATH/$ACTION ]; then
	echo "Executing action $BUILDPATH/$ACTION"
	cd $BUILDPATH
	[ "x$ACTION" == "xclean.sh" ] || set -v
	source ./$ACTION
fi

