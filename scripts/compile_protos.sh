#!/bin/bash
set -e

# Directory containing .proto files
PROTO_DIR="src/protos"
# Output directory for generated Python files
GENERATED_DIR="src/generated"

# --- FIX: Ensure we use the Python from the virtual environment ---
# Check if a virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "ERROR: No virtual environment is active. Please run 'source myenv/bin/activate' first."
    exit 1
fi
# Use the python from the active VIRTUAL_ENV path
PYTHON_EXEC="$VIRTUAL_ENV/bin/python"


# Create the output directory if it doesn't exist
mkdir -p "${GENERATED_DIR}"

# Find all .proto files and compile them
find "${PROTO_DIR}" -name "*.proto" -print0 | while IFS= read -r -d $'\0' proto_file; do
  echo "Compiling ${proto_file}..."
  # --- FIX: Use the explicit python path ---
  "$PYTHON_EXEC" -m grpc_tools.protoc \
    -I"${PROTO_DIR}" \
    --python_out="${GENERATED_DIR}" \
    --grpc_python_out="${GENERATED_DIR}" \
    "${proto_file}"
done

echo "Protobuf compilation finished."

# Create __init__.py files
touch "${GENERATED_DIR}/__init__.py"
echo "Created __init__.py in ${GENERATED_DIR}."

# Fix imports
echo "Fixing protobuf imports..."
# --- FIX: Use the explicit python path ---
"$PYTHON_EXEC" scripts/fix_protobuf_imports.py

echo "Protobuf compilation and import fixing completed."