#!/usr/bin/env python3
"""Generate the v0.1 Block Board schematic (openflaps-block.kicad_sch).

One board per 4 characters: PY32F030K28T6, 4x ULN2003A, XC6206 3.3 V LDO,
4x WS2812B-2020 debug LEDs, power LED, UART ring IN/OUT connectors, pogo pads.

Every pin gets a short wire stub and a net label, so the drawing needs no
routed wires. Re-run after changing the tables below; once the design moves
into KiCad for hand editing, this script stops being the source of truth.

    python3 gen_schematic.py && kicad-cli sch erc openflaps-block.kicad_sch
"""
import re
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
KLIB = Path("/usr/share/kicad/symbols")
PROJECT = "openflaps-block"
ROOT_UUID = "5c0a6e2e-8a52-4d0c-9c3b-0f1a2b3c4d5e"
STUB = 2.54

_ns = uuid.UUID("6f1d0a8e-2b47-4c8e-9a61-3e2f1d0c9b7a")


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
MCU_LEFT = [  # (number, name, type)
    ("1", "VCC", "power_in"),
    ("17", "VCC/PB2", "power_in"),
    ("16", "VSS", "power_in"),
    ("32", "VSS/PB8", "power_in"),
    ("4", "PF2/NRST", "bidirectional"),
    ("31", "PF4/BOOT0", "input"),
    ("23", "PA13/SWDIO", "bidirectional"),
    ("24", "PA14/SWCLK", "bidirectional"),
    ("9", "PA3/USART1_RX", "bidirectional"),
    ("8", "PA2/USART1_TX", "bidirectional"),
    ("28", "PB5/SPI1_MOSI", "bidirectional"),
    ("20", "PA10", "bidirectional"),
]
MCU_RIGHT = [(n, nm, "bidirectional") for n, nm in [
    ("2", "PF0"), ("3", "PF1"), ("5", "PF3"), ("6", "PA0"),
    ("7", "PA1"), ("10", "PA4"), ("11", "PA5"), ("12", "PA6"),
    ("13", "PA7"), ("14", "PB0"), ("15", "PB1"), ("18", "PA8"),
    ("21", "PA11"), ("22", "PA12"), ("25", "PA15"), ("26", "PB3"),
    ("27", "PB4"), ("29", "PB6"), ("30", "PB7"), ("19", "PA9"),
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
        '(symbol "openflaps:PY32F030K28T6" (in_bom yes) (on_board yes)\n'
        f'  (property "Reference" "U" (at -15.24 {h + 1.27} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
        f'  (property "Value" "PY32F030K28T6" (at -15.24 {-h - 1.27} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
        '  (property "Footprint" "Package_QFP:LQFP-32_7x7mm_P0.8mm" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        '  (property "Datasheet" "https://datasheet.lcsc.com/datasheet/pdf/b50f46ebe50d9b5ffc8bba3570f14d78.pdf?productCode=C3018720" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        '  (property "ki_description" "Puya PY32F030, Cortex-M0+, 64 KB flash, 8 KB RAM, LQFP-32 (K2 pinout; pins 1/17/32 wired so a K1 part also works)" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        '  (symbol "PY32F030K28T6_0_1"\n'
        f'    (rectangle (start -15.24 {h}) (end 15.24 {-h}) (stroke (width 0.254) (type default)) (fill (type background)))\n'
        '  )\n'
        '  (symbol "PY32F030K28T6_1_1"\n    ' + "\n    ".join(pins) + "\n  )\n)")


SYMBOL_DEFS = {
    "openflaps:PY32F030K28T6": mcu_symbol(),
    "Transistor_Array:ULN2003A": flatten("Transistor_Array", "ULN2003A", "ULN2003"),
    "Regulator_Linear:XC6206PxxxMR": flatten("Regulator_Linear", "XC6206PxxxMR", "APE8865N-12-HF-3"),
    "LED:WS2812B-2020": flatten("LED", "WS2812B-2020", "WS2812B-2020"),
    "Device:R": flatten("Device", "R", "R"),
    "Device:C": flatten("Device", "C", "C"),
    "Device:C_Polarized": flatten("Device", "C_Polarized", "C_Polarized"),
    "Device:LED": flatten("Device", "LED", "LED"),
    "Connector_Generic:Conn_01x02": flatten("Connector_Generic", "Conn_01x02", "Conn_01x02"),
    "Connector_Generic:Conn_01x05": flatten("Connector_Generic", "Conn_01x05", "Conn_01x05"),
    "Connector_Generic:Conn_01x06": flatten("Connector_Generic", "Conn_01x06", "Conn_01x06"),
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

# MCU, U1
mcu_nets = {
    "1": "+3V3", "17": "+3V3", "16": "GND", "32": "GND",
    "4": "NRST", "31": "BOOT0", "23": "SWDIO", "24": "SWCLK",
    "9": "RX", "8": "TX", "28": "LED_SPI", "20": "PA10",
    # motor coils: Mn_1..Mn_4 go to ULN2003 inputs I1..I4
    "2": "M1_1", "3": "M1_2", "5": "M1_3", "6": "M1_4",
    "7": "M2_1", "10": "M2_2", "11": "M2_3", "12": "M2_4",
    "13": "M3_1", "14": "M3_2", "15": "M3_3", "18": "M3_4",
    "21": "M4_1", "22": "M4_2", "25": "M4_3", "26": "M4_4",
    # limit switches, internal pull-ups
    "27": "SW1", "29": "SW2", "30": "SW3", "19": "SW4",
}
part("U1", "openflaps:PY32F030K28T6", "PY32F030K28T6", "Package_QFP:LQFP-32_7x7mm_P0.8mm",
     "C3018720", (165.1, 139.7), mcu_nets, ref_at=(-15.24, -31.75))
part("C1", "Device:C", "100nF", FP_C, "C14663", (127.0, 101.6), {"1": "+3V3", "2": "GND"})
part("C2", "Device:C", "1uF", FP_C, "C15849", (137.16, 101.6), {"1": "+3V3", "2": "GND"})
part("R3", "Device:R", "10k", FP_R, "C25804", (127.0, 177.8), {"1": "BOOT0", "2": "GND"})

# Power: LDO, bulk, power LED
part("U2", "Regulator_Linear:XC6206PxxxMR", "XC6206P332MR", "Package_TO_SOT_SMD:SOT-23",
     "C5446", (101.6, 50.8), {"3": "+5V", "2": "+3V3", "1": "GND"})
part("C3", "Device:C", "1uF", FP_C, "C15849", (83.82, 63.5), {"1": "+5V", "2": "GND"})
part("C4", "Device:C", "1uF", FP_C, "C15849", (119.38, 63.5), {"1": "+3V3", "2": "GND"})
part("C5", "Device:C_Polarized", "470uF 10V", "Capacitor_SMD:CP_Elec_6.3x7.7", "",
     (53.34, 63.5), {"1": "+5V", "2": "GND"})
part("C6", "Device:C", "100nF", FP_C, "C14663", (71.12, 63.5), {"1": "+5V", "2": "GND"})
part("R5", "Device:R", "3.3k", FP_R, "", (134.62, 50.8), {"1": "+3V3", "2": "PWR_LED"})
part("D5", "Device:LED", "green, dim", "LED_SMD:LED_0603_1608Metric", "",
     (134.62, 66.04), {"2": "PWR_LED", "1": "GND"})

# Ring link
LINK_FP = "Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical"
part("J1", "Connector_Generic:Conn_01x06", "LINK IN", LINK_FP, "",
     (30.48, 101.6), {"1": "+5V", "2": "GND", "3": "DATA_IN", "4": "RETURN", "5": "GND", "6": "+5V"})
part("J2", "Connector_Generic:Conn_01x06", "LINK OUT", LINK_FP, "",
     (30.48, 139.7), {"1": "+5V", "2": "GND", "3": "DATA_OUT", "4": "RETURN", "5": "GND", "6": "+5V"})
part("R1", "Device:R", "100", FP_R, "C22775", (63.5, 101.6), {"1": "DATA_IN", "2": "RX"})
part("R2", "Device:R", "100", FP_R, "C22775", (63.5, 139.7), {"1": "TX", "2": "DATA_OUT"})
part("JP1", "Jumper:SolderJumper_2_Open", "END OF CHAIN", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
     "", (63.5, 162.56), {"1": "DATA_OUT", "2": "RETURN"})

# Drivers, motor and switch connectors
for n in range(1, 5):
    y = 40.64 + (n - 1) * 50.8
    part(f"U{n + 2}", lib_id="Transistor_Array:ULN2003A", value="ULN2003A", fp="Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
         lcsc="C5252903", at=(264.16, y), ref_at=(-10.16, -17.78), nets={
             "1": f"M{n}_1", "2": f"M{n}_2", "3": f"M{n}_3", "4": f"M{n}_4",
             "5": "GND", "6": "GND", "7": "GND",
             "16": f"COIL{n}_1", "15": f"COIL{n}_2", "14": f"COIL{n}_3", "13": f"COIL{n}_4",
             "12": None, "11": None, "10": None, "8": "GND", "9": "+5V"})
    part(f"J{n + 2}", "Connector_Generic:Conn_01x05", f"MOTOR {n}",
         "Connector_JST:JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical", "C157991", (309.88, y),
         {"1": f"COIL{n}_1", "2": f"COIL{n}_2", "3": f"COIL{n}_3", "4": f"COIL{n}_4", "5": "+5V"})
    part(f"C{n + 6}", "Device:C", "100nF", FP_C, "C14663", (294.64, y + 25.4), {"1": "+5V", "2": "GND"})
    part(f"J{n + 6}", "Connector_Generic:Conn_01x02", f"SWITCH {n}",
         "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "C5360898", (350.52, y),
         {"1": f"SW{n}", "2": "GND"})
    part(f"C{n + 10}", "Device:C", "100nF", FP_C, "C14663", (365.76, y + 15.24), {"1": f"SW{n}", "2": "GND"})

# Debug LEDs, one per character, chained
part("R4", "Device:R", "33", FP_R, "", (50.8, 223.52), {"1": "LED_SPI", "2": "LED_D1"}, ref_at=(3.81, -1.27))
for n in range(1, 5):
    x = 76.2 + (n - 1) * 40.64
    part(f"D{n}", lib_id="LED:WS2812B-2020", value="WS2812B-2020-V6", fp="LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", lcsc="C52917434", at=(x, 223.52), ref_at=(5.08, -12.7), nets={"3": f"LED_D{n}", "1": f"LED_D{n + 1}" if n < 4 else None,
                                    "4": "+5V", "2": "GND"})
    part(f"C{n + 14}", "Device:C", "100nF", FP_C, "C14663", (x + 15.24, 241.3), {"1": "+5V", "2": "GND"})

# Pogo pads (SWD + boot), bottom side
for k, net in enumerate(["+3V3", "GND", "SWDIO", "SWCLK", "NRST", "BOOT0"]):
    part(f"TP{k + 1}", "Connector:TestPoint", net, "TestPoint:TestPoint_Pad_D1.5mm", "",
         (152.4 + k * 12.7, 198.12), {"1": net})

# Expansion header, not fitted: the spare pin plus the signals worth probing
part("J11", "Connector_Generic:Conn_01x06", "EXPANSION (DNP)",
     "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", "", (101.6, 180.34),
     {"1": "+3V3", "2": "PA10", "3": "RX", "4": "TX", "5": "LED_SPI", "6": "GND"})
DNP = {"J11"}

# ERC: nets fed only by connectors need a power flag
part("#FLG1", "power:PWR_FLAG", "PWR_FLAG", "", "", (30.48, 63.5), {"1": "+5V"})
part("#FLG2", "power:PWR_FLAG", "PWR_FLAG", "", "", (40.64, 63.5), {"1": "GND"})

NOTES = [
    ((22.86, 22.86), "OpenFlaps Block Board v0.1 (draft): one board per 4 characters, UART ring, 3.3 V logic"),
    ((22.86, 86.36), "Ring link. Same mirrored pinout at both ends. Bridge JP1 on the last board only."),
    ((22.86, 38.1), "Power: 5 V for motors and LEDs, 3.3 V LDO for the MCU"),
    ((127.0, 81.28), "MCU: pins 1/17 to 3V3, 32 to GND, so K1 or K2 pinout works"),
    ((246.38, 17.78), "Motor drivers, stepper connectors (pin 5 = +5 V, red) and limit switches"),
    ((22.86, 205.74), "Debug LEDs, one per character (WS2812B-2020-V6, 3.3 V data OK at 5 V supply)"),
    ((147.32, 182.88), "Pogo pads for SWD flashing (bottom side)"),
]


# ---------------------------------------------------------------- emit
def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def emit():
    out = [f'(kicad_sch (version 20230121) (generator eeschema)\n  (uuid {ROOT_UUID})\n  (paper "A3")\n',
           '  (title_block (title "OpenFlaps Block Board") (rev "0.1") (comment 1 "Draft, generated by gen_schematic.py"))\n',
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
        + SYMBOL_DEFS["openflaps:PY32F030K28T6"].replace('"openflaps:PY32F030K28T6"', '"PY32F030K28T6"', 1)
        + "\n)\n")
    (HERE / "sym-lib-table").write_text(
        '(sym_lib_table\n  (lib (name "openflaps")(type "KiCad")(uri "${KIPRJMOD}/openflaps.kicad_sym")(options "")(descr "OpenFlaps parts"))\n)\n')


if __name__ == "__main__":
    emit()
    emit_library()
    print(f"wrote {PROJECT}.kicad_sch with {len(P)} parts")
