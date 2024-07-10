#!/bin/bash

rm -rf dist
rm -rf build
rm -rf src/luckyrobots.egg-info

# Read the current version from setup.py
current_version=$(grep -E 'version="[^"]+"' setup.py | sed 's/.*version="\([^"]*\)".*/\1/')

if [ -z "$current_version" ]; then
    echo "Error: Could not find version in setup.py"
    exit 1
fi

# Split the version into parts
IFS='.' read -ra version_parts <<< "$current_version"

# Increment the last part
last_part=$((${version_parts[2]} + 1))

# Construct the new version
new_version="${version_parts[0]}.${version_parts[1]}.$last_part"

# Update the version in setup.py
sed -i.bak "s/version=\"$current_version\"/version=\"$new_version\"/" setup.py && rm setup.py.bak

echo "Version updated from $current_version to $new_version"

# Uncomment the following lines when ready to build and upload
python3.11 -m pip install --upgrade build
python3.11 -m build
python3.11 -m pip install --upgrade twine
python3.11 -m twine upload dist/*