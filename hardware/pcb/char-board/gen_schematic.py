#!/usr/bin/env python3
"""Generate the Character Board schematic (openflaps-char.kicad_sch).

One board per character, in DrewFerg11's dowjames v5.1 outline: PY32F002A,
ULN2003A, XC6206 3.3 V LDO, one WS2812B-2020 debug LED, power LED, A3144 hall
sensor input, UART ring PREV/NEXT headers in Drew's positions, pogo pads.

Every pin gets a short wire stub and a net label, so the drawing needs no
routed wires. Re-run after changing the tables below; once the design moves
into KiCad for hand editing, this script stops being the source of truth.

    python3 gen_schematic.py && kicad-cli sch export pdf openflaps-char.kicad_sch
"""
import re
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
KLIB = Path("/usr/share/kicad/symbols")
PROJECT = "openflaps-char"
ROOT_UUID = "7d1b3f4a-6e2c-4b9d-8a10-2c3d4e5f6a7b"
STUB = 2.54

_ns = uuid.UUID("8e2c1b9f-3c58-4d9f-ab72-4f3e2d1c0a8b")


def uid(*parts):
    """Deterministic UUIDs so re-running gives a stable diff."""
    return str(uuid.uuid5(_ns, "/".join(str(p) for p in parts)))


def sexpr_block(text, start):
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    raise ValueError("unbalanced")


def lib_symbol(lib, name):
    text = (KLIB / f"{lib}.kicad_sym").read_text()
    i = text.index(f'(symbol "{name}"')
    return sexpr_block(text, i)


def flatten(lib, name, base):
    """Embed a stock symbol (or the base of a derived one) under lib:name."""
    body = lib_symbol(lib, base)
    body = body.replace(f'(symbol "{base}"', f'(symbol "{lib}:{name}"', 1)
    body = body.replace(f'(symbol "{base}_', f'(symbol "{name}_')
    return body


# ---------------------------------------------------------------- MCU symbol
# PY32F002AF15P6 (TSSOP-20), pin names from the datasheet Rev 0.4
MCU_LEFT = [  # (number, name, type)
    ("20", "VCC", "power_in"),
    ("1", "VSS", "power_in"),
    ("10", "PF2/NRST", "bidirectional"),
    ("5", "PB6/PF4/BOOT0", "input"),
    ("2", "PA13/SWDIO", "bidirectional"),
    ("3", "PA14/SWCLK", "bidirectional"),
    ("14", "PA3/USART1_RX", "bidirectional"),
    ("13", "PA2/USART1_TX", "bidirectional"),
    ("16", "PA7/SPI1_MOSI", "bidirectional"),
]
MCU_RIGHT = [(n, nm, "bidirectional") for n, nm in [
    ("6", "PA6"), ("7", "PA5"), ("8", "PF0"), ("9", "PF1"),
    ("17", "PB0"), ("11", "PA0"), ("12", "PA1"), ("15", "PA4"),
    ("19", "PB1"), ("18", "PB2"), ("4", "PB3"),
]]


def mcu_symbol():
    rows = max(len(MCU_LEFT), len(MCU_RIGHT))
    top = (rows - 1) * 2.54 / 2
    top = round(top / 1.27) * 1.27
    pins = []
    for side, lst in (("L", MCU_LEFT), ("R", MCU_RIGHT)):
        for k, (num, name, typ) in enumerate(lst):
            y = round(top - k * 2.54, 2)
            x, rot = (-17.78, 0) if side == "L" else (17.78, 180)
            pins.append(
                f'(pin {typ} line (at {x} {y} {rot}) (length 2.54) '
                f'(name "{name}" (effects (font (size 1.27 1.27)))) '
                f'(number "{num}" (effects (font (size 1.27 1.27)))))')
    h = top + 2.54
    return (
        '(symbol "openflaps:PY32F002A" (in_bom yes) (on_board yes)\n'
        f'  (property "Reference" "U" (at -15.24 {h + 1.27} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
        f'  (property "Value" "PY32F002AF15P6" (at -15.24 {-h - 1.27} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
        '  (property "Footprint" "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        '  (property "Datasheet" "https://www.lcsc.com/datasheet/lcsc_datasheet_2303271200_PUYA-PY32F002AF15P6TU_C5292059.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        '  (property "ki_description" "Puya PY32F002A, Cortex-M0+, 20 KB flash, 3 KB RAM, TSSOP-20" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        '  (symbol "PY32F002A_0_1"\n'
        f'    (rectangle (start -15.24 {h}) (end 15.24 {-h}) (stroke (width 0.254) (type default)) (fill (type background)))\n'
        '  )\n'
        '  (symbol "PY32F002A_1_1"\n    ' + "\n    ".join(pins) + "\n  )\n)")


SYMBOL_DEFS = {
    "openflaps:PY32F002A": mcu_symbol(),
    "Transistor_Array:ULN2003A": flatten("Transistor_Array", "ULN2003A", "ULN2003"),
    "Regulator_Linear:XC6206PxxxMR": flatten("Regulator_Linear", "XC6206PxxxMR", "APE8865N-12-HF-3"),
    "LED:WS2812B-2020": flatten("LED", "WS2812B-2020", "WS2812B-2020"),
    "Device:R": flatten("Device", "R", "R"),
    "Device:C": flatten("Device", "C", "C"),
    "Device:LED": flatten("Device", "LED", "LED"),
    "Connector_Generic:Conn_01x03": flatten("Connector_Generic", "Conn_01x03", "Conn_01x03"),
    "Connector_Generic:Conn_01x05": flatten("Connector_Generic", "Conn_01x05", "Conn_01x05"),
    "Connector_Generic:Conn_01x04": flatten("Connector_Generic", "Conn_01x04", "Conn_01x04"),
    "Connector:TestPoint": flatten("Connector", "TestPoint", "TestPoint"),
    "Jumper:SolderJumper_2_Open": flatten("Jumper", "SolderJumper_2_Open", "SolderJumper_2_Open"),
    "power:PWR_FLAG": flatten("power", "PWR_FLAG", "PWR_FLAG"),
}

PIN_RE = re.compile(
    r'\(pin (\w+) \w+ \(at ([-\d.]+) ([-\d.]+) (\d+)\).*?\(number "([^"]*)"', re.S)


def pins_of(lib_id):
    return {m.group(5): (float(m.group(2)), float(m.group(3)), int(m.group(4)))
            for m in PIN_RE.finditer(SYMBOL_DEFS[lib_id])}


# ------------------------------------------------------------------- parts
# (ref, lib_id, value, footprint, lcsc, (x, y), {pin: net or None for no-connect})
P = []


REF_AT = {}  # ref -> (dx, dy) for the Reference field; Value sits 2.16 mm below it


def part(ref, lib_id, value, fp, lcsc, at, nets, ref_at=None):
    P.append((ref, lib_id, value, fp, lcsc, at, nets))
    if ref_at:
        REF_AT[ref] = ref_at


FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0603_1608Metric"


# Drew's v5.1 board: PREV is a right-angle 1x4 pin header, NEXT a right-angle 1x4
# socket, both pinned GND, +5V, bus, bus. We keep his pinout and positions and
# turn the two bus pins into DATA and RETURN. Data enters at PREV.
mcu_nets = {
    "20": "+3V3", "1": "GND",
    "10": "NRST", "5": "BOOT0", "2": "SWDIO", "3": "SWCLK",
    "14": "RX", "13": "TX", "16": "LED",
    "6": "M_1", "7": "M_2", "8": "M_3", "9": "M_4",
    "17": "HALL",
    "11": "PA0", "12": "PA1", "15": "PA4", "19": "PB1", "18": "PB2", "4": "PB3",
}
part("U1", "openflaps:PY32F002A", "PY32F002AF15P6", "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
     "C5292059", (139.7, 106.68), mcu_nets, ref_at=(-12.7, -20.32))
part("C1", "Device:C", "100nF", FP_C, "C14663", (114.3, 76.2), {"1": "+3V3", "2": "GND"})
part("C2", "Device:C", "1uF", FP_C, "C15849", (124.46, 76.2), {"1": "+3V3", "2": "GND"})
part("R3", "Device:R", "10k", FP_R, "C25804", (93.98, 134.62), {"1": "BOOT0", "2": "GND"})

# Power: LDO, bulk, power LED
part("U2", "Regulator_Linear:XC6206PxxxMR", "XC6206P332MR", "Package_TO_SOT_SMD:SOT-23",
     "C5446", (71.12, 43.18), {"3": "+5V", "2": "+3V3", "1": "GND"})
part("C3", "Device:C", "1uF", FP_C, "C15849", (55.88, 55.88), {"1": "+5V", "2": "GND"})
part("C4", "Device:C", "1uF", FP_C, "C15849", (86.36, 55.88), {"1": "+3V3", "2": "GND"})
part("C5", "Device:C", "22uF 10V", "Capacitor_SMD:C_1206_3216Metric", "", (30.48, 55.88), {"1": "+5V", "2": "GND"})
part("C6", "Device:C", "100nF", FP_C, "C14663", (45.72, 55.88), {"1": "+5V", "2": "GND"})
part("R5", "Device:R", "3.3k", FP_R, "", (101.6, 43.18), {"1": "+3V3", "2": "PWR_LED"})
part("D2", "Device:LED", "green, dim", "LED_SMD:LED_0603_1608Metric", "",
     (101.6, 58.42), {"2": "PWR_LED", "1": "GND"})

# Ring link, in Drew's header positions
part("J1", "Connector_Generic:Conn_01x04", "PREV (data in)",
     "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Horizontal", "C32713263",
     (25.4, 93.98), {"1": "GND", "2": "+5V", "3": "DATA_IN", "4": "RETURN"})
part("J2", "Connector_Generic:Conn_01x04", "NEXT (data out)",
     "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Horizontal", "C2897386",
     (25.4, 129.54), {"1": "GND", "2": "+5V", "3": "DATA_OUT", "4": "RETURN"})
part("R1", "Device:R", "100", FP_R, "C22775", (55.88, 93.98), {"1": "DATA_IN", "2": "RX"})
part("R2", "Device:R", "100", FP_R, "C22775", (55.88, 129.54), {"1": "TX", "2": "DATA_OUT"})
part("JP1", "Jumper:SolderJumper_2_Open", "END OF CHAIN", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
     "", (55.88, 152.4), {"1": "DATA_OUT", "2": "RETURN"})

# Driver, motor and hall sensor
part("U3", "Transistor_Array:ULN2003A", "ULN2003A", "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
     "C5252903", (203.2, 76.2), ref_at=(-10.16, -17.78), nets={
         "1": "M_1", "2": "M_2", "3": "M_3", "4": "M_4",
         "5": "GND", "6": "GND", "7": "GND",
         "16": "COIL_1", "15": "COIL_2", "14": "COIL_3", "13": "COIL_4",
         "12": None, "11": None, "10": None, "8": "GND", "9": "+5V"})
part("J3", "Connector_Generic:Conn_01x05", "MOTOR",
     "Connector_JST:JST_XH_S5B-XH-A_1x05_P2.50mm_Horizontal", "C263757", (248.92, 76.2),
     {"1": "COIL_1", "2": "COIL_2", "3": "COIL_3", "4": "COIL_4", "5": "+5V"})
part("C7", "Device:C", "100nF", FP_C, "C14663", (233.68, 99.06), {"1": "+5V", "2": "GND"})
part("J4", "Connector_Generic:Conn_01x03", "HALL",
     "Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical", "C2320", (248.92, 129.54),
     {"1": "HALL", "2": "GND", "3": "+5V"})
part("C8", "Device:C", "100nF", FP_C, "C14663", (215.9, 139.7), {"1": "HALL", "2": "GND"})
part("R6", "Device:R", "10k", FP_R, "C25804", (205.74, 139.7), {"1": "+3V3", "2": "HALL"})

# Debug LED
part("R4", "Device:R", "33", FP_R, "", (119.38, 149.86), {"1": "LED", "2": "LED_DIN"}, ref_at=(3.81, -1.27))
part("D1", lib_id="LED:WS2812B-2020", value="WS2812B-2020-V6", fp="LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm",
     lcsc="C52917434", at=(147.32, 149.86), ref_at=(5.08, -12.7),
     nets={"3": "LED_DIN", "1": None, "4": "+5V", "2": "GND"})
part("C9", "Device:C", "100nF", FP_C, "C14663", (177.8, 149.86), {"1": "+5V", "2": "GND"})

# Pogo pads (SWD + boot) and spare I/O pads, bottom side
for k, net in enumerate(["+3V3", "GND", "SWDIO", "SWCLK", "NRST", "BOOT0"]):
    part(f"TP{k + 1}", "Connector:TestPoint", net, "TestPoint:TestPoint_Pad_D1.5mm", "",
         (30.48 + k * 12.7, 180.34), {"1": net})
for k, net in enumerate(["PA0", "PA1", "PA4", "PB1", "PB2", "PB3"]):
    part(f"TP{k + 7}", "Connector:TestPoint", net, "TestPoint:TestPoint_Pad_D1.0mm", "",
         (114.3 + k * 10.16, 180.34), {"1": net})
DNP = set()

# ERC: nets fed only by connectors need a power flag
part("#FLG1", "power:PWR_FLAG", "PWR_FLAG", "", "", (15.24, 55.88), {"1": "+5V"})
part("#FLG2", "power:PWR_FLAG", "PWR_FLAG", "", "", (21.59, 55.88), {"1": "GND"})

NOTES = [
    ((17.78, 20.32), "OpenFlaps Character Board v0.1 (draft): one per character, DrewFerg11 v5.1 outline, UART ring"),
    ((17.78, 30.48), "Power: 5 V for motor, sensor and LED; 3.3 V LDO for the MCU"),
    ((17.78, 76.2), "Ring link: Drew's headers, pins GND, +5V, DATA, RETURN. Bridge JP1 on the last board."),
    ((172.72, 50.8), "Driver, motor (pin 5 = +5 V) and A3144 hall sensor (PH: OUT, GND, 5V, as Drew)"),
    ((109.22, 134.62), "Debug LED (3.3 V data OK at 5 V)"),
    ((17.78, 167.64), "Pogo pads for SWD (bottom)"),
    ((104.14, 167.64), "Spare I/O pads (bottom)"),
]


# ---------------------------------------------------------------- emit
def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def emit():
    out = [f'(kicad_sch (version 20230121) (generator eeschema)\n  (uuid {ROOT_UUID})\n  (paper "A4")\n',
           '  (title_block (title "OpenFlaps Character Board") (rev "0.1") (comment 1 "Draft, generated by gen_schematic.py"))\n',
           "  (lib_symbols\n" + "\n".join(SYMBOL_DEFS.values()) + "\n  )\n"]
    for ref, lib_id, value, fp, lcsc, (sx, sy), nets in P:
        pins = pins_of(lib_id)
        missing = set(pins) - set(nets)
        if missing:
            raise SystemExit(f"{ref}: pins without a net or no-connect: {sorted(missing)}")
        power = ref.startswith("#")
        hide = " hide" if power else ""
        rdx, rdy = REF_AT.get(ref, (2.54, -10.16))
        props = [
            f'(property "Reference" "{ref}" (at {fmt(sx + rdx)} {fmt(sy + rdy)} 0) (effects (font (size 1.27 1.27)) (justify left){hide}))',
            f'(property "Value" "{value}" (at {fmt(sx + rdx)} {fmt(sy + rdy + 2.16)} 0) (effects (font (size 1.27 1.27)) (justify left){hide}))',
            f'(property "Footprint" "{fp}" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) hide))',
            f'(property "Datasheet" "" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) hide))',
        ]
        if lcsc:
            props.append(f'(property "LCSC" "{lcsc}" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) hide))')
        pin_uuids = " ".join(f'(pin "{n}" (uuid {uid(ref, "pin", n)}))' for n in pins)
        out.append(
            f'  (symbol (lib_id "{lib_id}") (at {fmt(sx)} {fmt(sy)} 0) (unit 1) (in_bom {"no" if power else "yes"}) '
            f'(on_board {"no" if power else "yes"}) (dnp {"yes" if ref in DNP else "no"}) (uuid {uid(ref)})\n    ' + "\n    ".join(props) +
            f'\n    {pin_uuids}\n    (instances (project "{PROJECT}" (path "/{ROOT_UUID}" (reference "{ref}") (unit 1))))\n  )\n')
        for num, (lx, ly, rot) in pins.items():
            px, py = sx + lx, sy - ly
            net = nets[num]
            if net is None:
                out.append(f'  (no_connect (at {fmt(px)} {fmt(py)}) (uuid {uid(ref, "nc", num)}))\n')
                continue
            dx, dy, ang = {0: (-1, 0, 180), 180: (1, 0, 0), 90: (0, 1, 270), 270: (0, -1, 90)}[rot]
            ex, ey = px + dx * STUB, py + dy * STUB
            just = "right" if ang in (180, 270) else "left"
            out.append(f'  (wire (pts (xy {fmt(px)} {fmt(py)}) (xy {fmt(ex)} {fmt(ey)})) (stroke (width 0) (type default)) (uuid {uid(ref, "w", num)}))\n')
            out.append(f'  (label "{net}" (at {fmt(ex)} {fmt(ey)} {ang}) (fields_autoplaced) '
                       f'(effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid {uid(ref, "l", num)}))\n')
    for k, ((x, y), text) in enumerate(NOTES):
        out.append(f'  (text "{text}" (at {fmt(x)} {fmt(y)} 0) (effects (font (size 1.778 1.778) bold) (justify left bottom)) (uuid {uid("note", k)}))\n')
    out.append('  (sheet_instances (path "/" (page "1")))\n)\n')
    (HERE / f"{PROJECT}.kicad_sch").write_text("".join(out))


def emit_library():
    (HERE / "openflaps.kicad_sym").write_text(
        "(kicad_symbol_lib (version 20220914) (generator gen_schematic)\n"
        + SYMBOL_DEFS["openflaps:PY32F002A"].replace('"openflaps:PY32F002A"', '"PY32F002A"', 1)
        + "\n)\n")
    (HERE / "sym-lib-table").write_text(
        '(sym_lib_table\n  (lib (name "openflaps")(type "KiCad")(uri "${KIPRJMOD}/openflaps.kicad_sym")(options "")(descr "OpenFlaps parts"))\n)\n')


if __name__ == "__main__":
    emit()
    emit_library()
    print(f"wrote {PROJECT}.kicad_sch with {len(P)} parts")
