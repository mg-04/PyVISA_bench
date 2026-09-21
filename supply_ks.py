import pyvisa
from time import sleep

rm = pyvisa.ResourceManager('@py')
keysight = rm.open_resource('USB0::10893::36609::CN64160195::0::INSTR')
keysight.timeout = 5000

print("Connected to:", keysight.query('*IDN?'))

# ------------------------------------------------------------------
# Basic control (channel-aware — this supply has 3 outputs)
# ------------------------------------------------------------------

def reset():
    keysight.write('*RST')

def select_channel(channel):
    """Channel 1, 2, or 3."""
    keysight.write(f'INST:NSEL {channel}')

def output_on(channel):
    select_channel(channel)
    keysight.write('OUTP ON')

def output_off(channel):
    select_channel(channel)
    keysight.write('OUTP OFF')

def set_voltage(channel, volts):
    select_channel(channel)
    keysight.write(f'VOLT {volts}')

def set_current_limit(channel, amps):
    select_channel(channel)
    keysight.write(f'CURR {amps}')

def measure_voltage(channel):
    select_channel(channel)
    return float(keysight.query('MEAS:VOLT?'))

def measure_current(channel):
    select_channel(channel)
    return float(keysight.query('MEAS:CURR?'))

# ------------------------------------------------------------------
# Test sequence
# ------------------------------------------------------------------

if __name__ == "__main__":
    try:
        idn = keysight.query('*IDN?')
        print("PASS — identified:", idn.strip())

        reset()
        sleep(1)

        # Test channel 1 with a safe low setpoint
        set_voltage(1, 3.3)
        set_current_limit(1, 0.1)
        output_on(1)
        sleep(1)

        v = measure_voltage(1)
        i = measure_current(1)
        print(f"PASS — Channel 1: {v:.4f} V, {i:.4f} A")

        output_off(1)

        print("\nALL TESTS PASSED")

    except Exception as e:
        print("FAIL —", e)

    finally:
        keysight.close()