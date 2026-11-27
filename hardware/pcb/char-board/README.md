# Character Board (v0.1 draft)

One board per character, a drop-in replacement for the dowjames v5.1 module board in
[DrewFerg11/Split-Flap-Display](https://github.com/DrewFerg11/Split-Flap-Display). It
keeps Drew's outline and puts PREV, NEXT, MOTOR and HALL exactly where his board has
them (copied from his Edge_Cuts gerber and drill file), so it sits in his enclosure and
plugs into its neighbours the same way. It replaces I2C with the OpenFlaps UART ring:
no DIP switches, no address limit, addresses come from position in the chain.

Status: schematic drafted, outline and placement done, **not routed, not ERC/DRC
checked**. Not ordered.

| File | What |
|---|---|
| `gen_schematic.py` | Generates the schematic and symbol library |
| `gen_pcb.py` | Generates the board: Drew's outline, footprints placed, pads netted, no tracks |
| `openflaps-char.kicad_sch` / `.kicad_pcb` / `.kicad_pro` | KiCad project (opens in KiCad 7 or newer) |
| `Schematic_Character_Board.pdf`, `placement.png` | Renders |

Rebuild:

```bash
python3 gen_schematic.py
kicad-cli sch export pdf -o Schematic_Character_Board.pdf openflaps-char.kicad_sch
kicad-cli sch export netlist --format kicadxml -o openflaps-char.xml openflaps-char.kicad_sch
python3 gen_pcb.py   # needs KiCad's pcbnew Python module
```

Once routing starts by hand in KiCad, the `.kicad_pcb` becomes the source of truth and
`gen_pcb.py` should not be re-run over it.

## Circuit

- **MCU** PY32F002AF15P6 (TSSOP-20, LCSC C5292059) at 3.3 V from an XC6206P332MR LDO.
- **Motor**: ULN2003A, inputs PA6, PA5, PF0, PF1, outputs to a horizontal JST XH 5-pin
  (S5B-XH-A, C263757, as Drew), pin 5 = +5 V (red wire). COM to +5 V.
- **Hall sensor** (homing): JST PH 3-pin (C2320, as Drew), pinout `OUT GND +5V` in Drew's
  order so his A3144/WSH130 leads plug in. The sensor runs on 5 V; its open-collector
  output is pulled up to 3.3 V with 10k, so the MCU never sees 5 V. Active low on PB0,
  100 nF filter.
- **Ring link**: Drew's right-angle 1x4 PREV header (C32713263) and NEXT socket
  (C2897386), same positions and same pins 1-2 (GND, +5V). Pins 3-4 change from I2C to
  DATA and RETURN. Data enters at PREV (PA3, USART1 RX via 100 ohm) and leaves at NEXT
  (PA2, TX via 100 ohm). RETURN is a straight trace. Bridge **JP1** on the last board of a
  row to loop DATA back on RETURN.
- **Debug light**: one WS2812B-2020-V6 on 5 V, data from PA7 via 33 ohm (SPI1 MOSI if
  the AF table allows, otherwise bit-banged: one LED is about 30 us). Dim green power LED.
- **Flashing**: SWDIO, SWCLK, NRST, BOOT0, 3.3 V and GND on 1.5 mm pogo pads on the
  bottom, in a 2.54 mm row. BOOT0 has a 10k pull-down.
- **Spare I/O** on 1 mm bottom pads: PA0, PA1, PA4, PB1, PB2, PB3.

## MCU pin map

| Pin | Port | Net |
|---|---|---|
| 6, 7, 8, 9 | PA6, PA5, PF0, PF1 | Motor coils 1-4 (PF0/PF1 free because the internal oscillator is used) |
| 17 | PB0 | Hall sensor, active low |
| 14, 13 | PA3, PA2 | USART1 RX, TX (AF1) |
| 16 | PA7 | WS2812 data |
| 2, 3, 10, 5 | PA13, PA14, PF2, PF4 | SWDIO, SWCLK, NRST, BOOT0 |
| 11, 12, 15, 19, 18, 4 | PA0, PA1, PA4, PB1, PB2, PB3 | Spare pads |
| 20, 1 | VCC, VSS | 3.3 V, GND |

## Not yet checked

- Routing, then ERC and DRC in KiCad 8 or 9.
- PA7 as SPI1 MOSI on the PY32F002A (AF table); PA2/PA3 as USART1 AF1.
- Drew's board has no mounting holes; this one copies that. Check how it is held in the
  enclosure (and the narrower dual-display enclosure from MakerWorld) on a real build.
- LCSC numbers still to pick: 22 uF 1206 bulk cap, 3.3k, 33 ohm, green 0603 LED.
- One power pin per side on the 4-pin link: fine for one motor per board (Drew does the
  same), but inject 5 V every few modules on a long row.
