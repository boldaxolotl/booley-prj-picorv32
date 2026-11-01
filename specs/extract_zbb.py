"""Extract the RV32 Zbb chapter (section 29.4.2 + the 18 RV32 instruction pages)
from the RISC-V unprivileged ISA manual HTML into compact Markdown.

Usage: python3 -I specs/extract_zbb.py <isa.html> <out.md> <manual-release>
"""

import base64
import hashlib
import html
import itertools
import re
import sys
from html.parser import HTMLParser

# The 18 RV32 Zbb instructions, as their manual anchor ids.
ZBB_RV32 = [
    "andn",
    "orn",
    "xnor",
    "clz",
    "ctz",
    "cpop",
    "max",
    "maxu",
    "min",
    "minu",
    "sext_b",
    "sext_h",
    "zext_h",
    "rol",
    "ror",
    "rori",
    "orc_b",
    "rev8",
]


def svg_encoding(svg: str) -> str:
    """Turn one WaveDrom register diagram into a Markdown field table."""
    rows = {}  # row y offset -> list of (x, text)
    for row in re.finditer(
        r"<g transform='translate\(12,(-?\d+)\)'>(.*?)(?=<g transform='translate\(12,|$)", svg, re.DOTALL
    ):
        y = int(row.group(1))
        items = []
        for m in re.finditer(r"translate\((\d+(?:\.\d+)?)\)'><text y='6'>(?:<tspan>)?([^<]*)", row.group(2)):
            items.append((float(m.group(1)), html.unescape(m.group(2))))
        rows[y] = items
    ys = sorted(rows)
    if len(ys) < 2:
        return "(encoding diagram not decodable)"
    # WaveDrom layout of this manual's 32-bit diagrams: bit 31 at x = 0, bit 0 at x = 766.
    width = 766.0

    def bit(x: float) -> int:
        return round(31 - x * 31 / width)

    labels = sorted({int(t) for _, t in rows[ys[0]] if t.isdigit()})
    # Field boundaries come in (lsb, msb) pairs from the index row. A one-bit
    # field carries a single label and would shift the later pairs; the pairs
    # must at least tile bits 0..31. (Two adjacent one-bit fields could still
    # pair up unnoticed; no RV32 Zbb diagram has a one-bit field.)
    fields = [(labels[i], labels[i + 1]) for i in range(0, len(labels) - 1, 2)]
    tiles = bool(fields) and fields[0][0] == 0 and fields[-1][1] == 31
    tiles = tiles and all(nxt[0] == cur[1] + 1 for cur, nxt in itertools.pairwise(fields))
    if not tiles:
        raise ValueError(f"encoding diagram fields are not (lsb, msb) pairs over bits 0..31: labels {labels}")
    cells = []
    for lo, hi in sorted(fields, reverse=True):
        content = [(x, t) for x, t in rows[ys[1]] if lo <= bit(x) <= hi]
        if content and all(t in "01" for _, t in content) and len(content) == hi - lo + 1:
            value = "".join(t for _, t in sorted(content))
        else:
            value = " ".join(t for _, t in sorted(content)) or "?"
        name = ""
        if len(ys) > 2:
            name = " ".join(t for x, t in rows[ys[2]] if lo <= bit(x) <= hi)
        span = f"[{hi}:{lo}]" if hi != lo else f"[{hi}]"
        cells.append((span, value + (f" ({name})" if name else "")))
    head = "| " + " | ".join(s for s, _ in cells) + " |"
    sep = "|" + "---|" * len(cells)
    body = "| " + " | ".join(v for _, v in cells) + " |"
    return f"{head}\n{sep}\n{body}"


class ToMarkdown(HTMLParser):
    """Very small HTML -> Markdown converter for asciidoctor output."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out, self.pre, self.cell, self.row = [], False, None, None
        self.first_row = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag in ("h3", "h4", "h5"):
            self.out.append("\n\n" + "#" * (int(tag[1]) - 1) + " ")
        elif tag == "p" and self.cell is None:
            self.out.append("\n\n")
        elif tag == "pre":
            self.pre = True
            self.out.append("\n\n```\n")
        elif tag == "dt":
            self.out.append("\n\n**")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag == "table":
            self.first_row = True
            self.out.append("\n")
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []
        elif tag == "img" and a.get("src", "").startswith("data:image/svg+xml;base64,"):
            svg = base64.b64decode(a["src"].split(",", 1)[1]).decode("utf-8", "replace")
            self.out.append("\n\n" + svg_encoding(svg) + "\n")
        elif tag == "em" and not self.pre:
            self._emit("_")
        elif tag == "code" and not self.pre:
            self._emit("`")

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre":
            self.pre = False
            self.out.append("\n```\n")
        elif tag == "dt":
            self.out.append("**")
        elif tag in ("td", "th") and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.out.append("\n| " + " | ".join(self.row) + " |")
            if self.first_row:  # Markdown tables need a separator under the header row
                self.out.append("\n|" + "---|" * len(self.row))
                self.first_row = False
            self.row = None
        elif tag == "em" and not self.pre:
            self._emit("_")
        elif tag == "code" and not self.pre:
            self._emit("`")

    def _emit(self, text: str) -> None:
        (self.cell if self.cell is not None else self.out).append(text)

    def handle_data(self, data: str) -> None:
        if self.pre:
            self.out.append(data)
        else:
            self._emit(re.sub(r"\s+", " ", data))

    def text(self) -> str:
        md = "".join(self.out)
        md = re.sub(r"[ \t]+\n", "\n", md)
        # Asciidoctor admonitions are one-row tables with an empty icon cell.
        md = re.sub(r"^\|  \| (.*) \|\n\|---\|---\|$", r"> \1", md, flags=re.MULTILINE)
        return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


def section(doc: str, anchor: str) -> str:
    """HTML from heading `anchor` up to the next heading of the same or higher level."""
    m = re.search(rf'<h([34]) id="{re.escape(anchor)}">', doc)
    if m is None:
        raise SystemExit(f"section anchor {anchor!r} not found; is this the RISC-V unprivileged ISA manual HTML?")
    level = int(m.group(1))
    end = re.compile(rf"<h[2-{level}] id=")
    nxt = end.search(doc, m.end())
    return doc[m.start() : nxt.start() if nxt else len(doc)]


def convert(fragment: str) -> str:
    parser = ToMarkdown()
    parser.feed(fragment)
    return parser.text()


HEADER = """# RV32 Zbb 1.0 specification excerpt

Source: _The RISC-V Instruction Set Manual, Volume I: Unprivileged ISA_,
release {release}, section 29.4.2 (Zbb: Basic bit-manipulation) and the
section 29.5 pages of the 18 RV32 Zbb instructions. Copied from
`/opt/riscv-docs/riscv-isa-unprivileged.html` in the demo's pinned Sandbox
image, SHA-256
`{digest}`.
The manual is licensed CC-BY-4.0 by RISC-V International. The text is
unchanged; the encoding diagrams are transcribed into tables. Regenerate with
`python3 -I specs/extract_zbb.py <html> specs/zbb.md <release>`.

Scope for this Project: RV32 only. Rows and encodings marked RV64 (`clzw`,
`ctzw`, `cpopw`, `rolw`, `roriw`, `rorw`, and the RV64 forms of `zext.h`,
`rori` and `rev8`) are out of scope. On RV32, `rori` encodings with
`shamt[5]=1` are reserved.

"""


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    src, dst, release = sys.argv[1:]
    with open(src, "rb") as handle:
        raw = handle.read()
    doc = raw.decode("utf-8")
    parts = [HEADER.format(release=release, digest=hashlib.sha256(raw).hexdigest()), convert(section(doc, "zbb"))]
    for name in ZBB_RV32:
        parts.append(convert(section(doc, f"insns-{name}")))
    with open(dst, "w", encoding="utf-8") as handle:
        handle.write("\n".join(parts))


if __name__ == "__main__":
    main()
