"""Dynamic Open Graph share cards.

Renders a 1200x630 PNG "standings card" for a league on the fly (brand-dark
background, neon accents, league name, and the top of the leaderboard) so shared
links unfurl like an ESPN/Sleeper share image instead of a generic logo.

Kept dependency-light: Pillow + two bundled OFL fonts (Anton for headlines and
big numbers, Barlow for names/labels), so it renders identically in dev and prod
without relying on system fonts.
"""
from __future__ import annotations

import io
import os

from django.conf import settings

# 1200x630 is the canonical OG/Twitter large-image size.
W, H = 1200, 630

# Brand palette.
BG = (10, 10, 10)              # #0a0a0a
CARD = (20, 22, 20)            # subtle panel
NEON = (57, 255, 20)          # #39ff14
WHITE = (245, 245, 245)
MUTED = (150, 150, 150)
GOLD = (255, 196, 0)
ROW_ALT = (26, 28, 26)

# Static source dir is BASE_DIR/static (BASE_DIR is the inner project package).
_FONT_DIR = os.path.join(settings.BASE_DIR, 'static', 'fonts')


def _font(name, size):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(os.path.join(_FONT_DIR, name), size)
    except OSError:
        return ImageFont.load_default()


def _truncate(draw, text, font, max_width):
    """Ellipsize text to fit within max_width px."""
    if draw.textlength(text, font=font) <= max_width:
        return text
    ell = '…'
    while text and draw.textlength(text + ell, font=font) > max_width:
        text = text[:-1]
    return (text + ell) if text else ell


def render_standings_card(league, standings, current_week=None):
    """Return PNG bytes for a league standings share card.

    ``standings`` is the list from ``League.get_standings()`` (already ranked).
    """
    from PIL import Image, ImageDraw

    img = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)

    f_brand = _font('Anton-Regular.ttf', 40)
    f_title = _font('Anton-Regular.ttf', 72)
    f_kicker = _font('Barlow-Bold.ttf', 30)
    f_head = _font('Barlow-Bold.ttf', 26)
    f_name = _font('Barlow-SemiBold.ttf', 40)
    f_num = _font('Anton-Regular.ttf', 40)
    f_foot = _font('Barlow-SemiBold.ttf', 28)

    pad = 64

    # Top neon rule + brand wordmark.
    draw.rectangle([0, 0, W, 8], fill=NEON)
    draw.text((pad, 40), 'PRIMETIMEPIX', font=f_brand, fill=NEON)
    kicker = 'NFL PRIMETIME PICK\u2019EM'
    draw.text(
        (W - pad - draw.textlength(kicker, font=f_kicker), 52),
        kicker, font=f_kicker, fill=MUTED,
    )

    # League name (headline), truncated to fit.
    name = _truncate(draw, league.name, f_title, W - 2 * pad)
    draw.text((pad, 120), name, font=f_title, fill=WHITE)

    sub = 'LIVE STANDINGS'
    if current_week:
        sub += f'   \u00b7   WEEK {current_week}'
    draw.text((pad, 210), sub, font=f_kicker, fill=NEON)

    # Leaderboard panel.
    top = standings[:5]
    panel_x0, panel_y0, panel_x1 = pad, 268, W - pad
    row_h = 62
    panel_y1 = panel_y0 + 44 + row_h * max(len(top), 1) + 12
    draw.rounded_rectangle([panel_x0, panel_y0, panel_x1, panel_y1], radius=18, fill=CARD)

    # Column positions.
    x_rank = panel_x0 + 34
    x_name = panel_x0 + 110
    x_pts = panel_x1 - 60
    x_rec = panel_x1 - 230

    # Header row.
    hy = panel_y0 + 14
    draw.text((x_rank, hy), '#', font=f_head, fill=MUTED)
    draw.text((x_name, hy), 'PLAYER', font=f_head, fill=MUTED)
    draw.text((x_rec - draw.textlength('W-L', font=f_head), hy), 'W-L', font=f_head, fill=MUTED)
    draw.text((x_pts - draw.textlength('PTS', font=f_head), hy), 'PTS', font=f_head, fill=MUTED)

    ry = panel_y0 + 48
    if not top:
        draw.text((x_name, ry + 8), 'No picks yet \u2014 standings open once games finish.',
                  font=f_name, fill=MUTED)
    for i, row in enumerate(top):
        rank = i + 1
        if i % 2 == 1:
            draw.rounded_rectangle(
                [panel_x0 + 12, ry - 6, panel_x1 - 12, ry + row_h - 12],
                radius=10, fill=ROW_ALT,
            )
        rank_color = GOLD if rank == 1 else WHITE
        draw.text((x_rank, ry), str(rank), font=f_num, fill=rank_color)

        username = getattr(row.get('user'), 'username', '') if isinstance(row, dict) else ''
        username = _truncate(draw, username, f_name, x_rec - x_name - 24)
        draw.text((x_name, ry - 2), username, font=f_name, fill=WHITE)

        record = row.get('record', '') if isinstance(row, dict) else ''
        draw.text((x_rec - draw.textlength(record, font=f_name), ry - 2),
                  record, font=f_name, fill=MUTED)

        pts = str(row.get('total_points', 0) if isinstance(row, dict) else 0)
        draw.text((x_pts - draw.textlength(pts, font=f_num), ry),
                  pts, font=f_num, fill=NEON)
        ry += row_h

    # Footer.
    foot = 'Free NFL primetime pick\u2019em with friends \u00b7 primetimepixsports.com'
    draw.text((pad, H - 56), foot, font=f_foot, fill=MUTED)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
