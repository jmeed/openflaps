#!/usr/bin/env python3
"""Generate the Character Board PCB (openflaps-char.kicad_pcb): outline and placement.

The outline and the four connectors (PREV, NEXT, MOTOR, HALL) copy DrewFerg11's
dowjames v5.1 board exactly, taken from its Edge_Cuts gerber and drill file, so
the board drops into his enclosure and plugs into his neighbours the same way.
Everything else is placed, not routed: routing is the next step, in KiCad.

Needs KiCad's pcbnew Python module and a netlist exported from the schematic:

    python3 gen_schematic.py
    kicad-cli sch export netlist --format kicadxml -o openflaps-char.xml openflaps-char.kicad_sch
    python3 gen_pcb.py
"""
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
FPLIB = Path("/usr/share/kicad/footprints")
MM = pcbnew.FromMM

# Drew's v5.1 Edge_Cuts, gerber coordinates (1e-6 mm, Y up), verbatim from
# custom-pcb/dowjames-v5.1 SplitFlap-Edge_Cuts.gm1 in DrewFerg11/Split-Flap-Display.
EDGE_GERBER = """
G01* X178500000Y-90000000D02* X178000000Y-90000000D01*
X176500000Y-91500000D02* G02* X178000000Y-90000000I1500000J0D01*
G01* X175000000Y-94500000D02* X146500000Y-94500000D01*
X175000000Y-59500000D02* G02* X176500000Y-61000000I0J-1500000D01*
G01* X180000000Y-88500000D02* G02* X178500000Y-90000000I-1500000J0D01*
G01* X145000000Y-61060660D02* G02* X146560660Y-59500000I1560700J-40D01*
G01* X178000000Y-68310619D02* G02* X176499981Y-66810660I0J1500019D01*
G01* X145000000Y-61060660D02* X145000000Y-93000000D01*
X176500000Y-93000000D02* G02* X175000000Y-94500000I-1500000J0D01*
G01* X176500041Y-66810660D02* X176500000Y-61000000D01*
X146560700Y-59500000D02* X175000000Y-59500000D01*
X178500000Y-68321654D02* X178000000Y-68310660D01*
X146500000Y-94500000D02* G02* X145000000Y-93000000I0J1500000D01*
G01* X176500000Y-91500000D02* X176500000Y-93000000D01*
X180000000Y-69821654D02* X180000000Y-88500000D01*
X178500000Y-68321654D02* G02* X179999946Y-69821654I0J-1499946D01*
"""


# ref: (footprint library, footprint, x, y, rotation, side). KiCad coordinates
# (Y down). J1-J4 sit at Drew's positions: pin 1 from his drill file.
PLACE = {
    "J1": ("Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Horizontal", 175.5, 80.25, 0, "F"),
    "J2": ("Connector_PinSocket_2.54mm", "PinSocket_1x04_P2.54mm_Horizontal", 154.65, 80.25, 0, "F"),
    "J3": ("Connector_JST", "JST_XH_S5B-XH-A_1x05_P2.50mm_Horizontal", 158.25, 75.169, 180, "F"),
    "J4": ("Connector_JST", "JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical", 164.25, 91.3, 180, "F"),
    "U3": ("Package_SO", "SOIC-16_3.9x9.9mm_P1.27mm", 166.5, 71.6, 90, "F"),
    "U1": ("Package_SO", "TSSOP-20_4.4x6.5mm_P0.65mm", 168.3, 84.0, 0, "F"),
    "U2": ("Package_TO_SOT_SMD", "SOT-23", 172.9, 62.6, 0, "F"),
    "C3": ("Capacitor_SMD", "C_0603_1608Metric", 169.6, 62.6, 90, "F"),
    "C4": ("Capacitor_SMD", "C_0603_1608Metric", 175.4, 66.6, 90, "F"),
    "C5": ("Capacitor_SMD", "C_1206_3216Metric", 163.5, 62.0, 0, "F"),
    "C6": ("Capacitor_SMD", "C_0603_1608Metric", 166.9, 62.6, 90, "F"),
    "C7": ("Capacitor_SMD", "C_0603_1608Metric", 163.4, 65.9, 0, "F"),
    "C1": ("Capacitor_SMD", "C_0603_1608Metric", 172.3, 77.0, 90, "F"),
    "C2": ("Capacitor_SMD", "C_0603_1608Metric", 170.6, 77.0, 90, "F"),
    "R3": ("Resistor_SMD", "R_0603_1608Metric", 163.0, 80.0, 90, "F"),
    "R1": ("Resistor_SMD", "R_0603_1608Metric", 172.9, 90.6, 0, "F"),
    "R2": ("Resistor_SMD", "R_0603_1608Metric", 158.4, 85.3, 90, "F"),
    "JP1": ("Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", 151.0, 91.6, 0, "F"),
    "R6": ("Resistor_SMD", "R_0603_1608Metric", 167.8, 89.6, 90, "F"),
    "C8": ("Capacitor_SMD", "C_0603_1608Metric", 169.4, 89.6, 90, "F"),
    "R4": ("Resistor_SMD", "R_0603_1608Metric", 174.4, 73.4, 0, "F"),
    "D1": ("LED_SMD", "LED_WS2812B-2020_PLCC4_2.0x2.0mm", 174.4, 70.4, 0, "F"),
    "C9": ("Capacitor_SMD", "C_0603_1608Metric", 173.2, 66.6, 90, "F"),
    "R5": ("Resistor_SMD", "R_0603_1608Metric", 173.5, 92.8, 0, "F"),
    "D2": ("LED_SMD", "LED_0603_1608Metric", 170.2, 92.8, 180, "F"),
    # bottom side: SWD pogo pads in a 2.54 mm row under the MCU, spare I/O pads near the LDO
    "TP1": ("TestPoint", "TestPoint_Pad_D1.5mm", 159.5, 79.7, 0, "B"),
    "TP2": ("TestPoint", "TestPoint_Pad_D1.5mm", 162.04, 79.7, 0, "B"),
    "TP3": ("TestPoint", "TestPoint_Pad_D1.5mm", 164.58, 79.7, 0, "B"),
    "TP4": ("TestPoint", "TestPoint_Pad_D1.5mm", 167.12, 79.7, 0, "B"),
    "TP5": ("TestPoint", "TestPoint_Pad_D1.5mm", 169.66, 79.7, 0, "B"),
    "TP6": ("TestPoint", "TestPoint_Pad_D1.5mm", 172.2, 79.7, 0, "B"),
    "TP7": ("TestPoint", "TestPoint_Pad_D1.0mm", 166.0, 63.0, 0, "B"),
    "TP8": ("TestPoint", "TestPoint_Pad_D1.0mm", 168.0, 63.0, 0, "B"),
    "TP9": ("TestPoint", "TestPoint_Pad_D1.0mm", 170.0, 63.0, 0, "B"),
    "TP10": ("TestPoint", "TestPoint_Pad_D1.0mm", 172.0, 63.0, 0, "B"),
    "TP11": ("TestPoint", "TestPoint_Pad_D1.0mm", 174.0, 63.0, 0, "B"),
    "TP12": ("TestPoint", "TestPoint_Pad_D1.0mm", 166.0, 65.0, 0, "B"),
}


def parse_gerber(text):
    """Yield ('line', s, e) or ('arc', s, mid, e) in KiCad coordinates (Y flipped)."""
    mode, pos = "G01", None
    for tok in re.findall(r"[^*\s]+", text):
        if tok in ("G01", "G02", "G03"):
            mode = tok
            continue
        m = re.match(r"X(-?\d+)Y(-?\d+)(?:I(-?\d+)J(-?\d+))?D0([12])", tok)
        if not m:
            continue
        x, y = int(m.group(1)) / 1e6, int(m.group(2)) / 1e6
        if m.group(5) == "2":
            pos = (x, y)
            continue
        if mode == "G01":
            yield "line", (pos[0], -pos[1]), (x, -y)
        else:
            cx, cy = pos[0] + int(m.group(3)) / 1e6, pos[1] + int(m.group(4)) / 1e6
            a0 = math.atan2(pos[1] - cy, pos[0] - cx)
            a1 = math.atan2(y - cy, x - cx)
            d = a1 - a0
            if mode == "G02":  # clockwise
                while d >= 0:
                    d -= 2 * math.pi
            else:
                while d <= 0:
                    d += 2 * math.pi
            r = math.hypot(pos[0] - cx, pos[1] - cy)
            am = a0 + d / 2
            mid = (cx + r * math.cos(am), cy + r * math.sin(am))
            yield "arc", (pos[0], -pos[1]), (mid[0], -mid[1]), (x, -y)
        pos = (x, y)


def vec(p):
    return pcbnew.VECTOR2I(MM(p[0]), MM(p[1]))


def main():
    netlist = HERE / "openflaps-char.xml"
    if not netlist.exists():
        sys.exit("export the netlist first (see the docstring)")
    root = ET.parse(netlist).getroot()
    comps = {c.get("ref"): c for c in root.iter("comp")}
    pad_net = {}
    for n in root.iter("net"):
        name = n.get("name").lstrip("/")
        for node in n.iter("node"):
            pad_net[(node.get("ref"), node.get("pin"))] = name

    board = pcbnew.BOARD()
    nets = {}
    for name in sorted(set(pad_net.values())):
        if name.startswith("unconnected"):
            continue
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    for kind, *pts in parse_gerber(EDGE_GERBER):
        sh = pcbnew.PCB_SHAPE(board)
        sh.SetLayer(pcbnew.Edge_Cuts)
        sh.SetWidth(MM(0.05))
        if kind == "line":
            sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
            sh.SetStart(vec(pts[0]))
            sh.SetEnd(vec(pts[1]))
        else:
            sh.SetShape(pcbnew.SHAPE_T_ARC)
            sh.SetArcGeometry(vec(pts[0]), vec(pts[1]), vec(pts[2]))
        board.Add(sh)

    missing = set(comps) - set(PLACE)
    if missing:
        sys.exit(f"no placement for {sorted(missing)}")
    for ref, (lib, name, x, y, rot, side) in PLACE.items():
        fp = pcbnew.FootprintLoad(str(FPLIB / f"{lib}.pretty"), name)
        fp.SetReference(ref)
        fp.SetValue(comps[ref].findtext("value"))
        lcsc = next((f.text for f in comps[ref].iter("field") if f.get("name") == "LCSC"), None)
        if lcsc:
            (fp.SetField if hasattr(fp, "SetField") else fp.SetProperty)("LCSC", lcsc)
        board.Add(fp)
        fp.SetPosition(vec((x, y)))
        fp.SetOrientationDegrees(rot)
        if side == "B":
            fp.Flip(fp.GetPosition(), False)
        for pad in fp.Pads():
            net = pad_net.get((ref, pad.GetNumber()))
            if net in nets:
                pad.SetNet(nets[net])

    out = HERE / "openflaps-char.kicad_pcb"
    board.Save(str(out))
    print(f"wrote {out.name} with {len(PLACE)} footprints")


if __name__ == "__main__":
    main()
