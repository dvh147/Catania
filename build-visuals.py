#!/usr/bin/env python3
"""
build-visuals.py
Generates SVG infographics and fetches photos from Wikimedia Commons
for all chapters of the Catania travel guide.

Usage:
    python3 build-visuals.py              # generate everything
    python3 build-visuals.py --svgs-only  # only generate SVG infographics
    python3 build-visuals.py --photos-only # only fetch photos
    python3 build-visuals.py --dry-run    # show what would happen, write nothing

Requirements: Python 3.6+ stdlib only — no pip installs needed.
"""

import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

IMAGES_DIR = Path("images")
CHAPTERS_DIR = Path(".")

# ── Colour palette ─────────────────────────────────────────────────────────────
RAIN       = "#4A90D9"
SUN        = "#F5A623"
GREEN      = "#27AE60"
DARK       = "#2C3E50"
MID        = "#7F8C8D"
LIGHT      = "#ECF0F1"
ORANGE     = "#E8700A"
WHITE      = "#FFFFFF"
BG         = "#FAFAFA"
PURPLE     = "#8E44AD"
TEAL       = "#16A085"
RED        = "#E74C3C"

# ══════════════════════════════════════════════════════════════════════════════
# SVG generators
# ══════════════════════════════════════════════════════════════════════════════

def svg_week_at_a_glance():
    days = [
        ("Sat 14", "Arrive",    62,  "partial"),
        ("Sun 15", "Catania",   87,  "heavy"),
        ("Mon 16", "Syracuse",  90,  "heavy"),
        ("Tue 17", "Taormina",  90,  "heavy"),
        ("Wed 18", "Coast",     80,  "rain"),
        ("Thu 19", "Etna ☀",   13,  "sun"),
        ("Fri 20", "Depart",    85,  "rain"),
    ]

    W, H = 714, 260
    cw = W / 7

    def cell(i, date, plan, pct, icon):
        x = i * cw
        is_thu = icon == "sun"
        bg        = GREEN  if is_thu else LIGHT
        text_col  = WHITE  if is_thu else DARK
        plan_col  = WHITE  if is_thu else ORANGE
        bar_bg    = "rgba(255,255,255,0.4)" if is_thu else "#D5E8F0"
        rain_col  = SUN if pct < 30 else (RAIN if pct > 60 else "#90CAF9")

        out = [f'<rect x="{x:.1f}" y="0" width="{cw:.1f}" height="{H}" fill="{bg}" stroke="{WHITE}" stroke-width="2"/>']

        # Date
        out.append(f'<text x="{x+cw/2:.1f}" y="26" text-anchor="middle" font-size="11" font-weight="bold" fill="{text_col}" font-family="system-ui,sans-serif">{date}</text>')
        # Plan
        out.append(f'<text x="{x+cw/2:.1f}" y="46" text-anchor="middle" font-size="13" font-weight="bold" fill="{plan_col}" font-family="system-ui,sans-serif">{plan}</text>')

        # Weather icon centred at cy=105
        cx, cy = x + cw/2, 105
        if icon == "sun":
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="16" fill="{SUN}"/>')
            for deg in range(0, 360, 45):
                r = math.radians(deg)
                x1, y1 = cx + 21*math.cos(r), cy + 21*math.sin(r)
                x2, y2 = cx + 27*math.cos(r), cy + 27*math.sin(r)
                out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{SUN}" stroke-width="2.5"/>')
        else:
            cloud_fill = "#78909C" if icon == "heavy" else "#B0BEC5"
            out.append(f'<ellipse cx="{cx:.1f}"     cy="{cy-7:.1f}" rx="17" ry="10" fill="{cloud_fill}"/>')
            out.append(f'<ellipse cx="{cx-8:.1f}"   cy="{cy-3:.1f}" rx="12" ry="8"  fill="{cloud_fill}"/>')
            drop_col = RAIN if icon in ("heavy","rain") else "#90CAF9"
            n_drops = 3 if icon == "heavy" else 2
            for d in range(n_drops):
                dx = (d - n_drops//2) * 8
                out.append(f'<line x1="{cx+dx:.1f}" y1="{cy+6:.1f}" x2="{cx+dx-3:.1f}" y2="{cy+17:.1f}" stroke="{drop_col}" stroke-width="2" stroke-linecap="round"/>')

        # Rain bar
        bx, by, bh = x+8, 148, 8
        bw_max = cw - 16
        bw = bw_max * pct / 100
        out.append(f'<rect x="{bx:.1f}" y="{by}" width="{bw_max:.1f}" height="{bh}" rx="4" fill="{bar_bg}"/>')
        out.append(f'<rect x="{bx:.1f}" y="{by}" width="{bw:.1f}"     height="{bh}" rx="4" fill="{rain_col}"/>')
        out.append(f'<text x="{x+cw/2:.1f}" y="{by+22}" text-anchor="middle" font-size="11" fill="{text_col}" font-family="system-ui,sans-serif">{pct}% rain</text>')

        if is_thu:
            out.append(f'<text x="{x+cw/2:.1f}" y="{H-10}" text-anchor="middle" font-size="9" font-weight="bold" fill="{WHITE}" font-family="system-ui,sans-serif">THE CLEAR DAY</text>')

        return "".join(out)

    cells = "".join(cell(i, *d) for i, d in enumerate(days))
    title = f'<text x="{W/2:.1f}" y="-8" text-anchor="middle" font-size="13" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">14–20 March 2026 · Catania — Week at a Glance</text>'

    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -28 {W} {H+32}" width="{W}" height="{H+32}" style="background:{BG}">{title}{cells}</svg>'


def svg_etna_cross_section():
    W, H = 720, 400
    mountain_l, mountain_r, peak_x = 90, W-180, W//2 - 10

    def ay(alt):  # altitude to SVG y
        return H - 50 - (alt / 3357) * (H - 100)

    zones = [
        (0,    500,  "#66BB6A", None),
        (500,  1200, "#AED581", None),
        (1200, 1900, "#8D6E63", None),
        (1900, 2500, "#78909C", None),
        (2500, 2900, "#546E7A", None),
        (2900, 3357, "#37474F", None),
    ]

    zone_rects = []
    for lo, hi, col, _ in zones:
        yt, yb = ay(hi), ay(lo)
        zone_rects.append(f'<rect x="{mountain_l}" y="{yt:.1f}" width="{mountain_r-mountain_l}" height="{yb-yt:.1f}" fill="{col}" opacity="0.75"/>')

    peak_y = ay(3357)
    base_y = ay(0)
    silhouette = f"M{mountain_l},{base_y:.1f} L{peak_x},{peak_y:.1f} L{mountain_r},{base_y:.1f}Z"

    markers = [
        (3357, "Summit craters",     "Four active craters · fumaroles · steam"),
        (2900, "Jeep zone top",      "4x4 shuttles from cable car upper station"),
        (2500, "Cable car — upper",  "Upper station · ~0–8°C in March"),
        (1900, "Rifugio Sapienza",   "Cable car base · car park · restaurant"),
        (1500, "Lower lava fields",  "2001/2002 flows · free access by road"),
        (600,  "Zafferana Etnea",    "Eastern slope village · honey · lunch stop"),
        (0,    "Catania",            "Your base · 45 min drive to Rifugio"),
    ]

    right_x = mountain_r + 12
    marker_svg = []
    for alt, name, note in markers:
        y = ay(alt)
        marker_svg += [
            f'<line x1="{mountain_l-28}" y1="{y:.1f}" x2="{mountain_l-4}" y2="{y:.1f}" stroke="{DARK}" stroke-width="1" stroke-dasharray="3,2"/>',
            f'<text x="{mountain_l-32}" y="{y+4:.1f}" text-anchor="end" font-size="8.5" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">{alt}m</text>',
            f'<line x1="{mountain_r+4}" y1="{y:.1f}" x2="{right_x}" y2="{y:.1f}" stroke="{MID}" stroke-width="1"/>',
            f'<text x="{right_x+4}" y="{y-3:.1f}" font-size="9.5" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">{name}</text>',
            f'<text x="{right_x+4}" y="{y+9:.1f}" font-size="8" fill="{MID}" font-family="system-ui,sans-serif">{note}</text>',
        ]

    # Cable car dashed line
    ccx = peak_x - 15
    cable = [
        f'<line x1="{ccx}" y1="{ay(1900):.1f}" x2="{ccx}" y2="{ay(2500):.1f}" stroke="{SUN}" stroke-width="2" stroke-dasharray="5,3"/>',
        f'<text x="{ccx-4}" y="{(ay(1900)+ay(2500))/2:.1f}" text-anchor="end" font-size="8" font-weight="bold" fill="{SUN}" font-family="system-ui,sans-serif">cable car</text>',
    ]

    title = f'<text x="{W/2}" y="18" text-anchor="middle" font-size="14" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">Mount Etna — Altitude Guide</text>'
    subtitle = f'<text x="{W/2}" y="34" text-anchor="middle" font-size="9.5" fill="{MID}" font-family="system-ui,sans-serif">Summit 3,357m · Europe\'s largest active volcano · 45 min drive from Catania</text>'

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'{title}{subtitle}'
            f'<defs><clipPath id="mc"><path d="{silhouette}"/></clipPath></defs>'
            f'<g clip-path="url(#mc)">{"".join(zone_rects)}</g>'
            f'<path d="{silhouette}" fill="none" stroke="{DARK}" stroke-width="2"/>'
            f'{"".join(cable)}{"".join(marker_svg)}</svg>')


def svg_temperature_by_month():
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    highs  = [15,   16,   18,   21,   25,   29,   32,   32,   29,   25,   20,   16]
    lows   = [8,    9,    11,   13,   17,   21,   24,   24,   21,   17,   13,   9]

    W, H = 660, 300
    pl, pr, pt, pb = 50, 20, 55, 50
    cw = (W-pl-pr) / 12
    bw = cw * 0.34
    max_t = 36

    def ty(t):
        return pt + (H-pt-pb) - (t/max_t)*(H-pt-pb)

    parts = []
    # Grid
    for t in [0, 10, 20, 30]:
        y = ty(t)
        parts += [
            f'<line x1="{pl}" y1="{y:.1f}" x2="{W-pr}" y2="{y:.1f}" stroke="{LIGHT}" stroke-width="1"/>',
            f'<text x="{pl-5}" y="{y+4:.1f}" text-anchor="end" font-size="9" fill="{MID}" font-family="system-ui,sans-serif">{t}°C</text>',
        ]

    # Summer warning band (Jun-Aug = indices 5-7)
    sw_x = pl + 5.5*cw
    sw_w = 2*cw
    parts.append(f'<rect x="{sw_x:.1f}" y="{pt}" width="{sw_w:.1f}" height="{H-pt-pb}" fill="{RED}" opacity="0.07"/>')
    parts.append(f'<text x="{sw_x+sw_w/2:.1f}" y="{pt+14}" text-anchor="middle" font-size="8.5" fill="{RED}" font-family="system-ui,sans-serif">too hot</text>')

    # Bars
    for i, (m, hi, lo) in enumerate(zip(months, highs, lows)):
        xc = pl + (i+0.5)*cw
        is_mar = (i == 2)
        hi_col = ORANGE if is_mar else "#F4A460"
        lo_col = RAIN   if is_mar else "#87CEEB"
        wt = "bold" if is_mar else "normal"
        tc = DARK if is_mar else MID

        # High bar (left of centre)
        parts.append(f'<rect x="{xc-bw:.1f}" y="{ty(hi):.1f}" width="{bw:.1f}" height="{ty(0)-ty(hi):.1f}" fill="{hi_col}" rx="2"/>')
        # Low bar (right of centre)
        parts.append(f'<rect x="{xc:.1f}"     y="{ty(lo):.1f}" width="{bw:.1f}" height="{ty(0)-ty(lo):.1f}" fill="{lo_col}" rx="2"/>')
        # Month label
        parts.append(f'<text x="{xc:.1f}" y="{H-pb+16}" text-anchor="middle" font-size="10" font-weight="{wt}" fill="{tc}" font-family="system-ui,sans-serif">{m}</text>')
        if is_mar:
            parts.append(f'<text x="{xc-bw/2:.1f}" y="{ty(hi)-4:.1f}" text-anchor="middle" font-size="8.5" fill="{ORANGE}" font-weight="bold" font-family="system-ui,sans-serif">{hi}°</text>')
            parts.append(f'<text x="{xc+bw/2:.1f}" y="{ty(lo)-4:.1f}" text-anchor="middle" font-size="8.5" fill="{RAIN}"   font-weight="bold" font-family="system-ui,sans-serif">{lo}°</text>')
            parts.append(f'<text x="{xc:.1f}" y="{pt-20}" text-anchor="middle" font-size="9.5" font-weight="bold" fill="{GREEN}" font-family="system-ui,sans-serif">YOUR VISIT</text>')
            parts.append(f'<line x1="{xc:.1f}" y1="{pt-14}" x2="{xc:.1f}" y2="{pt-4}" stroke="{GREEN}" stroke-width="2" marker-end="url(#arr)"/>')

    title = f'<text x="{W/2}" y="22" text-anchor="middle" font-size="13" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">Catania — Average Monthly Temperatures</text>'
    legend = (f'<rect x="{W-180}" y="36" width="12" height="12" fill="{ORANGE}" rx="2"/>'
              f'<text x="{W-163}" y="47" font-size="9" fill="{DARK}" font-family="system-ui,sans-serif">Avg daily high</text>'
              f'<rect x="{W-180}" y="53" width="12" height="12" fill="{RAIN}" rx="2"/>'
              f'<text x="{W-163}" y="64" font-size="9" fill="{DARK}" font-family="system-ui,sans-serif">Avg daily low</text>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'<defs><marker id="arr" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6Z" fill="{GREEN}"/></marker></defs>'
            f'{title}{legend}{"".join(parts)}</svg>')


def svg_syracuse_timeline():
    W, H = 720, 220
    events = [
        (-734, "734 BC", "Greeks found\nSyracusae"),
        (-413, "413 BC", "Athenian fleet\ndefeated"),
        (-212, "212 BC", "Rome conquers\nSicily"),
        ( 535, "535 AD", "Byzantine\nEmpire"),
        ( 878, "878",    "Arab\nconquest"),
        (1085, "1085",   "Norman\nrule"),
        (1693, "1693",   "Earthquake +\nbaroque rebuild"),
        (2005, "2005",   "UNESCO World\nHeritage Site"),
    ]
    pad = 55
    span = events[-1][0] - events[0][0]
    ty = H // 2 + 15

    def ex(yr):
        return pad + (yr - events[0][0]) / span * (W - 2*pad)

    parts = [f'<line x1="{pad}" y1="{ty}" x2="{W-pad}" y2="{ty}" stroke="{MID}" stroke-width="2"/>']

    # BC/AD divider
    dx = ex(0)
    parts.append(f'<line x1="{dx:.1f}" y1="{pad}" x2="{dx:.1f}" y2="{H-pad}" stroke="{LIGHT}" stroke-width="1" stroke-dasharray="4,3"/>')
    parts.append(f'<text x="{dx+3}" y="{pad+10}" font-size="8" fill="{MID}" font-family="system-ui,sans-serif">BC/AD</text>')

    for i, (yr, label, note) in enumerate(events):
        x = ex(yr)
        above = (i % 2 == 0)
        col = RAIN if yr < 0 else ORANGE

        parts.append(f'<circle cx="{x:.1f}" cy="{ty}" r="5" fill="{col}"/>')

        if above:
            yl = ty - 30
            parts.append(f'<line x1="{x:.1f}" y1="{ty-6}" x2="{x:.1f}" y2="{yl+18}" stroke="{col}" stroke-width="1.5"/>')
            parts.append(f'<text x="{x:.1f}" y="{yl}" text-anchor="middle" font-size="8.5" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">{label}</text>')
            for j, ln in enumerate(note.split("\n")):
                parts.append(f'<text x="{x:.1f}" y="{yl+12+j*10}" text-anchor="middle" font-size="8" fill="{MID}" font-family="system-ui,sans-serif">{ln}</text>')
        else:
            yl = ty + 45
            parts.append(f'<line x1="{x:.1f}" y1="{ty+6}" x2="{x:.1f}" y2="{yl-18}" stroke="{col}" stroke-width="1.5"/>')
            parts.append(f'<text x="{x:.1f}" y="{yl}" text-anchor="middle" font-size="8.5" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">{label}</text>')
            for j, ln in enumerate(note.split("\n")):
                parts.append(f'<text x="{x:.1f}" y="{yl+12+j*10}" text-anchor="middle" font-size="8" fill="{MID}" font-family="system-ui,sans-serif">{ln}</text>')

    title = f'<text x="{W/2}" y="22" text-anchor="middle" font-size="13" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">Syracuse — 2,700 Years of History</text>'

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'{title}{"".join(parts)}</svg>')


def svg_daily_budget():
    # Per-day costs for 5 people (2 adults + 2 grandparents + toddler)
    scenarios = [
        ("Budget day",             "Street food · free sights · picnic",         120, 180),
        ("Mid-range day",          "Bar breakfast · trattoria lunch · dinner",    200, 320),
        ("Taormina day",           "Funivia · toll · lunch · good dinner",        220, 360),
        ("Etna (cable car+jeep)",  "Cable car · jeep · guide · lunch",            280, 440),
        ("Etna (lava fields)",     "Petrol · Zafferana lunch · gelato",            90, 150),
        ("Syracuse day",           "Motorway · park/museum entry · lunch",        160, 260),
        ("Coast day",              "Petrol · seafront trattoria · gelato",        100, 180),
    ]
    colours = [GREEN, RAIN, ORANGE, PURPLE, TEAL, "#E91E63", "#FF9800"]

    W, H = 660, 290
    pl, pr, pt, pb = 200, 80, 52, 35
    max_v = 500

    parts = []

    # Grid lines
    for v in [0, 100, 200, 300, 400, 500]:
        gx = pl + v/max_v*(W-pl-pr)
        parts += [
            f'<line x1="{gx:.1f}" y1="{pt-12}" x2="{gx:.1f}" y2="{H-pb}" stroke="{LIGHT}" stroke-width="1"/>',
            f'<text x="{gx:.1f}" y="{pt-14}" text-anchor="middle" font-size="9" fill="{MID}" font-family="system-ui,sans-serif">€{v}</text>',
        ]

    row_h = (H-pt-pb) / len(scenarios)

    for i, (label, note, lo, hi) in enumerate(scenarios):
        y = pt + i*row_h
        bh = row_h * 0.5
        by = y + row_h*0.25
        col = colours[i % len(colours)]
        lo_x = pl + lo/max_v*(W-pl-pr)
        hi_x = pl + hi/max_v*(W-pl-pr)

        # Row label
        parts.append(f'<text x="{pl-8}" y="{by+bh*0.35:.1f}" text-anchor="end" font-size="10" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">{label}</text>')
        parts.append(f'<text x="{pl-8}" y="{by+bh*0.35+11:.1f}" text-anchor="end" font-size="8.5" fill="{MID}" font-family="system-ui,sans-serif">{note}</text>')
        # Range bar
        parts.append(f'<rect x="{lo_x:.1f}" y="{by:.1f}" width="{hi_x-lo_x:.1f}" height="{bh:.1f}" fill="{col}" rx="3" opacity="0.85"/>')
        # Range label
        parts.append(f'<text x="{hi_x+5}" y="{by+bh*0.7:.1f}" font-size="10" font-weight="bold" fill="{col}" font-family="system-ui,sans-serif">€{lo}–{hi}</text>')

    title = f'<text x="{W/2}" y="22" text-anchor="middle" font-size="13" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">Daily Costs — Group of 5 (2 adults + 2 grandparents + toddler)</text>'
    footnote = f'<text x="{W/2}" y="{H-8}" text-anchor="middle" font-size="8" fill="{MID}" font-family="system-ui,sans-serif">Excludes accommodation · Toddler eats free · Includes all meals, transport, entrance fees for the day</text>'

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'{title}{"".join(parts)}{footnote}</svg>')


def svg_best_time_of_day():
    activities = [
        ("La Pescheria market",     [True,  True,  False, False, False, False]),
        ("Piazza del Duomo",        [False, True,  False, True,  False, True]),
        ("Benedictine Monastery",   [False, False, True,  True,  False, False]),
        ("Castello Ursino",         [False, False, True,  True,  False, False]),
        ("Taormina theatre",        [True,  True,  False, False, False, False]),
        ("Etna cable car",          [True,  True,  False, False, False, False]),
        ("Ortigia (Syracuse)",      [False, True,  True,  True,  False, False]),
        ("Coast / Faraglioni",      [False, True,  True,  False, False, False]),
        ("Aperitivo + passeggiata", [False, False, False, False, True,  True]),
        ("Dinner",                  [False, False, False, False, False, True]),
    ]
    slots = ["6–8am", "9–11am", "Noon–2pm\n(nap)", "3–5pm", "6–8pm", "8–10pm"]

    W, H = 680, 320
    pl, pr, pt, pb = 185, 18, 60, 28

    cw = (W-pl-pr) / len(slots)
    rh = (H-pt-pb) / len(activities)

    parts = []

    # Column headers
    for j, slot in enumerate(slots):
        x = pl + j*cw + cw/2
        is_nap = "nap" in slot
        col = RAIN if is_nap else DARK
        for k, ln in enumerate(slot.split("\n")):
            parts.append(f'<text x="{x:.1f}" y="{pt-18+k*12}" text-anchor="middle" font-size="9" font-weight="bold" fill="{col}" font-family="system-ui,sans-serif">{ln}</text>')

    for i, (label, good) in enumerate(activities):
        yc = pt + i*rh + rh/2
        parts.append(f'<text x="{pl-8}" y="{yc+4:.1f}" text-anchor="end" font-size="9.5" fill="{DARK}" font-family="system-ui,sans-serif">{label}</text>')
        for j, is_good in enumerate(good):
            x = pl + j*cw
            y = pt + i*rh
            is_nap = j == 2
            if is_good:
                fill = "#FFD580" if is_nap else "#A8D8A8"
                mark = "~" if is_nap else "✓"
                mark_col = "#B8860B" if is_nap else GREEN
            else:
                fill = LIGHT
                mark = ""
                mark_col = DARK
            parts.append(f'<rect x="{x+2:.1f}" y="{y+2:.1f}" width="{cw-4:.1f}" height="{rh-4:.1f}" fill="{fill}" rx="3" opacity="0.7"/>')
            if mark:
                parts.append(f'<text x="{x+cw/2:.1f}" y="{yc+5:.1f}" text-anchor="middle" font-size="13" fill="{mark_col}" font-family="system-ui,sans-serif">{mark}</text>')

    title = f'<text x="{W/2}" y="22" text-anchor="middle" font-size="13" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">Best Time of Day — When to Do What</text>'
    legend = (f'<rect x="{W-175}" y="34" width="12" height="12" fill="#A8D8A8" rx="2"/>'
              f'<text x="{W-157}" y="45" font-size="9" fill="{DARK}" font-family="system-ui,sans-serif">Good slot</text>'
              f'<rect x="{W-100}" y="34" width="12" height="12" fill="#FFD580" rx="2"/>'
              f'<text x="{W-82}" y="45" font-size="9" fill="{DARK}" font-family="system-ui,sans-serif">Nap window</text>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'{title}{legend}{"".join(parts)}</svg>')


def svg_sicily_at_a_glance():
    W, H = 600, 280

    stats = [
        ("25,711 km²",  "Area",            "Largest island\nin the Mediterranean"),
        ("5 million",   "Population",      ""),
        ("3,357m",      "Mt Etna",         "Europe's largest\nactive volcano"),
        ("~1,000 km",   "Coastline",       ""),
        ("9",           "Provinces",       "Catania is on\nthe eastern coast"),
        ("March 2026",  "Your visit",      "Blood oranges ·\noff-season · mild"),
    ]

    cols = 3
    rows = 2
    cw = W / cols
    rh = (H - 50) / rows

    parts = []
    title = f'<text x="{W/2}" y="28" text-anchor="middle" font-size="15" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">Sicily at a Glance</text>'
    parts.append(title)

    colours = [ORANGE, RAIN, RED, GREEN, PURPLE, TEAL]
    for i, (value, label, note) in enumerate(stats):
        col_i = i % cols
        row_i = i // cols
        x = col_i * cw + cw/2
        y = 50 + row_i * rh

        col = colours[i]
        # Background card
        parts.append(f'<rect x="{col_i*cw+6:.1f}" y="{y:.1f}" width="{cw-12:.1f}" height="{rh-8:.1f}" fill="{col}" rx="8" opacity="0.08"/>')
        parts.append(f'<text x="{x:.1f}" y="{y+28:.1f}" text-anchor="middle" font-size="20" font-weight="bold" fill="{col}" font-family="system-ui,sans-serif">{value}</text>')
        parts.append(f'<text x="{x:.1f}" y="{y+44:.1f}" text-anchor="middle" font-size="10" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">{label}</text>')
        for j, ln in enumerate(note.split("\n") if note else []):
            parts.append(f'<text x="{x:.1f}" y="{y+58+j*12:.1f}" text-anchor="middle" font-size="9" fill="{MID}" font-family="system-ui,sans-serif">{ln}</text>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'{"".join(parts)}</svg>')


def svg_catania_markets():
    W, H = 640, 300

    markets = [
        {
            "name": "La Pescheria",
            "hours": "Mon–Sat  6am–2pm",
            "best": "7–9am (busiest, best fish)",
            "buy": "Fresh fish · sea urchin · clams\nOctopus · swordfish · tuna",
            "eat": "Boiled octopus · fried stall food\nStreet vendors at the edges",
            "stroller": "★★★☆ Narrow in centre · carrier best",
            "tip": "Arrive before 8am. The middle\nof the market is for professionals.",
            "col": RAIN,
        },
        {
            "name": "Mercato di Via Plebiscito",
            "hours": "Mon–Sat  7am–2pm",
            "best": "9–11am (quieter, more relaxed)",
            "buy": "Fruit · veg · herbs · spices\nBlood oranges · lemons · capers",
            "eat": "Less food at stalls — eat\nbefore or after at nearby bars",
            "stroller": "★★★★ Wider aisles, more manageable",
            "tip": "Buy blood oranges in bulk here.\nCheaper than tourist spots.",
            "col": ORANGE,
        },
    ]

    parts = []
    title = f'<text x="{W/2}" y="24" text-anchor="middle" font-size="14" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">The Markets of Catania</text>'
    parts.append(title)

    cw = W / 2
    for i, m in enumerate(markets):
        x = i * cw
        col = m["col"]
        # Header
        parts.append(f'<rect x="{x+6:.1f}" y="36" width="{cw-12:.1f}" height="24" fill="{col}" rx="4" opacity="0.85"/>')
        parts.append(f'<text x="{x+cw/2:.1f}" y="53" text-anchor="middle" font-size="12" font-weight="bold" fill="{WHITE}" font-family="system-ui,sans-serif">{m["name"]}</text>')

        rows = [
            ("Hours",   m["hours"]),
            ("Best at", m["best"]),
            ("Buy",     m["buy"]),
            ("Eat",     m["eat"]),
            ("Stroller",m["stroller"]),
            ("Tip",     m["tip"]),
        ]
        y = 72
        for label, text in rows:
            parts.append(f'<text x="{x+10}" y="{y}" font-size="8.5" font-weight="bold" fill="{col}" font-family="system-ui,sans-serif">{label}</text>')
            for j, ln in enumerate(text.split("\n")):
                parts.append(f'<text x="{x+10}" y="{y+10+j*11}" font-size="8.5" fill="{DARK}" font-family="system-ui,sans-serif">{ln}</text>')
            y += 10 + text.count("\n")*11 + 16

    # Divider
    parts.append(f'<line x1="{cw}" y1="36" x2="{cw}" y2="{H}" stroke="{LIGHT}" stroke-width="2"/>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'{"".join(parts)}</svg>')


def svg_arancino_debate():
    W, H = 600, 260

    parts = []
    title = f'<text x="{W/2}" y="26" text-anchor="middle" font-size="14" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">Arancin<tspan fill="{ORANGE}">o</tspan> vs Arancin<tspan fill="{RAIN}">a</tspan> — The Great Sicilian Debate</text>'
    subtitle = f'<text x="{W/2}" y="42" text-anchor="middle" font-size="10" fill="{MID}" font-family="system-ui,sans-serif">Both are the same thing: a fried rice ball filled with ragù or cheese. The name is the war.</text>'
    parts += [title, subtitle]

    sides = [
        {"name": "Arancino", "m": "♂", "region": "Catania + eastern Sicily", "logic": "Una palla · masc. noun\n(it's ball-shaped)", "col": ORANGE},
        {"name": "Arancina", "f": "♀", "region": "Palermo + western Sicily", "logic": "La palla · fem. noun\n(orange = arancia, fem.)", "col": RAIN},
    ]

    cw = W / 2
    for i, s in enumerate(sides):
        x = i * cw
        col = s["col"]
        # Background
        parts.append(f'<rect x="{x+10}" y="54" width="{cw-20}" height="{H-68}" fill="{col}" rx="8" opacity="0.08"/>')
        # Name
        parts.append(f'<text x="{x+cw/2:.1f}" y="78" text-anchor="middle" font-size="24" font-weight="bold" fill="{col}" font-family="system-ui,sans-serif">{s["name"]}</text>')
        # Region
        parts.append(f'<text x="{x+cw/2:.1f}" y="96" text-anchor="middle" font-size="9.5" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">{s["region"]}</text>')
        # Arancino shape (cone for Catania, sphere for Palermo)
        cx = x + cw/2
        if i == 0:  # cone shape
            parts.append(f'<path d="M{cx-20},{H-100} L{cx+20},{H-100} L{cx},{H-68}Z" fill="{col}" opacity="0.4"/>')
            parts.append(f'<text x="{cx:.1f}" y="{H-78:.1f}" text-anchor="middle" font-size="8" fill="{col}" font-family="system-ui,sans-serif">cone ▲</text>')
        else:  # round shape
            parts.append(f'<circle cx="{cx:.1f}" cy="{H-88:.1f}" r="20" fill="{col}" opacity="0.4"/>')
            parts.append(f'<text x="{cx:.1f}" y="{H-85:.1f}" text-anchor="middle" font-size="8" fill="{col}" font-family="system-ui,sans-serif">round ●</text>')
        # Logic
        for j, ln in enumerate(s["logic"].split("\n")):
            parts.append(f'<text x="{x+cw/2:.1f}" y="{H-44+j*13}" text-anchor="middle" font-size="9" fill="{MID}" font-family="system-ui,sans-serif">{ln}</text>')

    # Verdict
    verdict = f'<text x="{W/2}" y="{H-8}" text-anchor="middle" font-size="9.5" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">In Catania: say "arancino" or risk mild judgement. Both taste identical. Order confidently.</text>'
    parts.append(verdict)
    # VS
    parts.append(f'<text x="{W/2}" y="78" text-anchor="middle" font-size="18" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif" opacity="0.2">vs</text>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'{"".join(parts)}</svg>')


def svg_rainy_day_decision_tree():
    W, H = 660, 320
    parts = []

    # Decision tree nodes: (id, x, y, text, is_decision, colour)
    nodes = {
        "start":     (W//2,    40,  "Rain today?",            True,  DARK),
        "light":     (180,    110,  "Light rain\n(drizzle)",  True,  RAIN),
        "heavy":     (480,    110,  "Heavy rain\n(downpour)", True,  "#37474F"),
        "nap_l":     (90,     185,  "Nap window?",            True,  MID),
        "nap_h":     (300,    185,  "Nap window?",            True,  MID),
        "out_l":     (270,    185,  "Go out!",                False, GREEN),
        "in_h":      (550,    185,  "Stay in",               False, ORANGE),
        "res1":      (50,     265,  "Nap at café\nnear market",False, TEAL),
        "res2":      (145,    265,  "Pescheria +\nPiazza",    False, TEAL),
        "res3":      (260,    265,  "Monastery\ntour",        False, TEAL),
        "res4":      (365,    265,  "Castello\nUrsino",       False, TEAL),
        "res5":      (480,    265,  "Long lunch\n+ nap",      False, TEAL),
        "res6":      (580,    265,  "Cathedral\nor bar",      False, TEAL),
    }

    edges = [
        ("start", "light", "light"),
        ("start", "heavy", "heavy"),
        ("light", "nap_l", "nap now"),
        ("light", "out_l", "not napping"),
        ("heavy", "nap_h", "nap now"),
        ("heavy", "in_h",  "not napping"),
        ("nap_l", "res1",  "yes"),
        ("nap_l", "res2",  "no"),
        ("out_l", "res2",  None),
        ("nap_h", "res3",  "yes"),
        ("nap_h", "res4",  "no"),
        ("in_h",  "res5",  "yes"),
        ("in_h",  "res6",  "no"),
    ]

    # Draw edges first
    for src, dst, label in edges:
        x1, y1 = nodes[src][0], nodes[src][1]+18
        x2, y2 = nodes[dst][0], nodes[dst][1]-18
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LIGHT}" stroke-width="1.5"/>')
        if label:
            mx, my = (x1+x2)//2, (y1+y2)//2
            parts.append(f'<text x="{mx}" y="{my}" text-anchor="middle" font-size="8" fill="{MID}" font-family="system-ui,sans-serif">{label}</text>')

    # Draw nodes
    for nid, (nx, ny, text, is_decision, col) in nodes.items():
        if is_decision:
            parts.append(f'<rect x="{nx-38}" y="{ny-18}" width="76" height="36" rx="18" fill="{col}" opacity="0.12"/>')
            parts.append(f'<rect x="{nx-38}" y="{ny-18}" width="76" height="36" rx="18" fill="none" stroke="{col}" stroke-width="1.5"/>')
        else:
            parts.append(f'<rect x="{nx-38}" y="{ny-18}" width="76" height="36" rx="6" fill="{col}" opacity="0.85"/>')

        tc = WHITE if not is_decision else col
        for j, ln in enumerate(text.split("\n")):
            offset = -5 if "\n" in text else 4
            parts.append(f'<text x="{nx}" y="{ny+offset+j*12}" text-anchor="middle" font-size="8.5" font-weight="bold" fill="{tc}" font-family="system-ui,sans-serif">{ln}</text>')

    title = f'<text x="{W/2}" y="16" text-anchor="middle" font-size="13" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">Rainy Day Decision Tree — Catania</text>'
    parts.insert(0, title)

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'{"".join(parts)}</svg>')


def svg_cyclopean_coast():
    W, H = 640, 280
    stops = [
        ("Catania",      "Your base — 20 min drive north",         DARK,  False),
        ("Aci Castello", "Norman castle on basalt rock over sea\nAny weather · 15 min from Catania",  RAIN,  True),
        ("Aci Trezza",   "The Faraglioni sea stacks\nHarbour, fish lunch, waterfront walk",          ORANGE, True),
        ("Acireale",     "Baroque clifftop city · good pasticcerie\nRainy day alternative to beach", PURPLE, True),
        ("Taormina",     "50 min north by A18\nSeparate day trip — not part of coast day",           MID,   False),
    ]

    parts = []
    title = f'<text x="{W/2}" y="24" text-anchor="middle" font-size="14" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">The Cyclopean Coast — What to Do Where</text>'
    parts.append(title)

    n = len(stops)
    for i, (name, desc, col, is_main) in enumerate(stops):
        x = 60 + i * (W-80) / (n-1)
        # Vertical road line
        if i < n-1:
            xnext = 60 + (i+1) * (W-80) / (n-1)
            parts.append(f'<line x1="{x:.1f}" y1="80" x2="{xnext:.1f}" y2="80" stroke="{LIGHT}" stroke-width="3"/>')
        # Dot
        r = 10 if is_main else 7
        parts.append(f'<circle cx="{x:.1f}" cy="80" r="{r}" fill="{col}" opacity="0.9"/>')
        if not is_main:
            parts.append(f'<circle cx="{x:.1f}" cy="80" r="{r}" fill="none" stroke="{col}" stroke-width="1.5"/>')
        # Name
        parts.append(f'<text x="{x:.1f}" y="105" text-anchor="middle" font-size="10" font-weight="bold" fill="{col}" font-family="system-ui,sans-serif">{name}</text>')
        # Description
        for j, ln in enumerate(desc.split("\n")):
            parts.append(f'<text x="{x:.1f}" y="{120+j*13}" text-anchor="middle" font-size="8.5" fill="{DARK if is_main else MID}" font-family="system-ui,sans-serif">{ln}</text>')

    note = f'<text x="{W/2}" y="{H-8}" text-anchor="middle" font-size="9" fill="{MID}" font-family="system-ui,sans-serif">Drive north along the SP59 coastal road · no motorway needed · Aci Trezza and Aci Castello are 10 min apart</text>'
    parts.append(note)

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'{"".join(parts)}</svg>')


def svg_map_placeholder(title_text, hint):
    W, H = 500, 200
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:{BG}">'
            f'<rect x="8" y="8" width="{W-16}" height="{H-16}" rx="10" fill="none" stroke="{LIGHT}" stroke-width="2"/>'
            f'<text x="{W/2}" y="70" text-anchor="middle" font-size="32" font-family="system-ui,sans-serif">🗺</text>'
            f'<text x="{W/2}" y="105" text-anchor="middle" font-size="14" font-weight="bold" fill="{DARK}" font-family="system-ui,sans-serif">{title_text}</text>'
            f'<text x="{W/2}" y="128" text-anchor="middle" font-size="10" fill="{MID}" font-family="system-ui,sans-serif">{hint}</text>'
            f'<text x="{W/2}" y="155" text-anchor="middle" font-size="9" fill="{MID}" font-family="system-ui,sans-serif">openstreetmap.org → search "Catania historic centre"</text>'
            f'</svg>')


# ══════════════════════════════════════════════════════════════════════════════
# Infographic registry
# ══════════════════════════════════════════════════════════════════════════════
INFOGRAPHICS = {
    "`[INFOGRAPHIC: The Week at a Glance — Real Forecast Edition]`": {
        "file": "week-at-a-glance.svg",
        "gen":  svg_week_at_a_glance,
        "alt":  "Week at a Glance: 14–20 March 2026, daily plans with rain forecast",
    },
    "`[INFOGRAPHIC: Etna Cross-Section]`": {
        "file": "etna-cross-section.svg",
        "gen":  svg_etna_cross_section,
        "alt":  "Mount Etna altitude cross-section, from Catania to summit craters",
    },
    "`[INFOGRAPHIC: Syracuse Through the Ages — A Timeline]`": {
        "file": "syracuse-timeline.svg",
        "gen":  svg_syracuse_timeline,
        "alt":  "Syracuse historical timeline from 734 BC to present",
    },
    "`[INFOGRAPHIC: Catania Temperature Guide by Month]`": {
        "file": "catania-temperature-by-month.svg",
        "gen":  svg_temperature_by_month,
        "alt":  "Catania average monthly temperatures, March highlighted",
    },
    "`[INFOGRAPHIC: Daily Budget Breakdown]`": {
        "file": "daily-budget.svg",
        "gen":  svg_daily_budget,
        "alt":  "Daily budget ranges for a group of 5 in Catania",
    },
    "`[INFOGRAPHIC: Best Time of Day for Each Attraction]`": {
        "file": "best-time-of-day.svg",
        "gen":  svg_best_time_of_day,
        "alt":  "Best time of day grid for major Catania-area attractions",
    },
    "`[INFOGRAPHIC: Sicily at a Glance]`": {
        "file": "sicily-at-a-glance.svg",
        "gen":  svg_sicily_at_a_glance,
        "alt":  "Sicily key facts: area, population, Etna, coastline, provinces",
    },
    "`[INFOGRAPHIC: The Markets of Catania]`": {
        "file": "catania-markets.svg",
        "gen":  svg_catania_markets,
        "alt":  "La Pescheria and Via Plebiscito markets: hours, what to buy, tips",
    },
    "`[INFOGRAPHIC: Arancino vs Arancina — The Great Debate]`": {
        "file": "arancino-vs-arancina.svg",
        "gen":  svg_arancino_debate,
        "alt":  "Arancino vs Arancina: the Catania/Palermo naming debate explained",
    },
    "`[INFOGRAPHIC: Rainy Day Decision Tree]`": {
        "file": "rainy-day-decision-tree.svg",
        "gen":  svg_rainy_day_decision_tree,
        "alt":  "Rainy day decision tree: what to do based on rain intensity and nap window",
    },
    "`[INFOGRAPHIC: The Cyclopean Coast — What to Do Where]`": {
        "file": "cyclopean-coast.svg",
        "gen":  svg_cyclopean_coast,
        "alt":  "Cyclopean coast route: Catania → Aci Castello → Aci Trezza → Acireale",
    },
    # Map-based: generate placeholder SVGs
    "`[INFOGRAPHIC: Historic Centre Walking Map]`": {
        "file": "historic-centre-walking-map.svg",
        "gen":  lambda: svg_map_placeholder("Historic Centre Walking Map", "Piazza del Duomo → Via Crociferi → Benedictine Monastery"),
        "alt":  "Walking map of Catania historic centre",
    },
    "`[INFOGRAPHIC: ZTL Zone Map for Central Catania]`": {
        "file": "catania-ztl-map.svg",
        "gen":  lambda: svg_map_placeholder("ZTL Zone Map — Central Catania", "Restricted traffic zones: check comune.catania.it for current boundaries"),
        "alt":  "ZTL restricted traffic zone map for central Catania",
    },
    "`[INFOGRAPHIC: Historic Centre Stroller Map]`": {
        "file": "catania-stroller-map.svg",
        "gen":  lambda: svg_map_placeholder("Stroller-Friendly Route Map", "Green: smooth pavements · Amber: cobblestones · Red: steps only"),
        "alt":  "Catania historic centre stroller accessibility map",
    },
    "`[INFOGRAPHIC: Catania Food Map]`": {
        "file": "catania-food-map.svg",
        "gen":  lambda: svg_map_placeholder("Catania Food Map", "Key locations: La Pescheria · Via Plebiscito · Piazza Carlo Alberto"),
        "alt":  "Map of Catania's key food and market locations",
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# Photo registry — Wikimedia Commons searches
# ══════════════════════════════════════════════════════════════════════════════
PHOTOS = {
    "`[PHOTO: Baroque church facade in Catania]`": {
        "file":  "catania-baroque-church.jpg",
        "query": "Catania baroque church lava stone Sicily",
        "alt":   "Baroque church facade in black lava stone, Catania",
    },
    "`[PHOTO: The elephant fountain, two shots]`": {
        "file":  "catania-elephant-fountain.jpg",
        "query": "Fontana dell'elefante Catania Piazza Duomo",
        "alt":   "The elephant fountain at Piazza del Duomo, Catania",
    },
    "`[PHOTO: La Pescheria market stall]`": {
        "file":  "catania-pescheria.jpg",
        "query": "Catania Pescheria fish market stall Sicily",
        "alt":   "La Pescheria fish market, Catania",
    },
    "`[PHOTO: Three shots from Etna]`": {
        "file":  "etna-summit.jpg",
        "query": "Mount Etna summit crater lava flow Sicily",
        "alt":   "Mount Etna: lava fields and summit craters",
    },
    "`[PHOTO: Teatro Greco-Romano, Taormina]`": {
        "file":  "taormina-teatro-greco.jpg",
        "query": "Taormina Greek theatre Teatro Greco Etna sea",
        "alt":   "The Teatro Greco-Romano at Taormina with Etna in the background",
    },
    "`[PHOTO: The Ear of Dionysius]`": {
        "file":  "ear-of-dionysius.jpg",
        "query": "Ear of Dionysius Latomia Syracuse cave",
        "alt":   "The Ear of Dionysius cave, Syracuse",
    },
    "`[PHOTO: Doric columns of the Syracuse Cathedral]`": {
        "file":  "syracuse-cathedral-columns.jpg",
        "query": "Syracuse Cathedral Doric columns Greek temple inside",
        "alt":   "Greek Doric columns embedded in the walls of Syracuse Cathedral",
    },
    "`[PHOTO: Ortigia waterfront at the golden hour]`": {
        "file":  "ortigia-waterfront.jpg",
        "query": "Ortigia island waterfront Syracuse golden hour",
        "alt":   "Ortigia island waterfront, Syracuse, at golden hour",
    },
    "`[PHOTO: The Faraglioni di Aci Trezza]`": {
        "file":  "aci-trezza-faraglioni.jpg",
        "query": "Faraglioni Aci Trezza sea stacks cyclops Sicily",
        "alt":   "The Faraglioni sea stacks at Aci Trezza",
    },
    "`[PHOTO: Castello di Aci Castello]`": {
        "file":  "aci-castello.jpg",
        "query": "Aci Castello Norman castle basalt sea Sicily",
        "alt":   "Aci Castello: the Norman castle on basalt rock over the sea",
    },
    "`[PHOTO: Map or aerial view of Sicily's east coast]`": {
        "file":  "sicily-east-coast.jpg",
        "query": "Sicily east coast aerial Catania Etna satellite",
        "alt":   "Sicily's eastern coast showing Catania and Mount Etna",
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# Wikimedia Commons helpers
# ══════════════════════════════════════════════════════════════════════════════
HEADERS = {"User-Agent": "CataniaTravelGuide/1.0 (github.com/catania-guide)"}

def _api_get(params):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read())

def wikimedia_search(query, limit=6):
    try:
        data = _api_get({"action":"query","list":"search","srsearch":query,
                         "srnamespace":"6","srlimit":limit,"format":"json"})
        return [r["title"] for r in data.get("query",{}).get("search",[])]
    except Exception as e:
        print(f"    search error: {e}")
        return []

def wikimedia_imageinfo(title):
    try:
        data = _api_get({"action":"query","titles":title,"prop":"imageinfo",
                         "iiprop":"url|extmetadata","format":"json"})
        for page in data.get("query",{}).get("pages",{}).values():
            ii = page.get("imageinfo",[{}])[0]
            meta = ii.get("extmetadata",{})
            author = re.sub(r"<[^>]+>","",meta.get("Artist",{}).get("value","Unknown")).strip()
            lic    = meta.get("LicenseShortName",{}).get("value","")
            licurl = meta.get("LicenseUrl",{}).get("value","")
            return ii.get("url",""), author, lic, licurl
    except Exception as e:
        print(f"    imageinfo error: {e}")
    return None, None, None, None

def fetch_photo(info, dry_run=False):
    dest = IMAGES_DIR / info["file"]
    if dest.exists():
        print(f"    already exists: {info['file']}")
        return True, None, None, None

    print(f"    searching: {info['query']}")
    titles = wikimedia_search(info["query"])
    if not titles:
        print(f"    no results.")
        return False, None, None, None

    for title in titles:
        img_url, author, lic, licurl = wikimedia_imageinfo(title)
        if not img_url:
            continue
        ext = img_url.split("?")[0].rsplit(".",1)[-1].lower()
        if ext not in ("jpg","jpeg","png","webp"):
            continue
        print(f"    found: {title[:70]}")
        if dry_run:
            print(f"    [dry-run] would download: {img_url[:80]}")
            return True, author, lic, licurl
        try:
            req = urllib.request.Request(img_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) > 8 * 1024 * 1024:
                print(f"    too large ({len(data)//1024}KB), skipping")
                continue
            dest.write_bytes(data)
            print(f"    saved: {info['file']} ({len(data)//1024}KB)")
            time.sleep(0.6)
            return True, author, lic, licurl
        except Exception as e:
            print(f"    download error: {e}")

    print(f"    could not download any result.")
    return False, None, None, None

# ══════════════════════════════════════════════════════════════════════════════
# Markdown updater
# ══════════════════════════════════════════════════════════════════════════════
def update_markdown(path, dry_run=False):
    text = path.read_text()
    changed = False

    for placeholder, info in INFOGRAPHICS.items():
        if placeholder in text:
            img_ref = f"![{info['alt']}](images/{info['file']})"
            text = text.replace(placeholder, img_ref)
            changed = True
            print(f"    svg:   {info['file']} → {path.name}")

    for placeholder, info in PHOTOS.items():
        if placeholder in text:
            img_ref = f"![{info['alt']}](images/{info['file']})"
            text = text.replace(placeholder, img_ref)
            changed = True
            print(f"    photo: {info['file']} → {path.name}")

    if changed and not dry_run:
        path.write_text(text)
    return changed

# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    dry_run     = "--dry-run"     in sys.argv
    photos_only = "--photos-only" in sys.argv
    svgs_only   = "--svgs-only"   in sys.argv

    if dry_run:
        print("── DRY RUN: no files will be written ──\n")

    IMAGES_DIR.mkdir(exist_ok=True)

    attribution = {}

    # 1. Generate SVGs
    if not photos_only:
        print("Generating SVG infographics...")
        for placeholder, info in INFOGRAPHICS.items():
            dest = IMAGES_DIR / info["file"]
            print(f"  {info['file']}")
            if not dry_run:
                dest.write_text(info["gen"]())
        print()

    # 2. Fetch photos
    if not svgs_only:
        print("Fetching photos from Wikimedia Commons...")
        for placeholder, info in PHOTOS.items():
            print(f"\n  [{info['file']}]")
            ok, author, lic, licurl = fetch_photo(info, dry_run=dry_run)
            if ok and author:
                attribution[info["file"]] = {"author": author, "license": lic, "license_url": licurl}

        if attribution and not dry_run:
            attr_lines = [
                "# Photo Attribution\n\n",
                "Photos sourced from [Wikimedia Commons](https://commons.wikimedia.org).",
                " All images used under their respective licences.\n\n",
                "| File | Author | Licence |\n|---|---|---|\n",
            ]
            for fname, d in attribution.items():
                lic_md = f"[{d['license']}]({d['license_url']})" if d["license_url"] else d["license"]
                attr_lines.append(f"| {fname} | {d['author']} | {lic_md} |\n")
            (IMAGES_DIR / "ATTRIBUTION.md").write_text("".join(attr_lines))
            print(f"\n  Wrote images/ATTRIBUTION.md")
        print()

    # 3. Update markdown
    print("Updating markdown files...")
    for md in sorted(CHAPTERS_DIR.glob("chapter-*.md")):
        update_markdown(md, dry_run=dry_run)
    print()

    if dry_run:
        print("Done (dry run — no changes written).")
    else:
        print("Done. Run `git diff` to review all changes.")


if __name__ == "__main__":
    main()
