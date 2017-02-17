[ "x`which protoc`" == "x" ] && die "protoc not installed"
JAVA_TARGZ="https://github.com/google/protobuf/releases/download/v$RELEASE/protobuf-java-${RELEASE}.tar.gz"
mkdir -p BUILD
cd BUILD

[ -e protobuf-java-${RELEASE}.tar.gz ] || \
	wget $JAVA_TARGZ || die "cannot download java protobuf bindings"

[ -d protobuf-$RELEASE ] || \
	tar -zxf protobuf-java-${RELEASE}.tar.gz || die "cannot untar java protobuf"

cd protobuf-$RELEASE || \
	die "cannot build java protobuf bindings"
[ -e config.log ] || ./configure --with-protoc=`which protoc` || \
		die "cannot build java protobuf bindings"
make && cd ../../ || die "cannot build java protobuf bindings"
