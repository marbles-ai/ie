[ "x`which protoc`" == "x" ] && exit 1
protoc --version | grep -iq '.*3.[0-9]' || exit 1
exit 0
