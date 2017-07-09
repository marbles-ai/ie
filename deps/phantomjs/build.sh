[ -d BUILD ] && exit 0
mkdir -p BUILD \
	&& cp -f Dockerfile BUILD \
	&& unzip phantomjs-$RELEASE-macosx.zip -d BUILD \
	&& cp BUILD/phantomjs-2.1.1-macosx/bin/phantomjs ../../src/python/marbles/newsfeed/data/phantomjs-osx \
	|| die "unzip phantomjs"

# This release has an issue on ubuntu - we patch source for that platform.
# Once it is resolved we can go back to binary tar
# Can use this for non-ubuntu releases
tar -jxf phantomjs-$RELEASE-linux-x86_64.tar.bz2 -C BUILD
cp BUILD/phantomjs-$RELEASE-linux-x86_64/bin/phantomjs ../../src/python/marbles/newsfeed/data/phantomjs-linux

# See if we have added it to git for this release
if [ -e phantomjs-${RELEASE}-ubuntu-x86_64.tar.bz2 ]; then
	tar -jxf phantomjs-$RELEASE-ubuntu-x86_64.tar.bz2 -C BUILD
	cp BUILD/phantomjs-$RELEASE-ubuntu/bin/phantomjs ../../src/python/marbles/newsfeed/data/phantomjs-ubuntu
	exit 0
fi

echo "Building phantomjs from source will take hours so be patient"
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

cd ../ \
	&& mkdir -p phantomjs-${RELEASE}-ubuntu/bin \
	&& cp phantomjs/phantomjs phantomjs-${RELEASE}-ubuntu/bin \
	&& cp phantomjs/phantomjs ../../../src/python/marbles/newsfeed/data/phantomjs-ubuntu \
	&& tar -jcf phantomjs-${RELEASE}-ubuntu-x86_64.tar.bz2 phantomjs-${RELEASE}-ubuntu/ \
	&& mv phantomjs-${RELEASE}-ubuntu-x86_64.tar.bz2 .. \
	&& cd .. \
	|| die "tar phantomjs"

echo "To avoid another build you should git-add phantomjs-${RELEASE}-ubuntu-x86_64.tar.bz2"

