#!/bin/bash
set -e

# Directory containing .proto files
PROTO_DIR="src/protos"
# Output directory for generated Python files
GENERATED_DIR="src/generated"

# --- Detect Python environment (virtual env or system) ---
# Check if a virtual environment is active
if [ -n "$VIRTUAL_ENV" ]; then
    echo "Using Python from virtual environment: $VIRTUAL_ENV"
    PYTHON_EXEC="$VIRTUAL_ENV/bin/python"
else
    echo "No virtual environment detected. Using system Python."
    # Try python3 first, then python
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_EXEC="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_EXEC="python"
    else
        echo "ERROR: No Python executable found. Please install Python."
        exit 1
    fi
fi

echo "Using Python executable: $PYTHON_EXEC"


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