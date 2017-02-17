mkdir -p BUILD/check
protoc -I ../ --cpp_out=BUILD/check ../checks/protobuf_check.proto || exit 1
protoc -I ../ --cpp_out=BUILD/check ../checks/protobuf3_check.proto || exit 1
exit 0
