# PCB review before ordering

Reviewed the saved `2ndpcb.kicad_pcb` and schematic. Original design files were not changed. This is a partial design review, not a functional certification.

## Confirmed issue

C4 positive pad 1 is connected to −12 V; pad 2 is ground. Reverse the capacitor polarity in the design (positive to ground), including the PCB marking and assembly orientation. Do not order this revision as-is.

## Other items to resolve

- Rename the input net +5V to AUDIO_IN and provide clear connector signal/power markings.
- R4/C5 output series network is 4.7 ohm/100 nF. Compare with ST's split-supply reference network, 2.2 ohm/470 nF; update the component choice, footprint and power rating as needed. This is not a conclusion that the existing network necessarily oscillates.
- C3 and C6 are the 100 nF supply bypass capacitors. Their placement and the full supply-to-capacitor-to-ground loops should be tightened around U1 supply pins 3 and 5. A footprint position alone does not establish loop inductance. C3 is notably separated from U1 (roughly 20 mm between footprint origins).
- Grounds are poured on both copper layers. A common GND net alone does not prove a good audio return path. Review speaker and supply current returns so they do not share narrow paths with R1/C2/input ground. Inspect filled copper and whether top/bottom ground regions need stitching.
- U1 uses `TO-220-5_P3.4x3.7mm_StaggerOdd_Lead3.8mm_Vertical`; the TDA2050 is a Pentawatt device. Verify the exact part's lead forming, pad positions, hole size, body orientation and heatsink clearance against the manufacturer's mechanical drawing and the actual purchased part. The footprint name alone does not establish compatibility.
- U1 is placed within the board area. Plan the heatsink mechanically; do not assume the copper board alone is sufficient. Confirm tab electrical connection and insulation requirements for the actual component and mounting arrangement.
- Confirm capacitor voltage ratings, physical diameters and lead pitches; the files specify values and footprint sizes but do not establish the installed parts' ratings.

## Checks completed

- Saved board size: 60 x 35 mm, two copper layers, nominal 1.6 mm thickness.
- Supply tracks: 1.5 mm. Output track: principally 1.5 mm. No current rating is claimed without copper thickness, temperature-rise assumptions and examination of restrictions at pads/thermal reliefs.
- U1 net mapping: pin 1 noninverting input, 2 inverting input, 3 −12 V, 4 output, 5 +12 V.
- Existing KiCad reports: zero ERC violations, zero PCB DRC violations and zero unconnected pads under current project rules. Four parity warnings concern resistor value text.
- `pcb-review.svg` is a layer export for inspection, not a manufacturing output or a completed visual review.

ST reference: https://www.st.com/resource/en/datasheet/tda2050.pdf (split-supply application, layout guidance and mechanical drawing).

After corrections, refill copper zones, run ERC and PCB DRC with schematic parity again, inspect fabrication Gerbers and drill files, and compare fabrication rules to the chosen board manufacturer's capabilities. Circuit simulation cannot establish PCB oscillation, hum or thermal performance; first-article bench testing is still required.
