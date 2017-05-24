#@IgnoreInspection BashAddShebang
PYVER="${PYTHON_VERSION}.${PYTHON_BUILD}"
mkdir -p BUILD &&
	cd BUILD ||
	die "directory access"

[ -e Python-${PYVER}.tgz ] || 
	wget http://www.python.org/ftp/python/${PYVER}/Python-${PYVER}.tgz ||
	die "could not download python $PYVER"

LOCALPY=V`echo "$PYTHON_VERSION" | sed 's/\./_/g'`

[ -d Python-${PYVER} ] ||
	tar -zxf Python-${PYVER}.tgz ||
	die "untar python $PYVER"

mkdir -p $BUILDPATH/ENV/$LOCALPY &&
	cd Python-$PYVER &&
	./configure --prefix=$BUILDPATH/ENV/$LOCALPY &&
	make &&
	make install ||
	die "build failed"

cd $BUILDPATH/ENV &&
	virtualenv vpython -p $LOCALPY/bin/python${PYTHON_VERSION} ||
	die "cannot enter python virtualenv"

source vpython/bin/activate
pip install --upgrade distribute
pip install --upgrade pip
pip install -r $BUILDPATH/python_requirements.txt
pip install --upgrade numpy
python -m nltk.downloader 'averaged_perceptron_tagger'
pip install pywsd
deactivate
