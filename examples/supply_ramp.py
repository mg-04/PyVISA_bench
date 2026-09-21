"""Bring a rail up to 3.3 V, measure it, and bring it back down.

The same code drives any supply on the bench — a single-output Keithley and a
three-output Keysight take identical calls, because the channel is a keyword
that defaults to 1. Change ``SUPPLY`` / ``CHANNEL`` and nothing else moves.

    python3 examples/supply_ramp.py

This one does enable a supply output.
"""

import sys
from pathlib import Path
from time import sleep

# Running a file by path puts this directory on sys.path, not the project
# root, so add the root before importing bench.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import Bench  # noqa: E402 — must follow the sys.path line above

SUPPLY = 'keysight'   # or 'keysight', or 'spd'
CHANNEL = 1
VOLTS = 1
CURRENT_LIMIT = 0.5

with Bench() as b:
    supply = b.supply[SUPPLY]
    print(f'{SUPPLY}:', supply.idn())

    supply.reset()
    sleep(1)

    supply.configure(VOLTS, CURRENT_LIMIT, channel=CHANNEL)
    supply.output_on(channel=CHANNEL)
    sleep(2)

    reading = supply.measure_all(channel=CHANNEL)
    print(f"  {reading['voltage_v']:.4f} V, {reading['current_a']:.4f} A")

    supply.all_off()
