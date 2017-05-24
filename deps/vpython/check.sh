#@IgnoreInspection BashAddShebang
[ -d $BUILDPATH/ENV/V`echo "$PYTHON_VERSION" | sed 's/\./_/g'` ] || exit 1
exit 0

