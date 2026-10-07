"""Generate static/img/tract-grid.svg, the landing page's census-tract motif.

A field of small squares at varying opacity: the NCRC mark multiplied, read as
a choropleth with the geography removed. One hue (cyan) on deep blue, plus a
single gold tract. Fixed seed, so the output never changes between runs.

    python scripts/gen_tract_grid.py > justdata/shared/web/static/img/tract-grid.svg
"""

import random

COLS, ROWS, CELL, GAP = 28, 18, 14, 3
W = COLS * (CELL + GAP)
H = ROWS * (CELL + GAP)
CYAN, GOLD = "#2FADE3", "#FFC23A"  # --ncrc-cyan-500, --ncrc-gold (SVG cannot read CSS tokens)
random.seed(20260101)


def alpha(c):
    """Denser toward the right, fading toward the left where the copy sits."""
    base = max(0.0, (c / COLS - 0.15) / 0.85)
    a = (base * 0.7 + random.random() * 0.3) ** 1.4
    return 0.0 if a < 0.08 else round(min(a, 0.95), 2)


def main():
    cells = [(r, c, alpha(c)) for r in range(ROWS) for c in range(COLS)]
    cells = [cell for cell in cells if cell[2] > 0.0]
    # Exactly one highlighted tract: the strongest cell in the middle row's right side.
    gold = max((cell for cell in cells if cell[0] == ROWS // 2 and cell[1] > COLS * 0.6),
               key=lambda cell: cell[2])
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" aria-hidden="true">']
    for r, c, a in cells:
        fill = GOLD if (r, c, a) == gold else CYAN
        out.append(f'<rect x="{c * (CELL + GAP)}" y="{r * (CELL + GAP)}" width="{CELL}" height="{CELL}" '
                   f'fill="{fill}" fill-opacity="{a}"/>')
    out.append("</svg>")
    print("\n".join(out))


if __name__ == "__main__":
    main()
