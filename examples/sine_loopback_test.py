"""End-to-end test of the two TCP/IP instruments.

Outputs a sine from the Agilent 33220A, measures it on channel 4 of the
Siglent scope, and checks that what comes back matches what was commanded.

    python examples/sine_loopback_test.py

Needs a cable from the generator's OUTPUT to scope channel 4. No power
supply is touched. Exits non-zero if any check fails.
"""

import sys
from pathlib import Path
from time import sleep

# Running a file by path puts this directory on sys.path, not the project
# root, so add the root before importing bench.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import Bench  # noqa: E402 — must follow the sys.path line above

FREQ_HZ = 500.0
VPP = 2.0
CHANNEL = 4

FREQ_TOL = 0.02   # 2 % — both instruments are crystal-referenced
VPP_TOL = 0.15    # 15 % — scope amplitude accuracy at 0.5 V/div, plus cabling
PLOT = 'sine_loopback.png'

results = []


def check(label, measured, expected, tol, unit=''):
    """Record a pass/fail against an expected value and print the line."""
    if measured is None:
        results.append(False)
        print(f'FAIL  {label}: no measurement (is the cable connected?)')
        return

    error = abs(measured - expected) / expected
    ok = error <= tol
    results.append(ok)
    print(f'{"PASS" if ok else "FAIL"}  {label}: {measured:g}{unit} '
          f'(expected {expected:g}{unit}, off by {error:.1%}, tol {tol:.0%})')


with Bench() as b:
    funcgen = b.funcgen.agilent
    scope = b.scope.sds1104x

    print('Function generator:', funcgen.idn())
    print('Scope:             ', scope.idn())
    print()

    # --- source: a plain sine, high-Z so the amplitude is what we asked for ---
    funcgen.reset()
    sleep(1)
    funcgen.set_load('INF')
    funcgen.set_sine(FREQ_HZ, amplitude_vpp=VPP)
    funcgen.output_on()

    # --- scope: enough vertical room for 2 Vpp, ~7 cycles across the screen ---
    scope.enable_channel(CHANNEL)
    scope.set_vertical_scale(CHANNEL, VPP / 4)   # 0.5 V/div -> 4 V full scale
    scope.set_vertical_offset(CHANNEL, 0)
    scope.set_timebase(1 / FREQ_HZ / 2)          # 1 ms/div at 500 Hz
    scope.set_trigger_source(CHANNEL)
    scope.set_trigger_level(CHANNEL, 0)
    scope.run()
    sleep(2)                                     # let the measurements settle

    # --- what the generator thinks it is doing ---
    settings = funcgen.settings()
    print('Generator settings:', settings)
    check('generator frequency', settings['freq_hz'], FREQ_HZ, 0.001, ' Hz')
    check('generator amplitude', settings['amplitude_vpp'], VPP, 0.001, ' Vpp')
    print()

    # --- what the scope actually sees ---
    measured = scope.measure_all(CHANNEL)
    print(f'Scope channel {CHANNEL}:', measured)
    check('measured frequency', measured['freq_hz'], FREQ_HZ, FREQ_TOL, ' Hz')
    check('measured period', measured['period_s'], 1 / FREQ_HZ, FREQ_TOL, ' s')
    check('measured Vpp', measured['vpp'], VPP, VPP_TOL, ' V')
    print()

    # --- and the raw samples, as a cross-check on the scope's own maths ---
    path, t, v = scope.plot_waveform(CHANNEL, path=PLOT)
    span = float(t[-1] - t[0])
    raw_vpp = float(v.max() - v.min())
    print(f'Captured {len(v)} points over {span:.6f} s '
          f'(~{span * FREQ_HZ:.1f} cycles), Vpp from samples {raw_vpp:.4f} V')
    check('raw-sample Vpp', raw_vpp, VPP, VPP_TOL, ' V')
    print(f'      plot written to {path} — open it to confirm by eye')

    funcgen.output_off()

print()
failed = results.count(False)
print(f'{len(results) - failed}/{len(results)} checks passed')
sys.exit(1 if failed else 0)
