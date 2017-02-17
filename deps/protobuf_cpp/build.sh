[ "x`which protoc`" == "x" ] && die "protoc not installed"
CPP_TARGZ="https://github.com/google/protobuf/releases/download/v$RELEASE/protobuf-cpp-${RELEASE}.tar.gz"
mkdir -p BUILD
cd BUILD

[ -e protobuf-cpp-${RELEASE}.tar.gz ] || \
	wget $CPP_TARGZ || die "cannot download cpp protobuf bindings"

[ -d protobuf-$RELEASE ] || \
	tar -zxf protobuf-cpp-${RELEASE}.tar.gz || die "cannot untar cpp protobuf"

cd protobuf-$RELEASE || \
	die "cannot build cpp protobuf bindings"
[ -e config.log ] || ./configure --with-protoc=`which protoc` || \
		die "cannot build cpp protobuf bindings"
make && cd ../../ || die "cannot build cpp protobuf bindings"
