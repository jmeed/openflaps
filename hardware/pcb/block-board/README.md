# Block Board (v0.2 draft)

> Shelved (2026-11-27): the build moved to DrewFerg11's enclosures, which take one board
> per character. See [`../char-board/`](../char-board/). Kept for the circuit and pin map.

A low-cost replacement for the Controller and Daisy Chain boards: **one board per
4 characters**, driving four 28BYJ-48 steppers from one Puya PY32F030K28T6. Boards
are chained with a 3.3 V UART ring to a Raspberry Pi. Design notes and costs:
the feasibility study doc (linked from the PR).

Status: **schematic only**, not yet laid out or built. Nothing here replaces the
existing boards yet.

## Files

| File | What it is |
|---|---|
| `openflaps-block.kicad_sch` | The schematic (KiCad 7 format; opens in KiCad 8 and 9) |
| `Schematic_Block_Board.pdf` | The schematic as a PDF |
| `openflaps.kicad_sym`, `sym-lib-table` | Project symbol library (the PY32F030K28T6 symbol) |
| `gen_schematic.py` | Generates the schematic from the part and net tables in it |

The schematic is generated: every pin has a short stub and a net label instead
of drawn wires. Edit the tables in `gen_schematic.py` and re-run it while the
design is still moving; once the layout starts in KiCad, the `.kicad_sch` becomes
the source of truth and the script can be deleted.

```bash
python3 gen_schematic.py
kicad-cli sch export pdf -o Schematic_Block_Board.pdf openflaps-block.kicad_sch
```

## Circuit

- **MCU** PY32F030K28T6, LQFP-32, at 3.3 V from an XC6206P332MR LDO. Pins 1 and 17
  go to 3.3 V and 32 to GND, so either LQFP-32 pinout in the datasheet (K1 or K2)
  works; the firmware must leave PB2 and PB8 as inputs.
- **Motors**: four ULN2003A, inputs from the MCU, outputs to JST XH 5-pin stepper
  connectors (pin 5 = +5 V, the motor's red wire), COM to +5 V for the flyback clamp.
- **Hall sensors (homing)**: one JST PH 3-pin header per character (B3B-PH-K, C2320), pinout
  `OUT GND +5V` (same order as DrewFerg11's board, so his sensor leads plug in), for an A3144/WSH130 unipolar hall sensor and a drum magnet (DrewFerg11
  mechanics). The sensor runs on 5 V (A3144 needs 4.5 V or more); its open-collector output
  is pulled up to 3.3 V with 10k, so the MCU never sees 5 V. 100 nF filter on each input.
- **Ring link**: identical 6-pin JST XH at both ends, pinout `+5V GND DATA RETURN GND +5V`.
  DATA_IN goes to USART1 RX, USART1 TX to DATA_OUT, each through 100 ohm. RETURN is a
  straight trace. Bridge **JP1** on the last board of a chain to loop DATA back on RETURN.
  The board works turned 180 degrees.
- **Debug lights**: four WS2812B-2020-V6, one per character, on 5 V, data from SPI1 MOSI
  (PB5) through 33 ohm; a dim green power LED on 3.3 V.
- **Expansion header J11** (1x6 2.54 mm, not fitted): 3.3 V, PA10, RX, TX, LED data, GND, for a logic analyser or a future add-on.
- **Flashing**: SWDIO, SWCLK, NRST, BOOT0, 3.3 V and GND on pogo pads. BOOT0 has a 10k
  pull-down.

## MCU pin map

| Pin | Port | Net |
|---|---|---|
| 2, 3, 5, 6 | PF0, PF1, PF3, PA0 | Motor 1 coils 1-4 |
| 7, 10, 11, 12 | PA1, PA4, PA5, PA6 | Motor 2 coils 1-4 |
| 13, 14, 15, 18 | PA7, PB0, PB1, PA8 | Motor 3 coils 1-4 |
| 21, 22, 25, 26 | PA11, PA12, PA15, PB3 | Motor 4 coils 1-4 |
| 27, 29, 30, 19 | PB4, PB6, PB7, PA9 | Hall sensors 1-4 (active low) |
| 9, 8 | PA3, PA2 | USART1 RX, TX (AF1) |
| 28 | PB5 | SPI1 MOSI (AF0), WS2812 data |
| 23, 24, 4, 31 | PA13, PA14, PF2, PF4 | SWDIO, SWCLK, NRST, BOOT0 |
| 20 | PA10 | spare, on the expansion header J11 |

The motor pins are grouped by package side for routing and may be reshuffled
during layout.

## Not checked yet

- ERC: the KiCad 7 command line used to generate this has no `sch erc`. Net
  connectivity was checked from the exported netlist (no dangling nets). Run
  **Inspect > Electrical Rules Checker** in KiCad before layout.
- LCSC numbers are filled in for the parts already known (see the `LCSC` field);
  the 470 uF cap, the 6-pin link connectors, the 3.3k, 33 ohm and green LED still
  need picking.
