#!/usr/bin/env bash

source /BUILD/docker/common.sh

die () {
	python -m platform
	echo $1
	exit 1
}

cd /BUILD/docker &&
	apt-get update &&
	apt-get install -y python &&
	apt-get install -y gcc g++ wget curl pkg-config git zip unzip ||
	die "deps failed"

rm -rf lib &&
	rm -rf z3 &&
	mkdir -p lib &&
	git clone https://github.com/Z3Prover/z3.git z3 &&
	cd z3 &&
	git checkout tags/z3-${RELEASE} &&
	cd .. ||
	die "could not download z3 prover"


cd z3 &&
	python scripts/mk_make.py --prefix=/BUILD/docker &&
	cd build && make && make install || die "build failed"

