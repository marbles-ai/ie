[ -d BUILD ] && exit 0
RELEASE=2.1.1
mkdir -p BUILD
if python -mplatform | grep -qi 'darwin'; then
	unzip phantomjs-$RELEASE-macosx.zip -d BUILD
	cp BUILD/phantomjs-2.1.1-macosx/bin/phantomjs ../../src/python/marbles/newsfeed/data
else
	tar -jxf phantomjs-$RELEASE-linux-x86_64.tar.bz2 -C BUILD 
	cp BUILD/phantomjs-$RELEASE-linux-x86_64/bin/phantomjs ../../src/python/marbles/newsfeed/data
fi
