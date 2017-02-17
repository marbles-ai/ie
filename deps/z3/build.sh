if [ "x$THREADS" == "x" ]; then
	THREADS = 4
fi

if [ ! -d BUILD/z3 ]; then
	mkdir -p BUILD &&
		cd BUILD &&
		git clone https://github.com/Z3Prover/z3.git z3 &&
		cd z3 &&
		cd ../../ ||
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
