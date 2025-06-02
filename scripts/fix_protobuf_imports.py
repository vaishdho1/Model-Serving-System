#!/usr/bin/env python3
"""
Script to fix imports in generated protobuf files.
Converts 'import common_pb2' to 'from . import common_pb2' for better module resolution.
"""
import os
import re
from pathlib import Path

def fix_protobuf_imports(generated_dir):
    """Fix imports in all *_pb2.py and *_pb2_grpc.py files in the generated directory."""
    generated_path = Path(generated_dir)
    
    if not generated_path.exists():
        print(f"Generated directory {generated_dir} does not exist.")
        return
    
    # Find all *_pb2.py and *_pb2_grpc.py files
    pb2_files = list(generated_path.glob("*_pb2.py"))
    grpc_files = list(generated_path.glob("*_pb2_grpc.py"))
    all_files = pb2_files + grpc_files
    
    for pb_file in all_files:
        print(f"Processing {pb_file.name}...")
        
        # Read the file content
        with open(pb_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        
        pattern = r'^import (\w+_pb2) as (\w+)$'
        
        # Replace with relative imports
        def replace_import(match):
            module_name = match.group(1)
            alias = match.group(2)
            return f'from . import {module_name} as {alias}'
        
        # Apply the replacement
        new_content = re.sub(pattern, replace_import, content, flags=re.MULTILINE)
        
        # Only write if content changed
        if new_content != content:
            with open(pb_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  Fixed imports in {pb_file.name}")
        else:
            print(f"  No changes needed in {pb_file.name}")

if __name__ == "__main__":
    # Default to src/generated directory
    generated_dir = "src/generated"
    fix_protobuf_imports(generated_dir)
    print("Import fixing completed.") 