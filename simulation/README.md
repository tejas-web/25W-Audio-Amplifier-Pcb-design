# Amplifier simulation and checks

## Audio file input and waveform output

Run the audio simulation with your own WAV recording:

```sh
PYTHONNOUSERSITE=1 python3 simulation/audio_simulation.py /path/to/music.wav
```

Open `simulation/audio_results/waveforms.png` for input/output waveforms and a
20 ms detail view. The same folder contains `waveforms.csv` (seconds and volts),
`output.wav`, `results.json`, and `ngspice.log`.

The default simulates the first second, mixes stereo to mono, and scales the
selected audio to 0.1 V peak into an 8 Ω load. For another segment or clipping:

```sh
PYTHONNOUSERSITE=1 python3 simulation/audio_simulation.py /path/to/music.wav --start 10 --duration 2 --input-peak 0.5 --load 4
```

Use `--out /path/to/results` to retain separate runs. Input supports PCM and float
WAV; convert other audio formats to WAV first. Longer segments take more time
because this runs a SPICE transient with the audio samples as a PWL voltage
source. Simulation starts from the selected segment's DC operating point;
startup can affect the first part of the result. Input samples are linearly
interpolated, without a DAC reconstruction filter.

Output WAV uses a fixed 10 V = full-scale mapping for listening; use the CSV for
actual voltages. This reuses `small_8ohm.cir` connectivity and
`amplifier_approx.lib`, with the same model limitations described below. It is
an approximation of the amplifier, not a validated TDA2050 device simulation.
Requires the existing numpy, scipy, matplotlib and libngspice installation.

The original schematic and PCB have not been edited. These results apply to the saved `25W-Audio-Amplifier-Pcb-design` files, not the autosave files. The circuit uses a TDA2050 with split ±12 V rails.

## Findings to resolve before powering the PCB

1. **C4 (220 µF) is reversed.** Its positive pin 1 is on −12 V and its negative pin 2 is on ground, in both the schematic and PCB. The positive terminal must face ground and the negative terminal −12 V. Correct the schematic and PCB polarity markings/placement together. SPICE ideal capacitors do not detect reverse-polarity damage.
2. **The audio input is named +5V.** J2 pin 2 feeds C1; J2 pin 1 is ground. Treat this as an audio signal input, not a power connection. Rename the net AUDIO_IN. C1 is polarized even though the input DC bias is unspecified; consider a suitable nonpolar coupling capacitor for a ground-centred source.
3. **Output stability network differs from the datasheet.** Your R4 is 4.7 Ω and C5 is 100 nF. ST's split-supply example uses 2.2 Ω and 470 nF for this series output-to-ground network. Consider adopting ST's values and a suitable resistor power rating, then update PCB/BOM values. Component reference numbers in ST's drawing differ from this project. This approximate model cannot determine stability.
4. KiCad ERC: **0 violations**. PCB DRC: **0 violations and 0 unconnected pads** under the current project rules. Four schematic/PCB parity warnings are resistor value labels on R1–R4. Synchronize the PCB from the schematic and review the resulting changes. These checks do not establish thermal performance, routing quality, or manufacturability under another fabricator's rules.

Reference: ST TDA2050 datasheet, split-supply circuit and recommendations, pages 4–6:
https://www.st.com/resource/en/datasheet/tda2050.pdf

## What was actually simulated

`schematic.net.xml` was exported directly from the saved schematic. The runner uses its resistor/capacitor values and pin connectivity, replaces connectors with a test source and load, and adds a behavioural amplifier. No manufacturer simulation model was supplied in the project.

**`amplifier_approx.lib` is an educational approximation, not an ST TDA2050 model.** It uses 100,000 V/V small-signal open-loop gain, a smooth tanh limiter fixed at ±10 V (assumed headroom for the ±12 V experiment), and 0.1 Ω output resistance. Changing supply values does not change this limiter. It has no frequency compensation, slew rate, current limit, supply-current model, thermal shutdown, realistic distortion, noise or PCB parasitics. It cannot validate oscillation, maximum power, heatsinking, supply loading or protection. AC high-frequency behaviour is particularly idealized.

Tests run for both 8 Ω and 4 Ω resistive loads:

- DC operating point: zero nominal output offset, because the model has no input offset.
- AC sweep: 2 Hz to 200 kHz, 1 V AC test source (linearized analysis).
- Transient: 1 kHz sine, 100 mV peak input; 100 ms total, last 20 ms saved, maximum step 2 µs.
- Overdrive: 500 mV peak input, visibly limited output; these are distorted waveforms, not clean rated power.

At 1 kHz, gain is about **33.34 V/V (30.46 dB)**. With 100 mV peak input, output is about **3.335 V peak / 2.357 V RMS**, giving **0.695 W into 8 Ω** or **1.389 W into 4 Ω**. This agrees with the feedback estimate 1 + 22000/680 = 33.35. It confirms the basic signal-path wiring in this approximation, not complete hardware operation.

See `response.png`, `results.json`, raw `*_ac.txt` / `*_tran.txt` / `*_op.txt`, and `ngspice.log`.

## Re-run here

The installed ngspice shared library is used directly; no ngspice executable or extra package installation is required. Run from the project directory:

```sh
kicad-cli sch export netlist --format kicadxml -o simulation/schematic.net.xml 25W-Audio-Amplifier-Pcb-design.kicad_sch
PYTHONNOUSERSITE=1 MPLCONFIGDIR=/tmp/pcb-simulation-mpl python3 simulation/run_simulation.py
```

The environment variable avoids an existing user NumPy / system Matplotlib incompatibility. The runner requires numpy and matplotlib. It maps this project's existing net names, so update its aliases if you rename nets. Re-export after schematic changes. Check ERC/DRC again after corrections.

## KiCad interactive simulation setup

Work on a separate simulation copy of the schematic. The exported `.cir` files also contain the full test circuit and can be opened in an ngspice-compatible simulator.

1. In U1's Simulation Model editor, choose a SPICE subcircuit model, select `amplifier_approx.lib`, and select `AMP_APPROX`. Its model pin order is **plus, minus, vp, vn, out**. Map these to TDA2050 physical pins **1, 2, 5, 3, 4**, respectively. This model is only for the approximate checks above. Replace it with a validated TDA2050 model for more meaningful device behaviour, checking that model's pin order independently.
2. Add a DC source from +12V to ground set to +12 V, and another from −12V to ground set to −12 V. Both source positive terminals face their named rail. Power symbols alone do not generate simulated power.
3. Add a voltage source between J2 pin 2 and ground: DC 0 V, sine offset 0 V, amplitude 0.1 V peak, frequency 1 kHz, AC magnitude 1 V. Remove/rename the +5V power label on the simulation copy; it is a signal node.
4. Add an 8 Ω resistor from J1 pin 1 to ground as the speaker test load. Repeat with 4 Ω if that is the intended load. A resistive load is only a first approximation of a speaker.
5. Exclude connector symbols and power flags from simulation; ensure resistors/capacitors have their normal R/C simulation models and suitable SPICE values (1u, 22u, 100n, 220u, 22k, 680, 4.7).
6. Open Simulator. Run operating point first, then AC (decade, 100 points/decade, 2 Hz–200 kHz), then transient (step 2 µs, stop 100 ms). Plot input and output; evaluate steady-state behaviour after 80 ms. Increase the input to 0.5 V peak to see overdrive.

Before claiming the built amplifier works, fix the reversed capacitor and verify real DC output offset, supply current, clipping and oscillation with appropriate bench equipment, a dummy load and the intended heatsink. The simulation cannot replace those measurements.
