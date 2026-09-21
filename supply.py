import pyvisa
from time import sleep

# --- Connect ---
rm = pyvisa.ResourceManager('@py')
keithley = rm.open_resource('USB0::1510::8832::4558551::0::INSTR')
keithley.timeout = 5000

print("Connected to:", keithley.query('*IDN?'))

# ------------------------------------------------------------------
# Basic control
# ------------------------------------------------------------------

def reset():
    """Reset to factory defaults."""
    keithley.write('*RST')

def output_on():
    keithley.write('OUTP ON')

def output_off():
    keithley.write('OUTP OFF')

def output_state():
    """Returns True if output is currently on."""
    return bool(int(keithley.query('OUTP?')))

# ------------------------------------------------------------------
# Voltage / current setpoints
# ------------------------------------------------------------------

def set_voltage(volts):
    keithley.write(f'VOLT {volts}')

def set_current_limit(amps):
    keithley.write(f'CURR {amps}')

def get_voltage_setpoint():
    return float(keithley.query('VOLT?'))

def get_current_limit_setpoint():
    return float(keithley.query('CURR?'))

# ------------------------------------------------------------------
# Measurements (actual output, not setpoints)
# ------------------------------------------------------------------

def measure_all():
    """
    Returns (current_A, voltage_V, timestamp_s) parsed from the compound
    measurement string this model returns.
    """
    raw = keithley.query('MEAS:VOLT?')  # returns curr,volt,time even from this query
    parts = raw.strip().split(',')

    current = float(parts[0].rstrip('A'))
    voltage = float(parts[1].rstrip('V'))
    timestamp = float(parts[2].rstrip('s'))

    return current, voltage, timestamp

def measure_voltage():
    """Just the voltage, parsed from the compound response."""
    _, voltage, _ = measure_all()
    return voltage

def measure_current():
    """Just the current, parsed from the compound response."""
    current, _, _ = measure_all()
    return current

# ------------------------------------------------------------------
# Protection settings
# ------------------------------------------------------------------

def set_ovp(volts):
    """Over-voltage protection threshold."""
    keithley.write(f'VOLT:PROT {volts}')

def set_ocp(amps):
    """Over-current protection threshold."""
    keithley.write(f'CURR:PROT {amps}')

# ------------------------------------------------------------------
# Example usage
# ------------------------------------------------------------------

if __name__ == "__main__":
    reset()
    sleep(1)

    set_voltage(3.3)
    set_current_limit(0.5)
    output_on()

    sleep(10)

    current, voltage, timestamp = measure_all()
    print(f"Output: {voltage:.4f} V, {current:.4f} A  (t={timestamp:.2f}s)")

    output_off()
    keithley.close()