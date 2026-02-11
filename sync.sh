#!/bin/bash
set -euo pipefail

#rsync -viah --info=progress2 --stats --delete --delete-excluded --exclude='.git' ./ pi:quesys/
# DONT DELETE THE DATABASE!!
rsync -viah --info=progress2 --stats --exclude='.git' ./ pi:quesys/
