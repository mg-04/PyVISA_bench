"""Exercise the basic function generator calls and read each one back.

Nothing needs to be connected to the output — every value is confirmed by
asking the generator what it thinks it is doing.

    python examples/funcgen_basics.py
"""

import sys
from pathlib import Path
from time import sleep

# Running a file by path puts this directory on sys.path, not the project
# root, so add the root before importing bench.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import Bench  # noqa: E402 — must follow the sys.path line above

with Bench() as b:
    funcgen = b.funcgen.agilent
    print('funcgen:', funcgen.idn())

    funcgen.reset()
    sleep(1)
    funcgen.set_load('INF')        # high-Z, or the amplitude reads half

    # --- a sine, set in one shot ---
    funcgen.set_sine(500, amplitude_vpp=2.0, offset_v=0.0)
    funcgen.output_on()
    print('sine: ', funcgen.settings())

    # --- change one parameter at a time ---
    funcgen.set_frequency(1000)
    funcgen.set_amplitude(1.5)
    funcgen.set_offset(0.25)
    print(f'  freq     {funcgen.get_frequency():.1f} Hz')
    print(f'  amplitude {funcgen.get_amplitude():.3f} Vpp')
    print(f'  offset   {funcgen.get_offset():.3f} V')

    # --- other waveforms ---
    funcgen.set_square(2000, amplitude_vpp=1.0)
    funcgen.set_duty_cycle(25)
    print('square:', funcgen.settings())

    funcgen.set_ramp(100, amplitude_vpp=1.0)
    print('ramp:  ', funcgen.settings())

    funcgen.output_off()
    print('output off:', funcgen.output_state())
