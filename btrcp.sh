#!/bin/bash

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}" )"

source $SCRIPT_DIR/btrcp-env/bin/activate
python3 $SCRIPT_DIR/BTRCP/src/btrcp.py "$@"
