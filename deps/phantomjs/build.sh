[ -d BUILD ] && exit 0
RELEASE=2.1.1
mkdir -p BUILD
unzip phantomjs-$RELEASE-macosx.zip -d BUILD
cp BUILD/phantomjs-2.1.1-macosx/bin/phantomjs ../../src/python/marbles/newsfeed/data/phantomjs-osx
tar -jxf phantomjs-$RELEASE-linux-x86_64.tar.bz2 -C BUILD
cp BUILD/phantomjs-$RELEASE-linux-x86_64/bin/phantomjs ../../src/python/marbles/newsfeed/data/phantomjs-linux
