if python -mplatform | grep -qi 'darwin'; then
	[ -e BUILD/lib/libz3.dylib ] || exit 1
else
	[ -e BUILD/lib/libz3.so ] || exit 1
fi
exit 0
