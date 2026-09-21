"""Function generator models."""

from .categories import FunctionGenerator


class Agilent33220A(FunctionGenerator):
    """Agilent 33220A, single output."""

    ALIAS = 'agilent'
    DEFAULT_RESOURCE = 'TCPIP::172.24.58.190::INSTR'
    DESCRIPTION = 'Agilent 33220A'

    # -- output control ---------------------------------------------------

    def output_on(self):
        self.write('OUTP ON')

    def output_off(self):
        self.write('OUTP OFF')

    def output_state(self):
        return bool(int(self.query('OUTP?')))

    def set_load(self, ohms='INF'):
        """Output termination: a resistance in ohms, or ``'INF'`` for high-Z.

        Set this before amplitudes matter — the generator halves its output
        when it assumes a 50 ohm load that isn't there.
        """
        self.write(f'OUTP:LOAD {ohms}')

    # -- waveform in one shot ---------------------------------------------

    def set_sine(self, freq_hz, amplitude_vpp=1.0, offset_v=0.0):
        self.write(f'APPL:SIN {freq_hz},{amplitude_vpp},{offset_v}')

    def set_square(self, freq_hz, amplitude_vpp=1.0, offset_v=0.0):
        self.write(f'APPL:SQU {freq_hz},{amplitude_vpp},{offset_v}')

    def set_ramp(self, freq_hz, amplitude_vpp=1.0, offset_v=0.0):
        self.write(f'APPL:RAMP {freq_hz},{amplitude_vpp},{offset_v}')

    def set_pulse(self, freq_hz, amplitude_vpp=1.0, offset_v=0.0):
        self.write(f'APPL:PULS {freq_hz},{amplitude_vpp},{offset_v}')

    # -- one parameter at a time -------------------------------------------

    def set_frequency(self, freq_hz):
        self.write(f'FREQ {freq_hz}')

    def set_amplitude(self, vpp):
        self.write(f'VOLT {vpp}')

    def set_offset(self, volts):
        self.write(f'VOLT:OFFS {volts}')

    def set_duty_cycle(self, percent):
        """Only meaningful for square/pulse waveforms."""
        self.write(f'FUNC:SQU:DCYC {percent}')

    # -- readback -----------------------------------------------------------

    def get_frequency(self):
        return self.query_float('FREQ?')

    def get_amplitude(self):
        return self.query_float('VOLT?')

    def get_offset(self):
        return self.query_float('VOLT:OFFS?')

    def get_waveform(self):
        return self.query('FUNC?').strip()
