mkdir -p BUILD
cd BUILD
if [ ! -d grpc-$RELEASE ]; then
	git clone https://github.com/grpc/grpc grpc-$RELEASE && \
		cd grpc-$RELEASE && \
		git checkout tags/v$RELEASE && \
		git submodule update --init || \
		die "git grpc failed"
	cd ..
fi

cd grpc-$RELEASE
if python -mplatform | grep -i darwin; then
	LDFLAGS="-L/usr/local/opt/openssl/lib" CPPFLAGS="-I/usr/local/opt/openssl/include" \
		PKG_CONFIG_PATH="/usr/local/opt/openssl/lib/pkgconfig" make || die "grpc build failed"
else
	make || die "grpc build failed"
fi
cd ../..
