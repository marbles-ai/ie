cd BUILD/protobuf-$RELEASE || die "not built"
make install && cd ../.. || die "install failed"

