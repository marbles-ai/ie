WHGIT="https://github.com/Webhose/webhoseio-python.git"
[ -d BUILD ] || \
	git clone $WHGIT BUILD || die "cannot download webhoseio python client"

cd BUILD && python setup.py install || \
	die "cannot install webhoseio python client"
