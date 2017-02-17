mkdir -p BUILD
cd BUILD
if python -mplatform | grep -i darwin; then
	[ ! -e protoc-$RELEASE-osx-x86_64.zip ] && \
		wget https://github.com/google/protobuf/releases/download/v$RELEASE/protoc-$RELEASE-osx-x86_64.zip || \
		die "cannot download protoc binary"
elif python -mplatform | grep -i 'ubuntu\|debian\|redhat\|centos'; then
	[ ! -e protoc-$RELEASE-linux-x86_64.zip ] && \
		wget https://github.com/google/protobuf/releases/download/v$RELEASE/protoc-$RELEASE-linux-x86_64.zip || \
		die "cannot download protoc binary"
else
	die "unsupported platform"
fi
cd ..
