[ -d BUILD ] && exit 0
mkdir -p BUILD \
	&& cp -f Dockerfile BUILD \
	&& unzip phantomjs-$RELEASE-macosx.zip -d BUILD \
	&& cp BUILD/phantomjs-2.1.1-macosx/bin/phantomjs ../../src/python/marbles/newsfeed/data/phantomjs-osx \
	|| die "unzip phantomjs"

# This release has an issue on ubuntu - we patch source for that platform.
# Once it is resolved we can go back to binary tar
#tar -jxf phantomjs-$RELEASE-linux-x86_64.tar.bz2 -C BUILD
#cp BUILD/phantomjs-$RELEASE-linux-x86_64/bin/phantomjs ../../src/python/marbles/newsfeed/data/phantomjs-linux

cd BUILD \
	&& git clone https://github.com/ariya/phantomjs.git \
	&& cd phantomjs \
	&& git checkout tags/${RELEASE} \
	|| die "git clone phantomjs"

# Patch deploy script
cp -f ../../docker-build.sh ./deploy \
	|| die "patch"

docker run -v $PWD:/src ubuntu:16.04 /src/deploy/docker-build.sh \
	|| die "phantomjs build"

