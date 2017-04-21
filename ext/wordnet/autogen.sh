#!/bin/sh

aclocal
autoheader
autoconf -f
# Why would I give a damn about supporting AM 1.6
# no-portability - bring it on
automake -a -c -Wno-portability
