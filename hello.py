import pyvisa
from time import sleep

# --- Connect ---
rm = pyvisa.ResourceManager('@py')
print("Available resources:", rm.list_resources())

# Replace with your supply's actual VISA resource string
supply = rm.open_resource('TCPIP::172.24.58.184::INSTR')
supply.timeout = 5000

print("Connected to:", supply.query('*IDN?'))

"""
# --- Supply control functions ---
def init_supply(channel=1, vcc=1.8, current_limit=0.5):
    # Set up a channel's voltage and current limit, output off initially.
    supply.write('OUTP OFF')
    supply.write(f'INST:SEL OUT{channel}')
    supply.write(f'CURRENT {current_limit}')
    supply.write(f'VOLT {vcc}')

def turn_on():
    supply.write('OUTP ON')
    print("Output ON")
    print(supply.query('MEAS:CURR?;VOLT?'))

def turn_off():
    supply.write('OUTP OFF')
    print("Output OFF")
    print(supply.query('MEAS:CURR?;VOLT?'))

def set_voltage(channel, volts):
    supply.write(f'INST:SEL OUT{channel}')
    supply.write(f'VOLT {volts}')

def read_measurements():
    """Returns (current, voltage) as floats."""
    result = supply.query('MEAS:CURR?;VOLT?')
    curr_str, volt_str = result.split(';')
    return float(curr_str), float(volt_str)
"""
# --- Example usage ---
if __name__ == "__main__":
    pass
    # init_supply(channel=1, vcc=1.8, current_limit=0.5)
    # turn_on()
    # sleep(1)
    # current, voltage = read_measurements()
    # print(f"Current: {current} A, Voltage: {voltage} V")
    # turn_off()
    # supply.close()