[ "x`which protoc`" == "x" ] && die "protoc not installed"
PYTHON_TARGZ="https://github.com/google/protobuf/releases/download/v$RELEASE/protobuf-python-${RELEASE}.tar.gz"
mkdir -p BUILD
cd BUILD

[ -e protobuf-python-${RELEASE}.tar.gz ] || \
	wget $PYTHON_TARGZ || die "cannot download python protobuf bindings"

[ -d protobuf-$RELEASE ] || \
	tar -zxf protobuf-python-${RELEASE}.tar.gz || die "cannot untar python protobuf"

cd protobuf-$RELEASE || \
	die "cannot build python protobuf bindings"
[ -e config.log ] || ./configure --with-protoc=`which protoc` || \
		die "cannot build python protobuf bindings"
make && cd ../../ || die "cannot build python protobuf bindings"
