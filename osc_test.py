import pyvisa

rm = pyvisa.ResourceManager('@py')
supply = rm.open_resource('TCPIP::172.24.58.190::INSTR')
supply.timeout = 5000

try:
    idn = supply.query('*IDN?')
    print("PASS — device responded:", idn.strip())
except Exception as e:
    print("FAIL —", e)
finally:
    supply.close()