#!/usr/bin/env python3
"""Feed a WAV recording through the project's approximate SPICE amplifier."""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import tempfile

os.environ.setdefault('MPLCONFIGDIR', '/tmp/pcb-audio-mpl')
import numpy as np
from scipy.io import wavfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audio', type=Path, help='PCM or float WAV file; stereo is mixed to mono')
    parser.add_argument('--start', type=float, default=0, help='Start within recording, seconds')
    parser.add_argument('--duration', type=float, default=1, help='Seconds to simulate (default: 1)')
    parser.add_argument('--input-peak', type=float, default=0.1, help='Scale selected audio to this peak voltage (default: 0.1 V)')
    parser.add_argument('--load', type=float, choices=[4, 8], default=8, help='Load resistance in ohms')
    parser.add_argument('--out', type=Path, default=ROOT / 'audio_results', help='Output directory')
    args = parser.parse_args()
    if not all(np.isfinite(v) for v in (args.start, args.duration, args.input_peak)) or args.start < 0 or args.duration <= 0 or args.input_peak <= 0:
        parser.error('start must be nonnegative; duration and input-peak must be positive finite numbers')
    rate, data = wavfile.read(args.audio)
    if data.dtype.kind == 'u':
        data = data.astype(float) - (np.iinfo(data.dtype).max + 1) / 2
    else:
        data = data.astype(float)
    if data.ndim == 2:
        data = data.mean(axis=1)
    data = data[int(args.start * rate):int((args.start + args.duration) * rate)]
    if len(data) < 2 or not np.all(np.isfinite(data)):
        parser.error('selected audio must contain at least two finite samples')
    peak = np.max(np.abs(data))
    vin = data * (args.input_peak / peak) if peak else data
    times = np.arange(len(vin)) / rate
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    messages = []
    callback_type = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)

    @callback_type
    def callback(message, ident, user):
        messages.append(message.decode(errors='replace'))
        return 0

    lib = C.CDLL('libngspice.so.0')
    lib.ngSpice_Init.argtypes = [callback_type] + [C.c_void_p] * 6
    lib.ngSpice_Command.argtypes = [C.c_char_p]
    lib.ngSpice_Init(callback, None, None, None, None, None, None)

    def command(value):
        if lib.ngSpice_Command(value.encode()):
            raise RuntimeError('ngspice command failed: ' + value)

    # Use a private temporary working directory for ngspice's relative file paths.
    previous = Path.cwd()
    try:
        with tempfile.TemporaryDirectory(prefix='pcb-audio-') as temp:
            os.chdir(temp)
            model = (ROOT / 'amplifier_approx.lib').read_text()
            # Reuse the existing circuit connectivity and replace only its source/load.
            lines = (ROOT / 'small_8ohm.cir').read_text().splitlines()
            deck = []
            for line in lines:
                if line.lower().startswith('.include'):
                    deck.append(model)
                elif line.startswith('Vinput '):
                    deck.append('Vinput input 0 DC 0 PWL(')
                    deck.extend(f'+ {t:.12g} {v:.12g}' for t, v in zip(times, vin))
                    deck.append('+ )')
                elif line.startswith('Rload '):
                    deck.append(f'Rload output 0 {args.load}')
                else:
                    deck.append(line)
            Path('audio.cir').write_text('\n'.join(deck) + '\n')
            command('source audio.cir')
            command('set wr_vecnames')
            command('set wr_singlescale')
            command(f'tran {1 / rate:.12g} {times[-1]:.12g} 0 {1 / (rate * 4):.12g}')
            command('wrdata transient.txt v(input) v(output)')
            raw = np.loadtxt('transient.txt', skiprows=1)
    finally:
        os.chdir(previous)
        (out / 'ngspice.log').write_text('\n'.join(messages) + '\n')
    if raw.ndim != 2 or raw.shape[1] != 3 or not np.all(np.isfinite(raw)) or raw[-1, 0] < times[-1] * 0.999:
        raise RuntimeError('Incomplete or invalid simulation; inspect ngspice.log')
    vout = np.interp(times, raw[:, 0], raw[:, 2])
    np.savetxt(out / 'waveforms.csv', np.column_stack((times, vin, vout)), delimiter=',', header='time_s,input_V,output_V', comments='')
    # Fixed 10 V full scale: preserves relative level between runs and avoids auto-normalizing silence.
    wavfile.write(out / 'output.wav', rate, (np.clip(vout / 10, -1, 1) * 32767).astype(np.int16))
    fig, axes = plt.subplots(2, 1, figsize=(12, 7))
    for ax in axes:
        ax.plot(times, vin, label='Input (V)', linewidth=0.8)
        ax.plot(times, vout, label='Output (V)', linewidth=0.8, alpha=0.8)
        ax.set(xlabel='Time (s)', ylabel='Voltage (V)')
        ax.grid(alpha=0.3)
        ax.legend()
    axes[0].set_title(f'Audio through approximate amplifier — {args.load:g} Ω load')
    axes[1].set_xlim(0, min(0.02, times[-1]))
    axes[1].set_title('First 20 ms (includes startup)')
    fig.tight_layout()
    fig.savefig(out / 'waveforms.png', dpi=160)
    plt.close(fig)
    rms = float(np.sqrt(np.mean(vout ** 2)))
    report = dict(source=str(args.audio.resolve()), sample_rate_Hz=int(rate), duration_s=float(times[-1]), input_peak_V=float(np.max(abs(vin))), output_peak_V=float(np.max(abs(vout))), output_rms_V=rms, mean_load_power_W=rms ** 2 / args.load, load_ohms=args.load, model='Educational approximation; not a manufacturer TDA2050 model', output_wav_full_scale_V=10)
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Saved waveform plot, CSV, output WAV and measurements to {out}')


if __name__ == '__main__':
    main()
