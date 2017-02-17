#! /bin/bash

die () {
	echo "Error: $1"
	exit 1
}

# Get project root absolute path
pushd $(dirname $0) &> /dev/null
cd ..
PROJROOT=`pwd`
popd &> /dev/null

[ -e ${PROJROOT}/ext/easysrl/model/model_questions.tar.gz ] || die "Missing model_questions.tar.gz"
[ -e ${PROJROOT}/ext/easysrl/model/model.tar.gz ] || die "Missing model.tar.gz"

pushd ${PROJROOT}/ext/easysrl/model

if [ ! -e ./questions/categories ]; then
	rm -rf questions
	tar -zxf model_questions.tar.gz
	mv model_questions questions
fi

if [ ! -e ./text/categories ]; then
	rm -rf text
	tar -zxf model.tar.gz
	mv model text
fi
