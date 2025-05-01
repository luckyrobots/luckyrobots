#!/bin/bash

rm -rf dist
rm -rf build
rm -rf src/luckyrobots.egg-info

# Read the current version from pyproject.toml
current_version=$(grep -E 'version\s*=\s*"[^"]+"' pyproject.toml | head -1 | sed 's/.*version\s*=\s*"\([^"]*\)".*/\1/')

if [ -z "$current_version" ]; then
    echo "Error: Could not find version in pyproject.toml"
    exit 1
fi

# Split the version into parts
IFS='.' read -ra version_parts <<< "$current_version"

# Increment the last part
last_part=$((${version_parts[2]} + 1))

# Construct the new version
new_version="${version_parts[0]}.${version_parts[1]}.$last_part"

# Update the version in pyproject.toml
sed -i.bak "s/version\s*=\s*\"$current_version\"/version = \"$new_version\"/" pyproject.toml && rm pyproject.toml.bak

echo "Version updated from $current_version to $new_version"

# Build and upload
python -m pip install --upgrade build
python -m build
python -m pip install --upgrade twine
python -m twine upload dist/*
