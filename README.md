# Bench instrument control on the PYNQ board

The `bench` package puts every instrument on this bench — scopes, function
generator, power supplies — behind one interface, over USB or TCP/IP.

- [Folder structure](#folder-structure)
- [Setup](#setup)
- [Registering a USB instrument](#registering-a-usb-instrument)
- [Examples](#examples)
- [Adding an instrument](#adding-an-instrument)

---

## Folder structure

```
ming/
├── bench/                      the package — one interface to every instrument
│   ├── __init__.py             Bench, Category, the REGISTRY, re-exports
│   ├── core.py                 Instrument base: lazy connect, SCPI helpers,
│   │                           *IDN?/*RST, context manager
│   ├── categories.py           Scope, FunctionGenerator, PowerSupply —
│   │                           the per-category interface + shared behaviour
│   ├── scopes.py               SiglentSDS1104XE
│   ├── funcgens.py             Agilent33220A
│   ├── supplies.py             Keithley2280S, KeysightEDU36311A, SiglentSPD3000
│   ├── discovery.py            scan() / discover() — what's on the bus
│   ├── cli.py                  the `python3 -m bench` front end
│   └── __main__.py             entry point for `python3 -m bench`
├── examples/                   runnable end-to-end sequences
│   ├── funcgen_basics.py       set waveforms and read every setting back
│   ├── scope_basics.py         set a channel up, measure it, capture it
│   ├── supply_ramp.py          bring a rail up to 3.3 V, measure, bring it down
│   └── sine_loopback_test.py   generator -> scope ch4, self-checking
├── legacy/                     the original standalone scripts, kept for reference
│   ├── diagnose.py             → bench/discovery.py
│   ├── funcgen.py              → bench/funcgens.py
│   ├── hello.py                → bench/supplies.py (SiglentSPD3000)
│   ├── osc.py                  → bench/scopes.py
│   ├── osc_save.py             → bench/scopes.py (waveform capture)
│   ├── osc_test.py             → `python3 -m bench check`
│   ├── supply.py               → bench/supplies.py (Keithley2280S)
│   └── supply_ks.py            → bench/supplies.py (KeysightEDU36311A)
├── pynq-visa-env/              virtualenv (pyvisa, pyvisa-py, numpy, matplotlib)
└── README.md
```

**Three layers:** `Instrument` (VISA plumbing) → a category class (what a
scope / generator / supply promises) → a model class (one manufacturer's
SCPI dialect).

That split is what keeps models interchangeable. A category holds everything
that can be written once — `Scope.measure_all()`, `save_waveform()`,
`plot_waveform()`, `FunctionGenerator.settings()`, and for supplies the whole
`VOLT` / `CURR` / `OUTP` vocabulary. A model class carries only its own
dialect: how a channel is selected (`INST:NSEL n` vs `INST:SEL OUTn` vs
nothing), that the SPD3000 spells its current limit `CURRENT`, and how
measurements come back. That's why `SiglentSPD3000` is 20 lines.

---

## Setup

### Python

`python3` on this board is the PYNQ virtualenv
(`/usr/local/share/pynq-venv/bin/python3`) and already has everything needed
— pyvisa 1.16.2, numpy 1.21.5, matplotlib 3.5.1. No activation, no install:

```bash
cd /home/xilinx/ming
python3 -m bench list
```

The project's own `pynq-visa-env/` works equally well if you prefer it
(`./pynq-visa-env/bin/python -m bench list`); every command below is
interchangeable between the two.

Run `python3 -m bench ...` from the project root, since that's how the
`bench` package gets found. The scripts in `examples/` add the project root
to `sys.path` themselves, so those run from anywhere by plain path.

> The first run that draws a plot spends a few minutes building matplotlib's
> font cache. It's a one-time cost.

### Memory

This board has ~2 GB of RAM with only a few hundred MB typically free, so
waveform captures need care. A full scope record is up to 14 M samples; as
float64 that's 112 MB per array, and the scaling arithmetic needs several at
once — enough to exhaust memory, thrash swap, and get processes killed
(including your SSH session).

`get_waveform()` therefore decimates the raw int8 data *before* expanding it
to float, returning at most `SiglentSDS1104XE.MAX_POINTS` (200 k) samples
while still spanning the full capture window. A full-span capture costs about
3 MB instead of 224 MB. Raise or remove the cap deliberately if you need it:

```python
t, v = scope.get_waveform(4)                    # 200 k points, whole window
t, v = scope.get_waveform(4, max_points=5000)   # coarser, whole window
t, v = scope.get_waveform(4, points=1000)       # first 1000 samples only (1 µs)
t, v = scope.get_waveform(4, max_points=0)      # every sample — watch memory
```

`save_waveform()` and `plot_waveform()` pull their own capture unless you
hand them one with `data=(t, v)`; pass it when you want both from a single
acquisition.

### Instrument names

Every instrument is addressed as **`<category>.<model>`** — the category says
what kind of thing it is, the model says which machine:

| Category | Models |
|---|---|
| `scope` | `sds1104x` (LAN), `sds1104x_usb` |
| `funcgen` | `agilent` |
| `supply` | `keithley`, `keysight`, `spd` |

### Known instruments on this bench

| Instrument | `bench` name | Interface | Resource string | idVendor:idProduct |
|---|---|---|---|---|
| Siglent SDS1104X-E (scope #1) | `scope.sds1104x` | TCP/IP | `TCPIP::172.24.58.184::INSTR` | — |
| Siglent SDS1104X-E (scope #2) | `scope.sds1104x_usb` | USB | `USB0::62700::60984::SDSMMEBQ4R5170::0::INSTR` | — |
| Agilent 33220A (function gen) | `funcgen.agilent` | TCP/IP | `TCPIP::172.24.58.190::INSTR` | — |
| Siglent SPD3000 (power supply) | `supply.spd` | USB | `USB0::1155::30016::SPD3XHCD3R4649::0::INSTR` | 0483:7540 |
| Keithley 2280S-32-6 (power supply) | `supply.keithley` | USB | `USB0::1510::8832::4558551::0::INSTR` | 05e6:2280 |
| Keysight EDU36311A (power supply) | `supply.keysight` | USB | `USB0::10893::36609::CN64160195::0::INSTR` | 2a8d:8f01 |

> Serial numbers and exact USB0 index/subaddress fields will vary if
> instruments are replugged into different ports — always confirm with
> `list_resources()` and `*IDN?` rather than assuming the string stays fixed.

### Check the bench is alive

```bash
python3 -m bench list     # every registered instrument and its resource string
python3 -m bench scan     # *IDN? everything the VISA backend can currently see
python3 -m bench check    # ping each registered instrument, PASS/FAIL per line
```

`check` exits non-zero if anything doesn't answer. A USB instrument missing
from `scan` usually needs the udev rule below.

---

## Registering a USB instrument

This section is about getting a USB-connected instrument visible to PyVISA in
the first place, so `pyvisa.ResourceManager('@py').list_resources()` picks it
up. Skip it for the TCP/IP instruments.

### Background: what's actually happening

Bench test instruments (scopes, supplies, function generators) that connect
over USB generally use a USB standard called **USBTMC** (USB Test &
Measurement Class). This defines how SCPI commands (`VOLT 5`, `MEAS:CURR?`,
etc.) get wrapped into USB packets, so any USBTMC-compliant instrument can be
controlled the same way regardless of manufacturer.

Two things can go wrong before PyVISA can see a USBTMC device:

1. **The Linux kernel's `usbtmc` driver isn't loaded / doesn't exist** on this
   system, so no `/dev/usbtmc*` device file is created.
2. **Even without that driver**, `pyvisa-py`'s USB backend can talk to a
   USBTMC device directly via `pyusb`/`libusb` — but only if your user account
   has **read/write** permission on the raw USB device node. By default, Linux
   only grants that to `root`.

### 1. Confirm the OS sees the device at all

```bash
lsusb
```

Look for your instrument in the list. Each line has this format:

```
Bus 001 Device 015: ID 2a8d:8f01 Keysight Technologies, Inc. EDU36311A
                        ^^^^ ^^^^
                  idVendor : idProduct
```

Note the `idVendor` and `idProduct` hex values — you'll need them for the udev
rule below.

> If nothing shows up in `lsusb` at all, the device isn't connected /
> recognized at the USB level — check the **physical** cable.

### 2. Confirm it's actually a USBTMC instrument (optional)

```bash
lsusb -v -d <idVendor>:<idProduct> 2>/dev/null | grep -A2 bInterfaceClass
```

You want to see:

```
bInterfaceClass       254 Application Specific Interface
bInterfaceSubClass      3 Test and Measurement
bInterfaceProtocol      1 TMC
```

### 3. Check current permissions on the raw device node

```bash
ls -l /dev/bus/usb/001/XXX   # use the Bus/Device numbers from lsusb
```

If you see something like:

```
crw-rw-r-- 1 root root 189, 2 ...
```

— read/write for `root`, read-only for everyone else — your user doesn't have
write access, which is why `pyvisa-py` can't talk to it (device is visible,
but not controllable).

### 4. Add a udev rule granting access

Edit (or create) the rules file:

```bash
sudo vim /etc/udev/rules.d/99-usbtmc.rules
```

Add one line per instrument, using the `idVendor`/`idProduct` from step 1:

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="7540", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="05e6", ATTRS{idProduct}=="2280", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="2a8d", ATTRS{idProduct}=="8f01", MODE="0666"
```

`MODE="0666"` grants read/write to everyone. You can scope this tighter (e.g.
to a specific group) if multiple users share the board and you want more
control, but `0666` is simplest for a single-user lab setup.

### 5. Reload udev and re-trigger

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 6. Unplug and replug the instrument

Rules only apply when a device (re)connects — `udevadm trigger` alone
sometimes isn't enough for USB devices already attached before the rule
existed. Physically unplug and replug the USB cable to force re-enumeration.

### 7. Verify permissions changed

```bash
lsusb   # note the (possibly new) Bus/Device number — it can change on replug
ls -l /dev/bus/usb/001/XXX
```

You should now see:

```
crw-rw-rw- 1 root root 189, 11 ...
```

### 8. Re-run the PyVISA resource scan

```bash
python3 -m bench scan
```

The new instrument should appear as a
`USB0::<vendor_dec>::<product_dec>::<serial>::0::INSTR` entry, followed by its
`*IDN?` string (note: PyVISA reports vendor/product IDs in **decimal**, not
hex — e.g. hex `2a8d` becomes decimal `10893`).

A clean identification string back confirms the instrument is fully working.

### 9. Add it to the package

Paste the resource string into `REGISTRY` in
[bench/\_\_init\_\_.py](bench/__init__.py) — see
[Adding an instrument](#adding-an-instrument) — and it becomes available as
`<category>.<model>` everywhere.

---

## Examples

### The scripts

They all run by plain path, from any directory — each adds the project root
to `sys.path` itself:

```bash
python examples/funcgen_basics.py      # one instrument, no wiring needed
python examples/scope_basics.py        # one instrument, no wiring needed
python examples/supply_ramp.py         # enables a supply output
python examples/sine_loopback_test.py  # both TCP/IP instruments, needs a cable
```

`python` and `python3` both work — see [Setup](#python).

**[examples/funcgen_basics.py](examples/funcgen_basics.py)** — the simplest
one. Sets a sine, then changes frequency / amplitude / offset one at a time,
then switches to square (with a duty cycle) and ramp, reading every value
back off the instrument as it goes. Nothing needs to be connected to the
output.

**[examples/scope_basics.py](examples/scope_basics.py)** — sets a channel's
vertical scale, offset, timebase and trigger, reads those back, takes the
four scalar measurements, then captures the waveform once and writes it to
both `scope_basics.csv` and `scope_basics.png`. With nothing connected you
get noise and `None` for frequency, which still exercises the whole path.
Set `SCOPE` at the top to `sds1104x` (LAN) or `sds1104x_usb`.

**[examples/supply_ramp.py](examples/supply_ramp.py)** — brings a rail up to
3.3 V, measures it, brings it down. Set `SUPPLY` to `keithley`, `keysight` or
`spd`; nothing else changes, because the supplies share one interface. **This
one does enable a supply output.**

**[examples/sine_loopback_test.py](examples/sine_loopback_test.py)** — the
end-to-end check of the two TCP/IP instruments. It commands a 500 Hz / 2 Vpp
sine out of the 33220A, measures it on scope channel 4, and compares the
readings against what was asked for: generator readback, the scope's own
frequency / period / Vpp, and Vpp recomputed from the raw samples. It writes
`sine_loopback.png` so the capture can be confirmed by eye, prints a
`PASS`/`FAIL` line per check, and exits non-zero if any fail.

**It needs a cable from the generator's OUTPUT to scope channel 4.** Cabled
up it reports 6/6 — 500 Hz, 2.1 Vpp measured against 2.0 commanded, 7 cycles
across the capture. With the cable out the two generator checks pass and
every scope check fails at ~0.1 Vpp of noise:

```
PASS  generator amplitude: 2 Vpp (expected 2 Vpp, off by 0.0%, tol 0%)
FAIL  measured frequency: no measurement (is the cable connected?)
FAIL  measured Vpp: 0.06 V (expected 2 V, off by 97.0%, tol 15%)
```

`sine_loopback.png` is written to the current directory — check it before
suspecting the code.

### From Python

```python
from bench import Bench

with Bench() as b:                              # nothing connects until you use it
    funcgen = b.funcgen.agilent
    scope = b.scope.sds1104x

    funcgen.set_load('INF')                     # high-Z, else amplitudes read half
    funcgen.set_sine(500, amplitude_vpp=2.0)
    funcgen.output_on()

    scope.enable_channel(4)
    print(scope.measure_all(4))                 # freq, period, Vpp, mean
    t, v = scope.get_waveform(4)                # numpy arrays
    scope.plot_waveform(4, 'check.png')         # decimated for drawing

    b.supply.keysight.set_voltage(3.3, channel=1)
```

Models are built on first touch and cached; the VISA session opens on the
first read/write and leaving the `with` block closes whatever was opened.

A category is also indexable and iterable, so you can pick a machine at
runtime:

```python
supply = b.supply['keithley']      # same object as b.supply.keithley
list(b.supply)                     # ['keithley', 'keysight', 'spd']
b['scope.sds1104x']                # the dotted name, as the CLI uses it
b.opened                           # ['scope.sds1104x']
```

**Within a category every model takes the same calls**, so swapping machines
doesn't mean rewriting call sites. Supplies take `channel` as a keyword
defaulting to 1 — a single-output Keithley and a three-output Keysight are
driven identically:

```python
for name in b.supply:
    supply = b.supply[name]
    supply.configure(3.3, 0.5)              # volts, current limit, channel=1
    print(name, supply.measure_all())       # {'voltage_v': ..., 'current_a': ...}
```

Asking a single-output supply for a channel it doesn't have is an error, not
a silent write to channel 1:

```python
b.supply.keithley.set_voltage(3.3, channel=2)
# ValueError: Keithley2280S has one output (channel 1), got 2
```

Drivers also work standalone, and resource strings can be overridden when
something moves:

```python
from bench import SiglentSDS1104XE
with SiglentSDS1104XE() as scope:
    print(scope.idn())

Bench(resources={'scope.sds1104x': 'TCPIP::172.24.58.99::INSTR'})
```

### From the command line

```bash
python3 -m bench list                      # every instrument
python3 -m bench scan                      # *IDN? every visible resource
python3 -m bench check                     # ping all
python3 -m bench check scope.sds1104x      # ...or just these
python3 -m bench methods supply.keithley   # what you can call
python3 -m bench call scope.sds1104x measure_all 4
python3 -m bench call supply.keysight set_voltage 3.3 channel=1
```

`call` passes positional values and `key=value` pairs straight through to the
method, parsing them as Python literals (`4` → int, `channel=2` → kwarg).

### Testing a change

Nothing in this section enables a supply output — the hardware checks are
read-only (`*IDN?` and queries), and the driver checks don't touch the bus at
all.

**Read-only, against real instruments:**

```bash
python3 -m bench check scope.sds1104x funcgen.agilent
python3 -m bench call scope.sds1104x measure_all 4
python3 -m bench call funcgen.agilent settings
python3 -c "
from bench import Bench
with Bench() as b:
    t, v = b.scope.sds1104x.get_waveform(4)
    print(len(t), 'points over', t[-1] - t[0], 's')"
```

**Offline, no hardware** — swap in a fake session and inspect the SCPI a
driver emits. This is how to check the supply drivers without powering
anything on:

```python
from bench import Bench

class Fake:
    timeout = 0
    def __init__(self, replies=None): self.log = []; self.replies = replies or {}
    def write(self, c): self.log.append(c)
    def query(self, c): self.log.append(c); return self.replies.get(c, '0')
    def close(self): pass

b = Bench()
spd = b.supply.spd
spd._inst = Fake({'MEAS:CURR?;VOLT?': '0.2500;1.8000'})   # bypass the real connection

spd.configure(1.8, 0.5, channel=1)
print(spd.measure_all(channel=1))   # {'current_a': 0.25, 'voltage_v': 1.8}
print(spd._inst.log)                # every command it would have sent
```

Pointing the same block at `b.supply.keithley` or `b.supply.keysight` with
their own canned replies is how the uniform interface gets checked — the
calls stay identical, only the emitted SCPI differs.

### What's been verified

| Driver | Status |
|---|---|
| `SiglentSDS1104XE` | verified on hardware over LAN — IDN, measurements, waveform capture at 1 GSa/s, CSV + PNG, and the full loopback test at 6/6. The decimation added since then is verified against a simulated 14 M-sample record, not yet on the instrument; the USB resource string has never been opened. |
| `Agilent33220A` | verified on hardware — IDN, settings readback, sine output measured back on the scope |
| `Keithley2280S` | SCPI verified offline against the original `legacy/supply.py` |
| `KeysightEDU36311A` | SCPI verified offline against the original `legacy/supply_ks.py` |
| `SiglentSPD3000` | **never run.** Reconstructed from the commented-out block in `legacy/hello.py` plus the resource string above — that old script actually opened the *scope's* IP under the name `supply`, so this code path has never talked to the real supply. Treat the first run as a bringup. |

Two caveats on the supply drivers, both inherited from the originals and
neither exercised yet: `get_current_limit()` queries `CURRENT?` on the
SPD3000 (matching how its limit is *set*), and `output_state()` assumes all
three supplies answer `OUTP?` with `0`/`1`.

---

## Adding an instrument

Subclass the right **category** — `Scope`, `FunctionGenerator` or
`PowerSupply` — rather than `Instrument` directly, so it inherits the shared
behaviour and keeps the interface its siblings have. Set `ALIAS` /
`DEFAULT_RESOURCE` / `DESCRIPTION` (and `CHANNELS` for a multi-output
supply), implement the model-specific methods, then add one line to
`REGISTRY` in [bench/\_\_init\_\_.py](bench/__init__.py) — it shows up in
`Bench` and the CLI automatically.

A whole new *kind* of instrument (a DMM, say) means a new category class in
[bench/categories.py](bench/categories.py) and a new key in `REGISTRY`.
