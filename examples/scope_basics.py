"""Exercise the basic scope calls: set a channel up, measure it, capture it.

Whatever is on the channel gets measured — with nothing connected you'll see
a few tens of mV of noise and no valid frequency, which is a fine smoke test
of the plumbing. Feed it a signal for interesting numbers.

    python examples/scope_basics.py

Set ``SCOPE`` to whichever scope is plugged in; `python -m bench list` shows
the names. The capture is decimated to keep memory small — see
``SiglentSDS1104XE.MAX_POINTS``.
"""

import sys
from pathlib import Path
from time import sleep

# Running a file by path puts this directory on sys.path, not the project
# root, so add the root before importing bench.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import Bench  # noqa: E402 — must follow the sys.path line above

SCOPE = 'sds1104x_usb'   # or 'sds1104x' for the LAN scope
CHANNEL = 4

with Bench() as b:
    scope = b.scope[SCOPE]
    print('scope:', scope.idn())

    # --- set the channel up ---
    scope.enable_channel(CHANNEL)
    scope.set_vertical_scale(CHANNEL, 0.5)     # 0.5 V/div
    scope.set_vertical_offset(CHANNEL, 0)
    scope.set_timebase(1e-3)                   # 1 ms/div
    scope.set_trigger_source(CHANNEL)
    scope.set_trigger_level(CHANNEL, 0)
    scope.run()
    sleep(2)                                   # let the measurements settle

    # --- read the settings back ---
    print(f'  {scope.get_vertical_scale(CHANNEL)} V/div, '
          f'offset {scope.get_vertical_offset(CHANNEL)} V, '
          f'{scope.sample_rate() / 1e6:.0f} MSa/s')

    # --- scalar measurements (None means the scope can't measure it) ---
    for name, value in scope.measure_all(CHANNEL).items():
        print(f'  {name}: {value}')

    # --- one capture, reused for both outputs ---
    t, v = scope.get_waveform(CHANNEL)
    print(f'  captured {len(v)} points over {t[-1] - t[0]:.6f} s, '
          f'Vpp {v.max() - v.min():.4f} V')

    print(' ', scope.save_waveform(CHANNEL, 'scope_basics.csv', data=(t, v)))
    print(' ', scope.plot_waveform(CHANNEL, 'scope_basics.png', data=(t, v))[0])

    scope.stop()
