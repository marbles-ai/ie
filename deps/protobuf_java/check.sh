mkdir -p BUILD/check
protoc -I ../ --java_out=BUILD/check ../checks/protobuf_check.proto || exit 1
exit 0

