# Registering USB Test Instruments on the PYNQ Board

This guide documents how to get USB-connected test instruments (power supplies,
scopes, function generators, etc.) visible to PyVISA on the PYNQ board, so
`pyvisa.ResourceManager('@py').list_resources()` picks them up correctly.

---

## Background: what's actually happening

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


---

## Registering a new USB instrument

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

```python
import pyvisa
rm = pyvisa.ResourceManager('@py')
print(rm.list_resources())
```

The new instrument should now appear as a `USB0::<vendor_dec>::<product_dec>::<serial>::0::INSTR`
entry (note: PyVISA reports vendor/product IDs in **decimal**, not hex — e.g.
hex `2a8d` becomes decimal `10893`).

### 9. Confirm it responds

```python
inst = rm.open_resource('USB0::...::INSTR')  # paste the exact string
inst.timeout = 5000
print(inst.query('*IDN?'))
```

A clean identification string back confirms the instrument is fully working.


---

## Quick reference: known instruments on this bench

| Instrument | Interface | Resource string | idVendor:idProduct |
|---|---|---|---|
| Siglent SDS1104X-E (scope #1) | TCP/IP | `TCPIP::172.24.58.184::INSTR` | — |
| Siglent SDS1104X-E (scope #2) | USB | `USB0::62700::60984::SDSMMEBQ4R5170::0::INSTR` | — |
| Agilent 33220A (function gen) | TCP/IP | `TCPIP::172.24.58.190::INSTR` | — |
| Siglent SPD3000 (power supply) | USB | `USB0::1155::30016::SPD3XHCD3R4649::0::INSTR` | 0483:7540 |
| Keithley 2280S-32-6 (power supply) | USB | `USB0::1510::8832::4558551::0::INSTR` | 05e6:2280 |
| Keysight EDU36311A (power supply) | USB | `USB0::10893::36609::CN64160195::0::INSTR` | 2a8d:8f01 |

> Serial numbers and exact USB0 index/subaddress fields will vary if
> instruments are replugged into different ports — always confirm with
> `list_resources()` and `*IDN?` rather than assuming the string stays fixed.