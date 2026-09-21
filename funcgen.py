import pyvisa
from time import sleep

# --- Connect ---
rm = pyvisa.ResourceManager('@py')
funcgen = rm.open_resource('TCPIP::172.24.58.190::INSTR')
funcgen.timeout = 5000

print("Connected to:", funcgen.query('*IDN?'))

# ------------------------------------------------------------------
# Basic control
# ------------------------------------------------------------------

def reset():
    """Reset to factory defaults."""
    funcgen.write('*RST')

def output_on():
    funcgen.write('OUTP ON')

def output_off():
    funcgen.write('OUTP OFF')

# ------------------------------------------------------------------
# Waveform setup
# ------------------------------------------------------------------

def set_sine(freq_hz, amplitude_vpp=1.0, offset_v=0.0):
    """Configure a sine wave in one shot."""
    funcgen.write(f'APPL:SIN {freq_hz},{amplitude_vpp},{offset_v}')

def set_square(freq_hz, amplitude_vpp=1.0, offset_v=0.0):
    funcgen.write(f'APPL:SQU {freq_hz},{amplitude_vpp},{offset_v}')

def set_ramp(freq_hz, amplitude_vpp=1.0, offset_v=0.0):
    funcgen.write(f'APPL:RAMP {freq_hz},{amplitude_vpp},{offset_v}')

def set_pulse(freq_hz, amplitude_vpp=1.0, offset_v=0.0):
    funcgen.write(f'APPL:PULS {freq_hz},{amplitude_vpp},{offset_v}')

# ------------------------------------------------------------------
# Fine-grained parameter control (adjust one thing at a time)
# ------------------------------------------------------------------

def set_frequency(freq_hz):
    funcgen.write(f'FREQ {freq_hz}')

def set_amplitude(vpp):
    funcgen.write(f'VOLT {vpp}')

def set_offset(volts):
    funcgen.write(f'VOLT:OFFS {volts}')

def set_duty_cycle(percent):
    """Only meaningful for square/pulse waveforms."""
    funcgen.write(f'FUNC:SQU:DCYC {percent}')

# ------------------------------------------------------------------
# Read back current settings
# ------------------------------------------------------------------

def get_frequency():
    return float(funcgen.query('FREQ?'))

def get_amplitude():
    return float(funcgen.query('VOLT?'))

def get_offset():
    return float(funcgen.query('VOLT:OFFS?'))

def get_waveform():
    return funcgen.query('FUNC?').strip()

# ------------------------------------------------------------------
# Example usage
# ------------------------------------------------------------------

if __name__ == "__main__":
    reset()
    sleep(1)
    funcgen.write(f'OUTP:LOAD INF')

    set_sine(freq_hz=500, amplitude_vpp=2.0, offset_v=0.0)
    output_on()

    print("Waveform:", get_waveform())
    print("Frequency:", get_frequency(), "Hz")
    print("Amplitude:", get_amplitude(), "Vpp")

    sleep(3)
    #output_off()
    #funcgen.close()