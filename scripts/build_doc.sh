#! /bin/sh

TOPDIR=`dirname $0`
[ "x$TOPDIR" = "x" ] && TOPDIR="."
pushd $TOPDIR 2> /dev/null 1> /dev/null
TOPDIR=`pwd`
popd 2> /dev/null 1> /dev/null
TOPDIR=`dirname $TOPDIR`

echo "Building documentation..."
mkdir -p $TOPDIR/build/doxygen
pushd $TOPDIR/pkg/doc 2> /dev/null 1> /dev/null
doxygen $TOPDIR/pkg/doc/ie.doxyfile
popd 2> /dev/null 1> /dev/null
