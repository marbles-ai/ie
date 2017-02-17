die () {
	echo "Error: $1"
	exit 1
}

create_logfile_name() {
	echo "${1}_`date +'%Y-%m-%d_%H-%M'`.log"
}

# Get project root absolute path
pushd `dirname $0` 2>/dev/null >/dev/null
cd ..
PROJROOT=`pwd`
popd 2>/dev/null 1>/dev/null

