#!/bin/bash
set -e

echo "Downloading Cobalt Strike beacon data from fox-it/cobaltstrike-beacon-data..."
mkdir -p data

base_url="https://github.com/fox-it/cobaltstrike-beacon-data/raw/refs/heads/main/"

# The original repository provides beacons separated by year
for year in 2018 2019 2020 2021 2022; do
  echo "Downloading beacons-$year.jsonl.gz..."
  curl -sL -o data/beacons-$year.jsonl.gz "$base_url/beacons-$year.jsonl.gz"
done

echo "Download complete! Files saved to ./data directory."
