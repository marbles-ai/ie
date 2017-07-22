build_local () {
	if [ ! -d BUILD/z3 ]; then
		mkdir -p BUILD &&
			cd BUILD &&
			git clone https://github.com/Z3Prover/z3.git z3 &&
			cd z3 &&
			git checkout tags/z3-${RELEASE} &&
			cd ../.. ||
			die "could not download z3 prover"
	fi

	rm -rf BUILD/lib
	mkdir -p BUILD/lib

	if python -mplatform | grep -qi 'darwin'; then
		cd BUILD/z3 &&
			CXX=clang++ CC=clang python scripts/mk_make.py --prefix=$BUILDPATH/BUILD &&
				cd build && make && make install || die "build failed"
	else
		cd BUILD/z3 &&
			python scripts/mk_make.py --prefix=$BUILDPATH/BUILD &&
				cd build && make && make install || die "build failed"
	fi
}

build_in_docker () {
	echo "Building Ubuntu Z3"
	cd $BUILDPATH &&
		mkdir -p BUILD/docker &&
		mkdir -p $ROOTPATH/../src/python/marbles/ie/semantics/lib &&
		cp -f docker-build.sh BUILD/docker &&
		cp -f common.sh BUILD/docker &&
		cp -f $ROOTPATH/pkg-installer.py BUILD/docker &&
		cp -f $ROOTPATH/linux_pkg_deps.conf BUILD/docker &&
		docker run -v $PWD/BUILD:/BUILD ubuntu:16.04 /BUILD/docker/docker-build.sh &&
		cp $BUILDPATH/BUILD/docker/lib/* $ROOTPATH/../src/python/marbles/ie/semantics/lib ||
		die "z3 docker build"
}

if python -mplatform | grep -qi 'darwin'; then
	# Latest version is in homebrew
	echo "Darwin version of z3 installed by homebrew"
else
	build_local
fi
build_in_docker
