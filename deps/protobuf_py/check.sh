mkdir -p BUILD/check
protoc -I ../ --python_out=BUILD/check ../checks/protobuf_check.proto || exit 1
exit 0

