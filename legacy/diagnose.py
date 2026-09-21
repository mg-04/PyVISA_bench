import pyvisa

rm = pyvisa.ResourceManager('@py')
resources = rm.list_resources()

for res in resources:
    try:
        inst = rm.open_resource(res)
        inst.timeout = 3000
        idn = inst.query('*IDN?')
        print(f"{res} -> {idn.strip()}")
        inst.close()
    except Exception as e:
        print(f"{res} -> Error: {e}")