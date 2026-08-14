"""Render PrimeTimePix brand assets as crisp PNGs (NOT AI-generated).

Style: vintage collegiate athletic badge/crest (double ring + arc text, star,
lightning bolts, banner ribbon) with broadcast-condensed type. Neon-green/black
brand scheme. The emblem is a BADGE (not an X). Hand-authored HTML/CSS + inline
SVG, rendered with headless Chromium, so it's fully editable/reproducible.

Outputs (into primetimepix/static/images/):
  - invite-og.png   1200x630  social / invite share card
  - logo.png         920x240  horizontal wordmark lockup (transparent)
  - logo-mark.png    512x512  badge crest icon (favicon / app icon, transparent)

Run:
    venv/bin/python scripts/generate_brand.py
(First time only: venv/bin/playwright install chromium)
"""
import math
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

IMG_DIR = (
    Path(__file__).resolve().parent.parent / "primetimepix" / "static" / "images"
)

EYEBROW = "PRIMETIME PICK'EM"
HEADLINE_TOP = "YOU'RE"
HEADLINE_BOTTOM = "INVITED"
SUBTITLE = "Make your picks. Talk your trash. Run the league."

# Emblem copy (sport-agnostic: no "NFL")
TOP_LABEL = "PRIMETIME PICK'EM"
BANNER = "PRIMETIMEPIX"
SPORTS = "SPORTS"
EST = "EST. 2026"

NEON = "#39ff14"
NEON_DK = "#1fbf07"
INK = "#0b0c10"
BONE = "#eef1ea"  # off-white for secondary text (two-tone hierarchy)


def _star(cx: float, cy: float, ro: float, ri: float, n: int = 5, rot: float = -90) -> str:
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = math.radians(rot + i * 180.0 / n)
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return "M" + "L".join(pts) + "Z"


# A single lightning bolt, drawn in a ~48x86 box starting at origin.
_BOLT = "M30 0 L6 46 L22 46 L14 86 L44 34 L28 34 Z"


def _bolt(cx: float, cy: float, scale: float, flip: bool = False) -> str:
    sx = -scale if flip else scale
    # center the ~48x86 art around (cx, cy)
    tx = cx - (sx * 24)
    ty = cy - (scale * 43)
    return (
        f'<path d="{_BOLT}" transform="translate({tx:.1f} {ty:.1f}) '
        f'scale({sx:.3f} {scale:.3f})" fill="{NEON}" '
        f'stroke="{INK}" stroke-width="3"/>'
    )


def build_shield() -> str:
    cx = 240
    # Heraldic shield: flat top with rounded corners, curving to a bottom point.
    outer = ("M 66 54 L 414 54 Q 434 54 434 74 L 434 300 "
             "C 434 410 360 470 240 516 C 120 470 46 410 46 300 "
             "L 46 74 Q 46 54 66 54 Z")
    inner = ("M 66 72 L 414 72 L 414 298 "
             "C 414 396 352 448 240 488 C 128 448 66 396 66 298 Z")
    # Flat design (no neon glow) for a cleaner, more professional mark.
    return f"""
<svg viewBox="0 0 480 560" fill="none" xmlns="http://www.w3.org/2000/svg">
  <g>
    <!-- shield body + double outline -->
    <path d="{outer}" fill="{INK}" stroke="{NEON}" stroke-width="8" stroke-linejoin="round"/>
    <path d="{inner}" fill="none" stroke="{NEON}" stroke-width="2.5" stroke-linejoin="round"/>

    <!-- top label (off-white for hierarchy) -->
    <text x="{cx}" y="104" font-family="Oswald, sans-serif" font-weight="600" font-size="20"
          letter-spacing="4" fill="{BONE}" text-anchor="middle">{TOP_LABEL}</text>
    <line x1="132" y1="120" x2="348" y2="120" stroke="{NEON}" stroke-width="2.5"/>
    <rect x="123" y="112" width="16" height="16" transform="rotate(45 131 120)" fill="{NEON}"/>
    <rect x="341" y="112" width="16" height="16" transform="rotate(45 349 120)" fill="{NEON}"/>

    <!-- single clean star -->
    <path d="{_star(240, 172, 38, 16)}" fill="{NEON}" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>

    <!-- banner ribbon (two lines: brand + SPORTS, both inside the ribbon) -->
    <path d="M52 202 L88 222 L88 302 L52 322 L70 262 Z" fill="{NEON_DK}"/>
    <path d="M428 202 L392 222 L392 302 L428 322 L410 262 Z" fill="{NEON_DK}"/>
    <rect x="86" y="212" width="308" height="100" rx="4" fill="{NEON}"/>
    <rect x="86" y="212" width="308" height="100" rx="4" fill="none" stroke="{INK}" stroke-width="2.5"/>
    <text x="{cx}" y="262" font-family="Anton, sans-serif" font-size="42"
          letter-spacing="1" fill="{INK}" text-anchor="middle">{BANNER}</text>
    <text x="{cx}" y="296" font-family="Oswald, sans-serif" font-weight="700" font-size="21"
          letter-spacing="11" fill="{INK}" text-anchor="middle">&#160;{SPORTS}</text>

    <!-- established line -->
    <text x="{cx}" y="356" font-family="Oswald, sans-serif" font-weight="600" font-size="18"
          letter-spacing="5" fill="{BONE}" text-anchor="middle">{EST}</text>

    <!-- bottom point star -->
    <path d="{_star(240, 452, 15, 6)}" fill="{NEON}" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>
  </g>
</svg>
"""


EMBLEM_SVG = build_shield()


def ico(size: int) -> str:
    return f'<span class="ico" style="width:{size}px;height:{size}px">{EMBLEM_SVG}</span>'


HEAD = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Oswald:wght@500;600;700&family=Saira+Condensed:wght@700;800;900&family=Inter:wght@500;600;700;800&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Inter',system-ui,sans-serif; -webkit-font-smoothing:antialiased; color:#fff; }
  .ico svg { width:100%; height:100%; display:block; }
  .anton { font-family:'Anton',sans-serif; font-weight:400; text-transform:uppercase; }
  .skew  { display:inline-block; transform:skewX(-8deg); }
  .neon  { color:#39ff14; }

  /* ================= INVITE CARD ================= */
  #card {
    position:relative; width:1200px; height:630px; overflow:hidden;
    background:
      radial-gradient(720px 620px at 76% 40%, rgba(57,255,20,0.09), transparent 62%),
      linear-gradient(150deg, #0a0b10 0%, #0d0e15 54%, #070709 100%);
  }
  /* Angled broadcast panel that gives the logo an intentional "scoreboard" home
     (with a crisp neon divider) instead of floating in a soft AI-style glow. */
  #card .panel { position:absolute; top:-70px; bottom:-70px; right:-72px; width:640px;
    transform:skewX(-9deg); transform-origin:top right; pointer-events:none;
    background:linear-gradient(155deg, rgba(28,31,42,0.92) 0%, rgba(11,12,18,0.94) 100%);
    border-left:3px solid rgba(57,255,20,0.6);
    box-shadow:-26px 0 60px rgba(0,0,0,0.35); }
  #card .panel::after { content:""; position:absolute; inset:0;
    background:repeating-linear-gradient(90deg, transparent 0 26px,
      rgba(255,255,255,0.028) 26px 28px); }
  /* Soft vignette to ground the composition (replaces the generic hairline field). */
  #card .field { position:absolute; inset:0; pointer-events:none;
    background:radial-gradient(130% 95% at 46% 122%, rgba(0,0,0,0.5), transparent 58%); }
  #card .corner { position:absolute; width:44px; height:44px; border-color:#39ff14; opacity:0.85; }
  #card .tl { top:36px; left:36px; border-top:4px solid; border-left:4px solid; border-top-left-radius:6px; }
  #card .br { bottom:36px; right:36px; border-bottom:4px solid; border-right:4px solid; border-bottom-right-radius:6px; }
  #card .wrap { position:relative; height:100%; display:flex; align-items:center; padding:0 70px; }
  #card .left { flex:1; }
  #card .eyebrow { display:inline-block; font-weight:800; font-size:19px; letter-spacing:4px; color:#39ff14;
    text-transform:uppercase; padding:8px 15px; border:1.5px solid rgba(57,255,20,0.45);
    border-radius:999px; background:rgba(57,255,20,0.06); }
  #card .headline { font-size:120px; line-height:0.86; letter-spacing:1px; margin-top:22px; }
  #card .headline .row { display:block; }
  #card .headline .b { }
  #card .rule { width:150px; height:9px; border-radius:4px; margin-top:24px;
    background:#39ff14; box-shadow:0 0 22px rgba(57,255,20,0.6); transform:skewX(-8deg); }
  #card .subtitle { margin-top:24px; font-size:26px; font-weight:600; color:#cbced8; max-width:560px; }
  #card .lockup { position:absolute; left:70px; bottom:48px; display:flex; align-items:center; gap:13px; }
  #card .lockup .wm { font-size:32px; letter-spacing:1px;
    -webkit-text-stroke:1px rgba(0,0,0,0.35); paint-order:stroke; }
  #card .art { width:440px; display:flex; align-items:center; justify-content:center; }
  #card .art .ico { filter: drop-shadow(0 8px 30px rgba(0,0,0,0.45)); }

  /* ================= LOGO LOCKUP (transparent) ================= */
  #logo { width:920px; height:240px; display:flex; align-items:center; gap:24px; padding:0 24px; background:transparent; }
  #logo .txt { display:flex; flex-direction:column; }
  #logo .wm { font-size:92px; line-height:0.9; letter-spacing:1px; white-space:nowrap;
    -webkit-text-stroke:1.2px rgba(0,0,0,0.4); paint-order:stroke; }
  #logo .tag { margin-top:8px; margin-left:4px; font-weight:700; font-size:21px; letter-spacing:7px;
    color:#39ff14; text-transform:uppercase; }

  /* ================= MARK BADGE (transparent) ================= */
  #mark { width:512px; height:512px; display:flex; align-items:center; justify-content:center; background:transparent; }

  /* ================= BROADCAST LOCKUP (ESPN-style) ================= */
  #lockwrap { display:inline-block; background:transparent; }
  #tilewrap { width:512px; height:512px; display:flex; align-items:center; justify-content:center;
    background: radial-gradient(120% 120% at 50% 30%, #17171f 0%, #0a0a0f 72%);
    border-radius:112px; border:2px solid rgba(57,255,20,0.18); }
  .lock { position:relative; display:inline-flex; flex-direction:column; align-items:center;
    padding:24px 40px 34px 104px; }
  /* Aggressive forward lean (SPORTS+MATCH slanting lettering) */
  .lock .cap { transform:skewX(-12deg); border-radius:999px; border:7px solid #0b0c10; }
  /* Top wordmark = PRIMETIME (white) + PIX (neon): freestanding outlined letters,
     hard 3D extrude + black keyline so it reads on light + dark. NO bubble. */
  .lock .cap.top { background:transparent; border:none; padding:0; box-shadow:none;
    display:inline-flex; align-items:baseline; position:relative; z-index:10; }
  .lock .cap.top .pt, .lock .cap.top .px { font-family:'Anton',sans-serif; font-size:90px;
    line-height:1.02; letter-spacing:1px; -webkit-text-stroke:2.5px #0b0c10; paint-order:stroke;
    text-shadow:2px 2px 0 #0b0c10, 4px 4px 0 #0b0c10, 6px 6px 0 #0b0c10, 9px 9px 0 #128a0a; }
  .lock .cap.top .pt { color:#ffffff; }
  .lock .cap.top .px { color:#39ff14; }
  /* Bottom = neon SPORTS pill tucked under the wordmark (connected, NOT covering
     it). The first/last S break past the pill's rounded caps and blend in neon,
     echoing how the S and ")" break the circle in SHOWCASE.
     Layers: back neon letters -> neon pill -> front black letters clipped to pill. */
  /* Bottom = SPORTS styled after ref #2: oversized lead S + PORTS, a ball/orbit
     swoosh behind the trailing end, and a speed-line underline sweeping up to it. */
  /* Bottom = SPORTS wordmark traced directly from the reference logo (exact
     letterforms), recoloured neon with a black keyline + 3D extrude so it reads on
     light + dark and matches the PRIMETIMEPIX wordmark above. No ball/underline. */
  .lock .cap.bot { margin-top:-14px; align-self:stretch; transform:none; display:flex;
    justify-content:center; background:transparent; border:none; box-shadow:none;
    padding:0; position:relative; z-index:3; }
  /* Full-width sub-wordmark: SPORTS spans the PRIMETIMEPIX width (SEGA SPORTS
     alignment), uniformly scaled so the letterforms stay undistorted. */
  .lock .cap.bot .swm { display:block; width:100%; height:auto; overflow:visible; }
  /* Crisper, thinner 3D extrude on the whole mark. */
  .lock .cap.bot .swm .art { filter:drop-shadow(1px 1px 0 #0b0c10)
    drop-shadow(2px 2px 0 #0b0c10) drop-shadow(4px 4px 0 #128a0a); }
  .lock .cap.bot .swm .neon path { fill:#39ff14; stroke:#0b0c10; stroke-width:5;
    stroke-linejoin:round; paint-order:stroke; }
  .lock .speed { position:absolute; left:24px; top:50%; transform:translateY(-54%) skewX(-9deg);
    display:flex; flex-direction:column; gap:11px; align-items:flex-end; }
  .lock .speed i { height:8px; border-radius:4px; background:#39ff14; }
  .lock .speed i:nth-child(1){ width:34px; opacity:.5; }
  .lock .speed i:nth-child(2){ width:62px; opacity:.85; }
  .lock .speed i:nth-child(3){ width:46px; opacity:.65; }
  .lock.nospeed { padding-left:34px; }
  #card .cardlock { transform:scale(0.58); transform-origin:center; }
  /* App-icon monogram — SHOWCASE treatment: letters break OUT of the disc and
     go two-tone (neon on the black tile, knocked-out black inside the neon disc).
     Layered: back neon letters -> neon disc -> front black letters clipped to disc. */
  #tilewrap .badgeicon { display:flex; align-items:center; justify-content:center; }
  /* Clean neon PIX roundel (no break-out): neon disc + centred black knockout. */
  .roundel { width:336px; height:336px; border-radius:50%; background:#39ff14;
    display:flex; align-items:center; justify-content:center;
    box-shadow:0 0 0 12px #0b0c10, 0 0 0 21px #39ff14, 9px 13px 0 21px rgba(11,12,16,0.45); }
  .roundel .mono { font-family:'Anton',sans-serif; font-size:152px; letter-spacing:2px;
    color:#0b0c10; transform:skewX(-10deg); padding-right:8px; }

  /* ========= VINTAGE BROADCAST LOCKUP (ref: PRIMETIMEPIX SPORTS) =========
     Tri-tone italic PRIMETIMEPIX wordmark, speedometer + speed-lines + checkmark
     emblem breaking out top-right, and a SPORTS sub-bar in the SAME Anton
     lettering framed by neon underline flanks. No pill / no capsule. */
  /* extra top/right padding so the emblem breaking out above the wordmark isn't
     clipped when #lockwrap is screenshotted (trim_transparent recrops after). */
  #lockwrap { padding:210px 104px 44px 64px; }
  .lockv { position:relative; display:inline-flex; flex-direction:column;
    align-items:center;
    /* shared inline "speed cut": a thin transparent notch slicing the letters,
       applied to BOTH the wordmark and SPORTS so the dash detail matches. */
    --cut:linear-gradient(to bottom, #000 0 49%, transparent 49% 55.5%, #000 55.5% 100%); }
  /* clean thin keyline + subtle single drop (not chunky stacked extrude) */
  .lockv .wm2 { display:flex; font-family:'Anton',sans-serif; font-size:104px;
    line-height:.9; letter-spacing:2px; transform:skewX(-10deg);
    -webkit-text-stroke:2.5px #0b0c10; paint-order:stroke;
    text-shadow:2px 3px 0 rgba(11,12,16,0.9);
    -webkit-mask-image:var(--cut); mask-image:var(--cut); }
  .lockv .wm2 .a { color:#39ff14; }
  .lockv .wm2 .b { color:#f4f6f5; }
  .lockv .emblem2 { position:absolute; top:-128px; right:-70px; width:372px; z-index:5;
    filter:drop-shadow(0 6px 14px rgba(0,0,0,0.32)); }
  /* thin full-width rule under the wordmark (separates it from the SPORTS row) */
  .lockv .uline { width:97%; height:7px; margin-top:14px; border-radius:4px;
    background:#f4f6f5; transform:skewX(-10deg); box-shadow:0 0 0 2.5px #0b0c10; }
  /* SPORTS row: ESPN-style condensed italic (Saira Condensed), white, pushed to
     centre with short neon dash accents at the far edges. */
  .lockv .tagbar { display:flex; align-items:center; justify-content:space-between;
    width:100%; margin-top:14px; }
  .lockv .tagbar .sports { font-family:'Saira Condensed',sans-serif; font-weight:900;
    font-size:56px; letter-spacing:2px; color:#f4f6f5; transform:skewX(-12deg);
    -webkit-text-stroke:2px #0b0c10; paint-order:stroke;
    text-shadow:2px 2px 0 rgba(11,12,16,0.9);
    -webkit-mask-image:var(--cut); mask-image:var(--cut); }
  .lockv .flank { display:flex; align-items:center; gap:9px; }
  .lockv .flank i { display:block; height:10px; border-radius:5px; background:#39ff14;
    transform:skewX(-10deg); box-shadow:0 0 0 2.5px #0b0c10; }
  .lockv .flank.l i:nth-child(1){ width:40px; }
  .lockv .flank.l i:nth-child(2){ width:16px; }
  .lockv .flank.r i:nth-child(1){ width:16px; }
  .lockv .flank.r i:nth-child(2){ width:40px; }
  /* speedometer/checkmark emblem (shared by lockup + app icon) */
  .emb { display:block; width:100%; height:auto; overflow:visible; }
  .emb path, .emb line { fill:none; stroke-linecap:round; stroke-linejoin:round; }
  .emb .rim.k, .emb .ndl.k, .emb .spd.k { stroke:#0b0c10; }
  .emb .rim.white { stroke:#f4f6f5; }
  .emb .rim.neon { stroke:#39ff14; }
  .emb .rim { stroke-width:13; }
  .emb .rim.k { stroke-width:20; }
  .emb .tick line { stroke:#f4f6f5; stroke-width:7; }
  .emb .ndl { stroke-width:15; }
  .emb .ndl.neon { stroke:#39ff14; }
  .emb .spd { stroke-width:9; }
  .emb .spd.k { stroke-width:16; }
  .emb .spd.neon { stroke:#39ff14; }
  .emb .spd.white { stroke:#f4f6f5; }
  .emb .swoosh { stroke:none; }
  .emb .swoosh.k { fill:#0b0c10; }
  .emb .swoosh.neon { fill:#39ff14; }
  .emb .swoosh.white { fill:#f4f6f5; }
  #tilewrap .embicon { width:412px; display:flex; align-items:center; justify-content:center; }
</style>
</head>
<body>
"""


BRAND_REFS = Path(__file__).resolve().parent.parent / "docs" / "brand_refs"


def _svg_paths(name: str) -> str:
    import re

    return "".join(re.findall(r"<path\b[^>]*/>", (BRAND_REFS / name).read_text()))


def sports_word_svg() -> str:
    """SPORTS lockup: the classic 'Sports' logo (italic S + PORTS + underline
    sweep) traced directly from the reference, recoloured to the neon/black
    brand (ball + red stripe removed). The leading S is stored separately so it
    can be scaled down and tucked against PORTS, and the underline's lower-left
    tail was trimmed for balance. Cropped tight so it stretches edge-to-edge
    under PRIMETIMEPIX like SEGA SPORTS.
    """
    rest = _svg_paths("sports_rest.svg")          # PORTS + trimmed underline
    first_s = _svg_paths("sports_first_s.svg")     # leading S (native x14-176 y88-269)
    s_tf = "translate(40,44) scale(0.75)"          # shrink + tuck against PORTS
    return (
        '<svg class="swm" viewBox="46 104 528 262" '
        'preserveAspectRatio="xMidYMid meet">'
        '<g class="art"><g class="neon">'
        f"{rest}"
        f'<g transform="{s_tf}">{first_s}</g>'
        "</g></g></svg>"
    )


EMB_CX, EMB_CY = 150, 132
EMB_R_OUT, EMB_R_IN = 104, 88


def _pt(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _arc(cx, cy, r, a0, a1):
    x0, y0 = _pt(cx, cy, r, a0)
    x1, y1 = _pt(cx, cy, r, a1)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M {x0:.1f} {y0:.1f} A {r} {r} 0 {large} 1 {x1:.1f} {y1:.1f}"


def _taper(x0, y0, x1, y1, w, sag=0.0):
    """Sleek filled swoosh: a sharp point at (x0,y0) sweeping to a rounded thick
    end (width w) at (x1,y1). `sag` bows the centreline (positive dips down),
    giving the dynamic speed-streak look from the reference logo."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + sag
    dx, dy = x1 - mx, y1 - my
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    ax, ay = x1 + nx * w / 2, y1 + ny * w / 2
    bx, by = x1 - nx * w / 2, y1 - ny * w / 2
    return (
        f"M {x0:.1f} {y0:.1f} Q {mx:.1f} {my - w / 2:.1f} {ax:.1f} {ay:.1f} "
        f"L {bx:.1f} {by:.1f} Q {mx:.1f} {my + w / 2:.1f} {x0:.1f} {y0:.1f} Z"
    )


def emblem_svg(speed: bool = True) -> str:
    """Hand-authored neon speedometer gauge with a checkmark-needle (doubles as
    a 'pick') and speed lines — the signature motif from the polished reference,
    rebuilt clean in neon/white/black. `speed=False` drops the speed lines and
    tightens the viewBox for use as the square app icon."""
    cx, cy, ro, ri = EMB_CX, EMB_CY, EMB_R_OUT, EMB_R_IN
    a0, a1 = 158, 382
    outer = _arc(cx, cy, ro, a0, a1)
    inner = _arc(cx, cy, ri, a0 + 6, a1 - 6)
    ticks = []
    for deg in range(198, 344, 24):
        xo, yo = _pt(cx, cy, ri - 6, deg)
        xi, yi = _pt(cx, cy, ri - 22, deg)
        ticks.append(f'<line x1="{xo:.1f}" y1="{yo:.1f}" x2="{xi:.1f}" y2="{yi:.1f}"/>')
    check = f"M {cx-52} {cy+2} L {cx-16} {cy+40} L {cx+60} {cy-46}"
    spd_k = spd = ""
    if speed:
        # two tapered streaks sweeping up-right into the gauge (neon lower,
        # white upper) — sleek pointed swooshes like the reference logo.
        sw = [
            ("neon", cx - 268, cy + 32, cx - 28, cy + 12, 31, 16),
            ("white", cx - 252, cy + 8, cx - 24, cy - 10, 20, 11),
        ]
        spd_k = "".join(
            f'<path class="swoosh k" d="{_taper(x0, y0, x1, y1, w + 8, sag)}"/>'
            for _c, x0, y0, x1, y1, w, sag in sw
        )
        spd = "".join(
            f'<path class="swoosh {c}" d="{_taper(x0, y0, x1, y1, w, sag)}"/>'
            for c, x0, y0, x1, y1, w, sag in sw
        )
    vb = "-132 8 420 200" if speed else "24 10 252 190"
    return (
        f'<svg class="emb" viewBox="{vb}" preserveAspectRatio="xMidYMid meet">'
        f'{spd_k}<path class="rim k" d="{outer}"/><path class="rim k" d="{inner}"/>'
        f'<path class="ndl k" d="{check}"/>'
        f'{spd}<path class="rim white" d="{outer}"/><path class="rim neon" d="{inner}"/>'
        f'<g class="tick">{"".join(ticks)}</g><path class="ndl neon" d="{check}"/>'
        "</svg>"
    )


def build_lockup(speed: bool = True) -> str:
    """Vintage broadcast lockup (ref: the PRIMETIMEPIX SPORTS logo). Tri-tone
    italic wordmark (PRIME neon / TIME white / PIX neon) with the neon
    speedometer + speed-lines + checkmark emblem breaking out of the top-right,
    and a SPORTS sub-bar rendered in the SAME Anton lettering framed by neon
    underline flanks. No pill / no capsule — freestanding with a SEGA-style
    black keyline + 3D extrude for the vintage feel."""
    return (
        '<div class="lockv">'
        f'<div class="emblem2">{emblem_svg(speed)}</div>'
        '<div class="wm2">'
        '<span class="a">PRIME</span><span class="b">TIME</span>'
        '<span class="a">PIX</span>'
        "</div>"
        '<div class="uline"></div>'
        '<div class="tagbar">'
        '<span class="flank l"><i></i><i></i></span>'
        '<span class="sports">SPORTS</span>'
        '<span class="flank r"><i></i><i></i></span>'
        "</div>"
        "</div>"
    )


def _build_lockup_legacy(speed: bool = True) -> str:
    """SEGA-style stacked lockup: big outlined 'PRIMETIMEPIX' wordmark on top,
    with a solid neon 'SPORTS' pill centred beneath it. ESPN italic slant + speed
    lines and a stacked-offset sticker shadow, all in the neon/black theme."""
    cls = "lock" if speed else "lock nospeed"
    speed_bars = '<div class="speed"><i></i><i></i><i></i></div>' if speed else ""
    return (
        f'<div class="{cls}">'
        f'{speed_bars}'
        '<div class="cap top">'
        '<span class="pt">PRIMETIME</span><span class="px">PIX</span>'
        '</div>'
        '<div class="cap bot">'
        f'{sports_word_svg()}'
        '</div>'
        '</div>'
    )


def card_html() -> str:
    return HEAD + f"""
  <div id="card">
    <div class="panel"></div>
    <div class="field"></div>
    <div class="corner tl"></div>
    <div class="corner br"></div>
    <div class="wrap">
      <div class="left">
        <div class="eyebrow">{EYEBROW}</div>
        <div class="headline anton">
          <span class="row skew">{HEADLINE_TOP}</span>
          <span class="row skew neon b">{HEADLINE_BOTTOM}</span>
        </div>
        <div class="rule"></div>
        <div class="subtitle">{SUBTITLE}</div>
      </div>
      <div class="art"></div>
    </div>
  </div>
</body></html>"""


def logo_html() -> str:
    return HEAD + f"""
  <div id="lockwrap">{build_lockup(True)}</div>
</body></html>"""


def mark_html() -> str:
    """App icon (favicon / home-screen): industry-standard single-monogram on a
    saturated tile. A neon-green squircle with a bold, forward-slanted 'PIX'
    knockout + faint motion speedlines (ESPN-style). High-contrast and legible
    from 512px down to 29px, and its neon hero pops against the mostly-dark
    sports-app grid (ESPN/DraftKings/theScore)."""
    lines = '<div class="spdx"><i></i><i></i><i></i></div>'
    return HEAD + f"""
  <style>
    /* Flat, premium dark tile (matches the app's dark neon UI) with a crisp neon
       diagonal seam accent — a deliberate designed structure, not a glossy blob. */
    #tilewrap {{ position:relative; overflow:hidden; border:none; border-radius:112px;
      background:linear-gradient(122deg, #15171e 0 49.4%, rgba(57,255,20,0.5) 49.4% 50.1%,
        #0a0b0f 50.1% 100%); }}
    /* faint top-left light + a low neon bloom in the lower-right for subtle depth */
    #tilewrap::before {{ content:""; position:absolute; inset:0; z-index:1;
      background:
        radial-gradient(85% 80% at 16% 12%, rgba(255,255,255,0.05), transparent 46%),
        radial-gradient(80% 80% at 82% 92%, rgba(57,255,20,0.14), transparent 56%); }}
    /* neon hairline keyline — crafted edge that ties the icon to the brand accent */
    #tilewrap::after {{ content:""; position:absolute; inset:16px; z-index:3;
      border-radius:96px; border:2.5px solid rgba(57,255,20,0.4); pointer-events:none; }}
    #tilewrap .spdx {{ position:absolute; z-index:2; left:60px; top:50%;
      transform:translateY(-50%) skewX(-9deg); display:flex; flex-direction:column;
      gap:15px; align-items:flex-end; }}
    #tilewrap .spdx i {{ display:block; height:13px; border-radius:7px; background:#39ff14; }}
    #tilewrap .spdx i:nth-child(1) {{ width:42px; opacity:.5; }}
    #tilewrap .spdx i:nth-child(2) {{ width:78px; opacity:.8; }}
    #tilewrap .spdx i:nth-child(3) {{ width:56px; opacity:.62; }}
    #tilewrap .pixmk {{ position:relative; z-index:2; font-family:'Anton',sans-serif;
      font-size:176px; letter-spacing:1px; color:#39ff14; transform:skewX(-9deg);
      text-shadow:2px 3px 0 rgba(2,34,0,0.7); }}
  </style>
  <div id="tilewrap">{lines}<div class="pixmk">PIX</div></div>
</body></html>"""


def render(page_html: str, selector: str, out: Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=2)
        page.set_content(page_html, wait_until="networkidle")
        page.evaluate("() => document.fonts.ready")
        page.wait_for_timeout(250)
        transparent = selector in ("#logo", "#mark", "#lockwrap")
        page.locator(selector).screenshot(path=str(out), omit_background=transparent)
        browser.close()
    print(f"Wrote {out}")


def downscale(path: Path, max_dim: int) -> None:
    subprocess.run(["sips", "-Z", str(max_dim), str(path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def trim_transparent(path: Path, pad: int = 24) -> None:
    """Crop transparent margins (from emblem-overflow padding) to a tight bbox."""
    from PIL import Image

    im = Image.open(path).convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    if bbox:
        left, top, right, bottom = bbox
        left, top = max(left - pad, 0), max(top - pad, 0)
        right, bottom = min(right + pad, im.width), min(bottom + pad, im.height)
        im.crop((left, top, right, bottom)).save(path)


REFERENCE = BRAND_REFS / "primetimepix_ref.png"


def recolor_reference():
    """Recolour the approved PRIMETIMEPIX SPORTS reference from red -> the exact
    brand neon (#39ff14), keeping black + white intact. We treat 'redness' as a
    coverage mask and composite flat neon over it, so solid areas land on the
    precise app colour while antialiased edges stay smooth. Returns RGB."""
    import numpy as np
    from PIL import Image

    im = Image.open(REFERENCE).convert("RGB")
    arr = np.array(im).astype(np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    redness = r - np.maximum(g, b)
    alpha = np.clip((redness - 30) / 110.0, 0, 1)[..., None]
    neon = np.array([57, 255, 20], np.float32)   # #39ff14, the app's neon
    out = neon * alpha + arr * (1 - alpha)
    return Image.fromarray(out.astype(np.uint8), "RGB")


def _render_svg(svg: str, width: int, height: int):
    """Render a bare SVG string to a transparent RGBA PIL image (3x supersampled)."""
    from PIL import Image

    html = (
        "<html><head><style>body{margin:0;background:transparent}"
        "svg{overflow:visible}</style></head><body>"
        f"{svg}</body></html>"
    )
    tmp = BRAND_REFS / "_svg_tmp.png"
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(device_scale_factor=3)
        pg.set_content(html, wait_until="networkidle")
        pg.wait_for_timeout(120)
        pg.locator("svg").screenshot(path=str(tmp), omit_background=True)
        br.close()
    return Image.open(tmp).convert("RGBA")


def clock_emblem_svg(W: int, H: int) -> str:
    """Prime-time emblem (ref: the red/black speedometer logo, reimagined as a CLOCK):
    a half-clock dial on the right whose outer edge meets the M in TIME, with two sharp
    tapered hands splaying from the dot of the lowercase 'i' (10:10 hero pose). The dial's
    lower-left is trimmed open and three tapered speed streaks sweep in there, exactly
    like the reference. White/neon split ties it to the brand palette."""

    def pt(x, y, r, deg):
        t = math.radians(deg - 90)
        return x + r * math.cos(t), y + r * math.sin(t)

    hub = (567.0, 344.0)                 # hands vertex / i-dot, over the italic i's stem
    # Arc is centered a touch left of the hub and sized so its outer stroke edge lands
    # exactly on the M's right edge (x=677) — SW/2 accounts for the stroke half-width.
    SW = 15.0
    cx, cy = 560.5, 322.0
    R = 677.0 - cx - SW / 2

    def arc(r, b0, b1):
        x0, y0 = pt(cx, cy, r, b0)
        x1, y1 = pt(cx, cy, r, b1)
        lg = 1 if (b1 - b0) % 360 > 180 else 0
        return f"M {x0:.1f} {y0:.1f} A {r} {r} 0 {lg} 1 {x1:.1f} {y1:.1f}"

    def hand(deg, length, halfw):        # sharp tapered wedge, base at hub -> point
        tx, ty = pt(*hub, length, deg)
        b1 = pt(*hub, halfw, deg + 90)
        b2 = pt(*hub, halfw, deg - 90)
        return (f'<polygon points="{b1[0]:.1f},{b1[1]:.1f} {tx:.1f},{ty:.1f} '
                f'{b2[0]:.1f},{b2[1]:.1f}" class="hd"/>')

    def line(xr, yr, xl, yl, hw, cls):   # speed line: blunt right end -> sharp point on the left
        dx, dy = xl - xr, yl - yr
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        return (f'<polygon points="{xr + nx * hw:.1f},{yr + ny * hw:.1f} {xl:.1f},{yl:.1f} '
                f'{xr - nx * hw:.1f},{yr - ny * hw:.1f}" class="{cls}"/>')

    neon_arc = arc(R, 300, 90)         # top-right dial; lower-LEFT opened for the speed lines
    white_arc = arc(R + 2, 300, 20)    # white rim highlight
    # CLOCK face markers: round hour pips at 10/11/1/2, with an emphasized 12 at top.
    marks = ""
    for d in (300, 330, 30, 60):
        mx, my = pt(cx, cy, R - 15, d)
        marks += f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="4" class="pip"/>'
    tx0, ty0 = pt(cx, cy, R - 11, 0)
    tx1, ty1 = pt(cx, cy, R - 23, 0)
    marks += f'<line x1="{tx0:.1f}" y1="{ty0:.1f}" x2="{tx1:.1f}" y2="{ty1:.1f}" class="twelve"/>'
    parts = [
        f'<path d="{neon_arc}" class="ao"/>',
        f'<path d="{white_arc}" class="aw"/>',
        marks,
        # 3 tapered speed lines: graduated + converging fan (top/mid slant down into bottom)
        line(470, 278, 330, 292, 3.4, "sw"),   # top (shortest, slants down-left)
        line(476, 294, 250, 310, 4.0, "sn"),   # middle (medium, slants down-left)
        line(468, 310, 158, 322, 3.4, "sw"),   # bottom (longest — reaches the P)
        hand(305, R * 0.44, 7.5),    # hour hand (short + thick, up-left toward 10)
        hand(38, R * 0.82, 5.0),     # minute hand (long + thin, up-right toward 1)
        f'<circle cx="{hub[0]}" cy="{hub[1]}" r="10" class="hubw"/>',   # hub sits on the i
        f'<circle cx="{hub[0]}" cy="{hub[1]}" r="5" class="hub"/>',
    ]
    style = (
        f"<style>.ao{{fill:none;stroke:{NEON};stroke-width:{SW};stroke-linecap:round}}"
        f".aw{{fill:none;stroke:#f4f6f5;stroke-width:6;stroke-linecap:round}}"
        f".pip{{fill:#f4f6f5}}.twelve{{stroke:#f4f6f5;stroke-width:6;stroke-linecap:round}}"
        f".hd{{fill:{NEON}}}.hubw{{fill:{NEON}}}.hub{{fill:#0b0c10}}"
        f".sn{{fill:{NEON}}}.sw{{fill:#f4f6f5}}</style>"
    )
    return (
        f'<svg viewBox="0 0 {W} {H}" style="width:{W}px;height:{H}px">'
        f"{style}{''.join(parts)}</svg>"
    )


def build_logo_art():
    """Recoloured reference wordmark, restyled: the entire speedometer motif (dial,
    ticks, needle AND the speed streaks) is removed, the 'I' in TIME is shortened to
    a lowercase 'i', and a HALF-CLOCK dial (E-of-PRIME -> M-of-TIME) with hands
    rising from the i-dot is composited on top. Returns the neon-on-black RGB master
    used for the light/dark variants."""
    import numpy as np
    from scipy import ndimage
    from PIL import Image

    neon = recolor_reference()
    a = np.array(neon).astype(np.uint8)
    H, W, _ = a.shape
    lbl, n = ndimage.label(a.max(2) > 40)

    def bb(i):
        ys, xs = np.where(lbl == i)
        return xs.min(), xs.max(), ys.min(), ys.max()

    drop, i_id = set(), None
    for i in range(1, n + 1):
        x0, x1, y0, y1 = bb(i)
        if y0 < 336:                           # whole speedometer band + streaks
            drop.add(i)
        if 535 < x0 < 545 and 578 < x1 < 586 and 335 < y0 < 342:
            i_id = i                           # the I in TIME
    a[np.isin(lbl, list(drop))] = (0, 0, 0)
    a[:336, :] = (0, 0, 0)                     # kill sub-threshold ghosts above the word
    # lowercase the "i": chop the top of the stem, leaving a gap for the dot
    ys = np.where(lbl == i_id)[0]
    a[(lbl == i_id) & (np.arange(H)[:, None] < ys.min() + 24)] = (0, 0, 0)

    art = Image.fromarray(a, "RGB").convert("RGBA")
    emb = _render_svg(clock_emblem_svg(W, H), W, H).resize((W, H), Image.LANCZOS)
    art.alpha_composite(emb)
    return art.convert("RGB")


def _variants(neon):
    """Two transparent cutouts of the black-bg neon logo: a dark-mode version
    (neon + white ink) and a light-mode version (neon + near-black ink). Alpha is
    taken from luminance so the black background drops out cleanly on both."""
    import numpy as np
    from PIL import Image

    arr = np.array(neon).astype(np.float32)
    alpha = np.clip((arr.max(-1) - 14) / 40.0, 0, 1) * 255
    dark = Image.fromarray(np.dstack([arr, alpha]).astype(np.uint8), "RGBA")

    hsv = np.array(neon.convert("HSV")).astype(np.float32)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    is_neon = (h > 55) & (h < 100) & (s > 80) & (v > 40)
    col = arr.copy()
    col[~is_neon] = [11, 12, 16]          # flip white neutrals -> ink for light bg
    col[is_neon] = [22, 163, 74]          # neon -> app light-mode accent (#16a34a) so
                                          # the logo green matches the UI buttons on white
    light = Image.fromarray(np.dstack([col, alpha]).astype(np.uint8), "RGBA")

    def tight(im):
        bb = im.getchannel("A").point(lambda q: 255 if q > 8 else 0).getbbox()
        return im.crop(bb) if bb else im

    return tight(dark), tight(light)


def main() -> None:
    from PIL import Image

    IMG_DIR.mkdir(parents=True, exist_ok=True)

    # Approved reference recoloured to neon, with the speedometer dial swapped for
    # a prime-time clock and the 'I' in TIME rebuilt as a checkmark, then split
    # into transparent light/dark variants so the logo reads on any background.
    neon = build_logo_art()
    dark, light = _variants(neon)
    dark.save(IMG_DIR / "logo.png")          # dark-mode (neon + white ink)
    light.save(IMG_DIR / "logo-light.png")   # light-mode (neon + dark ink)

    # invite-og.png — render the card background, composite the dark logo.
    render(card_html(), "#card", IMG_DIR / "invite-og.png")
    card = Image.open(IMG_DIR / "invite-og.png").convert("RGBA")
    scale = card.width / 1200.0
    target_w = int(430 * scale)
    lg = dark.resize((target_w, int(dark.height * target_w / dark.width)), Image.LANCZOS)
    card.alpha_composite(
        lg, (int(852 * scale) - lg.width // 2, card.height // 2 - lg.height // 2)
    )
    card.convert("RGB").save(IMG_DIR / "invite-og.png")
    downscale(IMG_DIR / "invite-og.png", 1200)

    # logo-mark.png — the speedometer emblem tile (favicon / app icon).
    render(mark_html(), "#tilewrap", IMG_DIR / "logo-mark.png")
    downscale(IMG_DIR / "logo-mark.png", 512)


if __name__ == "__main__":
    main()
