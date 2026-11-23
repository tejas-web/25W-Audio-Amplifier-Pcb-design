#!/usr/bin/env python3
"""Run an explicitly approximate amplifier model using installed libngspice."""
from pathlib import Path
import ctypes as C
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json, os
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
xml=ET.parse('schematic.net.xml').getroot()
node_alias={'GND':'0','+12V':'vcc','-12V':'vee','+5V':'input','Net-(U1-+)':'noninv','Net-(U1--)':'inv','Net-(J1-Pin_1)':'output','Net-(C2-Pad1)':'feedback_cap','Net-(C5-Pad1)':'zobel'}
pins={}
for n in xml.findall('./nets/net'):
    for p in n.findall('node'): pins[p.get('ref'),p.get('pin')]=node_alias[n.get('name')]
parts=[]
for p in xml.findall('./components/comp'):
    ref=p.get('ref')
    if ref[0] in 'RC':
        value=p.findtext('value').lower().replace('f','')
        parts.append(f'{ref} {pins[ref,"1"]} {pins[ref,"2"]} {value}')
model='''* Educational behavioural approximation, NOT a manufacturer TDA2050 model.
* Ideal high-gain amplifier with arbitrary 2 V rail headroom and 0.1 ohm output.
* No thermal/current protection, slew rate, frequency compensation or parasitics.
.subckt AMP_APPROX plus minus vp vn out
Bdrive drive 0 V=10*tanh(10000*V(plus,minus))
Rout drive out 0.1
.ends AMP_APPROX
'''
(ROOT/'amplifier_approx.lib').write_text(model)
base='''TDA2050 circuit connectivity check - APPROXIMATE MODEL
.include amplifier_approx.lib
Vpositive vcc 0 12
Vnegative vee 0 -12
Vinput input 0 DC 0 AC 1 SIN(0 {amp} 1000)
'''+ '\n'.join(parts)+'''\nXU1 noninv inv vcc vee output AMP_APPROX
Rload output 0 {load}
.nodeset v(output)=0 v(inv)=0 v(noninv)=0
'''
lib=C.CDLL('libngspice.so.0')
CB=C.CFUNCTYPE(C.c_int,C.c_char_p,C.c_int,C.c_void_p)
messages=[]
@CB
def output(s,i,u):
    messages.append(s.decode(errors='replace')); return 0
lib.ngSpice_Init.argtypes=[CB,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]
lib.ngSpice_Init(output,None,None,None,None,None,None)
lib.ngSpice_Command.argtypes=[C.c_char_p]
def command(x):
    rc=lib.ngSpice_Command(x.encode())
    if rc: raise RuntimeError(x)
results={}
for load in [8,4]:
    for name,amp in [('small',0.1),('overdrive',0.5)]:
        tag=f'{name}_{load}ohm'
        deck=base.format(amp=amp,load=load)+'.end\n'
        (ROOT/f'{tag}.cir').write_text(deck)
        for suffix in ['op', 'ac', 'tran']:
            (ROOT/f'{tag}_{suffix}.txt').unlink(missing_ok=True)
        command(f'source {tag}.cir')
        command('set wr_vecnames')
        command('set wr_singlescale')
        command('op')
        command(f'wrdata {tag}_op.txt v(output) v(noninv) v(inv)')
        command('ac dec 100 2 200000')
        command(f'wrdata {tag}_ac.txt v(output)')
        command('tran 2u 100m 80m')
        command(f'wrdata {tag}_tran.txt v(input) v(output)')
        a=np.loadtxt(f'{tag}_ac.txt',skiprows=1)
        t=np.loadtxt(f'{tag}_tran.txt',skiprows=1)
        if not np.all(np.isfinite(t)) or np.max(abs(t[:,2])) > 10.01:
            raise RuntimeError('Invalid simulation output; inspect ngspice log')
        gain=np.hypot(a[:,1],a[:,2]); idx=np.argmin(abs(a[:,0]-1000))
        rms=float(np.sqrt(np.mean(t[:,2]**2)))
        results[tag]={'gain_1khz_V_per_V':float(gain[idx]),'gain_1khz_dB':float(20*np.log10(gain[idx])),'output_peak_V':float(np.max(abs(t[:,2]))),'output_rms_V':rms,'load_power_W':rms*rms/load}
        if name=='small' and load==8:
            fig,ax=plt.subplots(2,1,figsize=(9,7))
            ax[0].semilogx(a[:,0],20*np.log10(gain)); ax[0].set(xlabel='Frequency (Hz)',ylabel='Gain (dB)',title='Approximate model only: frequency response, 8 ohm'); ax[0].grid()
            m=t[:,0]>0.096
            ax[1].plot(t[m,0]*1000,t[m,1],label='Input');ax[1].plot(t[m,0]*1000,t[m,2],label='Output');ax[1].set(xlabel='Time (ms)',ylabel='Voltage (V)',title='100 mV peak input, 1 kHz');ax[1].legend();ax[1].grid();fig.tight_layout();fig.savefig('response.png',dpi=150);plt.close(fig)
        command('destroy all')
(ROOT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
(ROOT/'ngspice.log').write_text('\n'.join(messages))
print(json.dumps(results,indent=2))
