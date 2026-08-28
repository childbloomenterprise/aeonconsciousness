#!/usr/bin/env bash
set -u

cd /home/vaish/aeon-runtime

for config in \
  configs/aeon-world.hazard-water.json \
  configs/aeon-world.hazard-fire.json \
  configs/aeon-world.hazard-energy.json
do
  /home/vaish/.venvs/aeon/bin/python -m aeon_world --env-file .env run --config "$config" || exit $?
done
