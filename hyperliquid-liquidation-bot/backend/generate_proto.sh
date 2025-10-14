#!/bin/bash

# Generate Python code from protobuf definition
python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    hyperliquid.proto

echo "✅ Protobuf files generated successfully!"
