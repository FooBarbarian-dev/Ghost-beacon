#!/bin/bash
set -e

echo "Downloading Cobalt Strike beacon data from fox-it/cobaltstrike-beacon-data..."
mkdir -p data

# The original repository hosts large JSONL files using Git LFS, so it's
# more reliable to clone the repository directly and copy the files.
echo "Cloning fox-it/cobaltstrike-beacon-data..."
git clone --depth 1 https://github.com/fox-it/cobaltstrike-beacon-data.git /tmp/cobaltstrike-beacon-data

echo "Copying data files..."
cp /tmp/cobaltstrike-beacon-data/beacons-*.jsonl.gz ./data/

echo "Cleaning up..."
rm -rf /tmp/cobaltstrike-beacon-data

echo "Download complete! Files saved to ./data directory."
