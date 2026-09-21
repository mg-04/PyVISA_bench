import pyvisa
from time import sleep

# --- Connect ---
rm = pyvisa.ResourceManager('@py')
osc = rm.open_resource('TCPIP::172.24.58.184::INSTR')  # use whichever IP was the scope
osc.timeout = 5000

print("Connected to:", osc.query('*IDN?'))

# ------------------------------------------------------------------
# Basic control
# ------------------------------------------------------------------

def autoset():
    """Let the scope auto-adjust vertical/horizontal/trigger settings."""
    osc.write('ASET')

def run():
    osc.write('RUN')

def stop():
    osc.write('STOP')

def reset():
    """Reset scope to default settings."""
    osc.write('*RST')

# ------------------------------------------------------------------
# Vertical / horizontal setup
# ------------------------------------------------------------------

def set_vertical_scale(channel, volts_per_div):
    """e.g. set_vertical_scale(1, 0.5) -> 500mV/div on channel 1."""
    osc.write(f'C{channel}:VDIV {volts_per_div}')

def set_vertical_offset(channel, offset_volts):
    osc.write(f'C{channel}:OFST {offset_volts}')

def set_timebase(sec_per_div):
    """e.g. set_timebase(1e-3) -> 1ms/div."""
    osc.write(f'TDIV {sec_per_div}')

def enable_channel(channel, on=True):
    state = 'ON' if on else 'OFF'
    osc.write(f'C{channel}:TRA {state}')

# ------------------------------------------------------------------
# Trigger setup
# ------------------------------------------------------------------

def set_trigger_source(channel):
    osc.write(f'TRSE EDGE,SR,C{channel},HT,OFF')

def set_trigger_level(channel, level_volts):
    osc.write(f'C{channel}:TRLV {level_volts}')

# ------------------------------------------------------------------
# Measurements
# ------------------------------------------------------------------

def measure_freq(channel=1):
    raw = osc.query(f'C{channel}:PAVA? FREQ')
    value_str = raw.split(',')[-1].strip('Hz\n')
    if '*' in value_str:
        print(f"Channel {channel}: no valid frequency measurement (got {raw.strip()})")
        return None
    return float(value_str)

def measure_period(channel=1):
    raw = osc.query(f'C{channel}:PAVA? PER')
    return float(raw.split(',')[-1].strip('S\n'))

def measure_pkpk(channel=1):
    """Peak-to-peak voltage."""
    raw = osc.query(f'C{channel}:PAVA? PKPK')
    return float(raw.split(',')[-1].strip('V\n'))

def measure_mean(channel=1):
    """Mean voltage."""
    raw = osc.query(f'C{channel}:PAVA? MEAN')
    return float(raw.split(',')[-1].strip('V\n'))

# ------------------------------------------------------------------
# Example usage
# ------------------------------------------------------------------

if __name__ == "__main__":
    # reset()
    sleep(1)
    enable_channel(4, on=True)
    set_vertical_scale(4, 0.5)
    set_timebase(1e-3)
    autoset()
    sleep(2)

    freq = measure_freq(4)
    vpp = measure_pkpk(4)
    print(f"Channel 4 — Frequency: {freq} Hz, Vpp: {vpp} V")

    osc.close()