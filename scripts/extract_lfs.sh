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
popd

[ -e ${PROJROOT}/ext/easyccg/model/model_questions.tar.gz ] || die "Missing model_questions.tar.gz"
[ -e ${PROJROOT}/ext/easyccg/model/model.tar.gz ] || die "Missing model.tar.gz"
[ -e ${PROJROOT}/ext/easyccg/model/model_rebank.tar.gz ] || die "Missing model_rebank.tar.gz"

pushd ${PROJROOT}/ext/easyccg/model
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

if [ ! -e ./rebank/categories ]; then
	rm -rf rebank
	tar -zxf model_rebank.tar.gz
	mv model_rebank rebank
fi
popd

[ -e ${PROJROOT}/data/LDC2005T13.tgz ] || die "Missing LDC2005T13.tgz"
mkdir -p ${PROJROOT}/data/ldc
pushd ${PROJROOT}/data/ldc
if [ ! -d ./ccgbank_1_1 ]; then
	tar -zxf ../LDC2005T13.tgz
fi
popd
