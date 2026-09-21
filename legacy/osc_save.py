import pyvisa
import numpy as np
from time import sleep

# --- Connect ---
rm = pyvisa.ResourceManager('@py')
osc = rm.open_resource('TCPIP::172.24.58.184::INSTR')
osc.timeout = 10000  # waveform transfers can be slow, give it more time

print("Connected to:", osc.query('*IDN?'))

# ------------------------------------------------------------------
# Basic control
# ------------------------------------------------------------------

def autoset():
    osc.write('ASET')

def run():
    osc.write('RUN')

def stop():
    osc.write('STOP')

def reset():
    osc.write('*RST')

# ------------------------------------------------------------------
# Vertical / horizontal setup
# ------------------------------------------------------------------

def set_vertical_scale(channel, volts_per_div):
    osc.write(f'C{channel}:VDIV {volts_per_div}')

def set_vertical_offset(channel, offset_volts):
    osc.write(f'C{channel}:OFST {offset_volts}')

def set_timebase(sec_per_div):
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
# Scalar measurements
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
    value_str = raw.split(',')[-1].strip('S\n')
    if '*' in value_str:
        print(f"Channel {channel}: no valid period measurement (got {raw.strip()})")
        return None
    return float(value_str)

def measure_pkpk(channel=1):
    raw = osc.query(f'C{channel}:PAVA? PKPK')
    value_str = raw.split(',')[-1].strip('V\n')
    if '*' in value_str:
        print(f"Channel {channel}: no valid Vpp measurement (got {raw.strip()})")
        return None
    return float(value_str)

def measure_mean(channel=1):
    raw = osc.query(f'C{channel}:PAVA? MEAN')
    value_str = raw.split(',')[-1].strip('V\n')
    if '*' in value_str:
        print(f"Channel {channel}: no valid mean measurement (got {raw.strip()})")
        return None
    return float(value_str)

# ------------------------------------------------------------------
# Waveform capture (raw points)
# ------------------------------------------------------------------

def parse_sara(sara_raw):
    """
    Parse a response like 'SARA 1.00GSa/s' or 'SARA 500MSa/s' into a float (samples/sec).
    Prints the raw string so you can confirm the format matches what's assumed here.
    """
    print("Raw SARA response:", repr(sara_raw))
    value_part = sara_raw.split(' ')[-1].strip()  # e.g. '1.00GSa/s\n'
    value_part = value_part.replace('Sa/s', '').strip()

    multiplier = 1.0
    if value_part.endswith('G'):
        multiplier = 1e9
        value_part = value_part[:-1]
    elif value_part.endswith('M'):
        multiplier = 1e6
        value_part = value_part[:-1]
    elif value_part.endswith('k') or value_part.endswith('K'):
        multiplier = 1e3
        value_part = value_part[:-1]

    return float(value_part) * multiplier


def get_waveform(channel=4, points=None):
    """
    Pull raw waveform data from the scope and return (time_array, voltage_array).
    """
    osc.write(f'C{channel}:WF? DAT2')
    raw = osc.read_raw()

    # Strip the block header before the actual binary payload
    header_end = raw.find(b'#')
    num_digits = int(raw[header_end + 1:header_end + 2])
    data_len = int(raw[header_end + 2: header_end + 2 + num_digits])
    data_start = header_end + 2 + num_digits
    adc_bytes = raw[data_start:data_start + data_len]

    adc_values = np.frombuffer(adc_bytes, dtype=np.int8)

    # Vertical scaling
    vdiv = float(osc.query(f'C{channel}:VDIV?').split(' ')[-1].strip('V\n'))
    offset = float(osc.query(f'C{channel}:OFST?').split(' ')[-1].strip('V\n'))
    voltage = adc_values * (vdiv / 25.0) - offset

    # Horizontal scaling — query real sample rate instead of guessing from timebase
    sara_raw = osc.query('SARA?')
    sample_rate = parse_sara(sara_raw)
    sample_interval = 1.0 / sample_rate
    time_axis = np.arange(len(voltage)) * sample_interval

    if points:
        return time_axis[:points], voltage[:points]
    return time_axis, voltage


def sanity_check(t, v, expected_freq_hz=None):
    """Print basic checks so you can eyeball whether the capture looks right."""
    print(f"Captured {len(v)} points")
    print(f"Vpp estimate: {v.max() - v.min():.4f} V  (min={v.min():.4f}, max={v.max():.4f})")

    total_time = t[-1] - t[0]
    print(f"Total capture window: {total_time:.6e} s")

    if expected_freq_hz:
        expected_period = 1.0 / expected_freq_hz
        expected_cycles = total_time / expected_period
        print(f"Expected period: {expected_period:.6e} s -> ~{expected_cycles:.2f} cycles should be visible")

    try:
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot(t, v)
        plt.xlabel("Time (s)")
        plt.ylabel("Voltage (V)")
        plt.title("Captured waveform")
        plt.savefig('waveform_check.png')
        print("Saved plot to waveform_check.png")
    except ImportError:
        print("matplotlib not installed — skipping plot (pip install matplotlib to enable)")


# ------------------------------------------------------------------
# Example usage
# ------------------------------------------------------------------

if __name__ == "__main__":
    enable_channel(4, on=True)
    set_vertical_scale(4, 0.5)
    run()
    sleep(1)

    freq = measure_freq(4)
    vpp = measure_pkpk(4)
    print(f"Channel 4 — Frequency: {freq} Hz, Vpp: {vpp} V")

    t, v = get_waveform(channel=4)
    sanity_check(t, v, expected_freq_hz=500)  # your known input: 500 Hz, 2.0 Vpp

    osc.close()