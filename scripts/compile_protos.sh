#!/bin/bash

# Directory containing .proto files
PROTO_DIR="src/protos"
# Output directory for generated Python files
GENERATED_DIR="src/generated"

# Create the output directory if it doesn't exist
mkdir -p "${GENERATED_DIR}"

# Find all .proto files and compile them
find "${PROTO_DIR}" -name "*.proto" -print0 | while IFS= read -r -d $'\0' proto_file; do
  echo "Compiling ${proto_file}..."
  python -m grpc_tools.protoc \
    -I"${PROTO_DIR}" \
    --python_out="${GENERATED_DIR}" \
    --grpc_python_out="${GENERATED_DIR}" \
    "${proto_file}"
done

echo "Protobuf compilation finished."

# Create __init__.py files if they don't exist, to make the generated directory a package
touch "${GENERATED_DIR}/__init__.py"

echo "Created __init__.py in ${GENERATED_DIR}."

# Fix imports in generated files
echo "Fixing protobuf imports..."
python scripts/fix_protobuf_imports.py

echo "Protobuf compilation and import fixing completed." 