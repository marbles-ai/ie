cd BUILD || die "no build directory"
if python -mplatform | grep -i darwin; then
	unzip -o -d /usr/local protoc-$RELEASE-osx-x86_64.zip || die "install failed"
elif python -mplatform | grep -i 'ubuntu\|debian\|redhat\|centos'; then
	unzip -o -d /usr/local protoc-$RELEASE-linux-x86_64.zip || die "install failed"
	#tar -zxf protoc-$RELEASE-linux-x86_64.tar.gz || die "install failed"
else
	die "unsupported platform"
fi
# On linux permissions were set incorrectly
chmod -R o+r /usr/local/include/google/protobuf
chmod o+rx /usr/local/bin/protoc
cd ..
