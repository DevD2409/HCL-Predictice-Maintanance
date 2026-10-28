"""
HCL Predictive Maintenance — AIZCRM-Inspired Dark Dashboard Theme
=================================================================
Reusable CSS tokens, SVG generators, and HTML helper functions
for a premium dark analytics UI (Poppins, emerald accent, charcoal cards).
"""

import math

# ── Colour palette ───────────────────────────────────────────────
BG_APP       = "#1B1D23"
BG_SIDEBAR   = "#1F2127"
BG_CARD      = "#25272E"
BG_CARD_ALT  = "#2A2D35"
BG_INPUT     = "#2E3038"
BORDER       = "#32353E"
BORDER_LIGHT = "#3A3D46"

TEXT_PRIMARY  = "#E8E9ED"
TEXT_HEADING  = "#FFFFFF"
TEXT_MUTED    = "#8A8F9C"
TEXT_SUBTLE   = "#5F6370"

GREEN        = "#1FB589"   # emerald primary / healthy
GREEN_DIM    = "rgba(31,181,137,0.12)"
GREEN_GLOW   = "rgba(31,181,137,0.35)"
AMBER        = "#F5A524"   # warning
AMBER_DIM    = "rgba(245,165,36,0.12)"
AMBER_GLOW   = "rgba(245,165,36,0.35)"
RED          = "#F0553F"   # fault / critical
RED_DIM      = "rgba(240,85,63,0.12)"
RED_GLOW     = "rgba(240,85,63,0.35)"
BLUE         = "#2D6BFF"   # secondary / info
BLUE_DIM     = "rgba(45,107,255,0.12)"
CYAN         = "#38BDF8"   # humidity / environmental
CYAN_DIM     = "rgba(56,189,248,0.12)"
CYAN_GLOW    = "rgba(56,189,248,0.35)"

# ── Semantic helpers ─────────────────────────────────────────────
def cond_color(cond: str) -> str:
    return GREEN if cond == "Healthy" else (AMBER if cond == "Warning" else RED)

def cond_dim(cond: str) -> str:
    return GREEN_DIM if cond == "Healthy" else (AMBER_DIM if cond == "Warning" else RED_DIM)

def cond_glow(cond: str) -> str:
    return GREEN_GLOW if cond == "Healthy" else (AMBER_GLOW if cond == "Warning" else RED_GLOW)

def cond_label(cond: str) -> str:
    return cond.upper()

def risk_color(risk: float) -> str:
    if risk < 30:
        return GREEN
    elif risk < 60:
        return AMBER
    return RED

# ── Global CSS ───────────────────────────────────────────────────
GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

/* ── Hide Streamlit chrome ─────────────────────── */
#MainMenu, header, footer,
div[data-testid="stDecoration"],
div[data-testid="stToolbar"] {{
    display: none !important;
}}

/* ── App canvas ────────────────────────────────── */
html, body, .stApp {{
    background-color: {BG_APP} !important;
    color: {TEXT_PRIMARY};
    font-family: 'Poppins', sans-serif !important;
}}

.stApp {{
    background-color: {BG_APP} !important;
}}

/* ── Main container ────────────────────────────── */
.block-container {{
    padding: 1.0rem 1.6rem 2rem 1.6rem !important;
    max-width: 1480px;
}}

/* ── Sidebar ───────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background-color: {BG_SIDEBAR} !important;
    border-right: 1px solid {BORDER} !important;
    padding-top: 0 !important;
}}
section[data-testid="stSidebar"] > div:first-child {{
    padding-top: 0.6rem !important;
}}
section[data-testid="stSidebar"] hr {{
    border-color: {BORDER} !important;
    margin: 0.8rem 0;
}}

/* ── Sidebar Radio as Rounded Pills ────────────── */
section[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] {{
    gap: 4px;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label {{
    background: transparent !important;
    border-radius: 12px !important;
    padding: 8px 14px !important;
    margin-bottom: 2px !important;
    color: {TEXT_MUTED} !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    border: 1px solid transparent !important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {{
    background: {BG_CARD} !important;
    color: {TEXT_PRIMARY} !important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-checked="true"],
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {{
    background: {GREEN} !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 14px {GREEN_GLOW} !important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child {{
    display: none !important;
}}

/* ── Streamlit element overrides ───────────────── */
div[data-testid="stMetricValue"] {{
    color: {TEXT_HEADING} !important;
    font-weight: 700 !important;
    font-family: 'Poppins', sans-serif !important;
}}
div[data-testid="stMetricLabel"] {{
    color: {TEXT_MUTED} !important;
    font-size: 0.78rem !important;
    font-family: 'Poppins', sans-serif !important;
}}
label, .stSlider label, .stCheckbox label,
.stRadio label, .stTextInput label, .stSelectbox label {{
    color: {TEXT_MUTED} !important;
    font-family: 'Poppins', sans-serif !important;
}}
.stSlider [data-baseweb="slider"] div[role="slider"] {{
    background: {GREEN} !important;
}}

/* ── Selectbox Pill Styling ────────────────────── */
div[data-baseweb="select"] > div {{
    background-color: {BG_INPUT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 20px !important;
    color: {TEXT_PRIMARY} !important;
    font-size: 0.76rem !important;
    min-height: 32px !important;
    font-family: 'Poppins', sans-serif !important;
}}
div[data-baseweb="popover"] ul {{
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 14px !important;
}}
div[data-baseweb="popover"] li {{
    color: {TEXT_PRIMARY} !important;
    font-size: 0.78rem !important;
    font-family: 'Poppins', sans-serif !important;
}}

/* ── Buttons ───────────────────────────────────── */
div.stButton > button {{
    background: {BG_CARD} !important;
    color: {TEXT_PRIMARY} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    padding: 7px 16px !important;
    transition: all 0.2s ease !important;
}}
div.stButton > button:hover {{
    background: {BG_CARD_ALT} !important;
    border-color: {GREEN} !important;
    box-shadow: 0 0 12px {GREEN_GLOW} !important;
    transform: translateY(-1px);
}}

/* Small pill button modifier */
.pill-btn div.stButton > button {{
    border-radius: 20px !important;
    padding: 3px 12px !important;
    font-size: 0.72rem !important;
    border-color: {BORDER_LIGHT} !important;
}}

/* ── Inputs ────────────────────────────────────── */
div[data-baseweb="input"] {{
    background-color: {BG_INPUT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
}}
div[data-baseweb="input"]:focus-within {{
    border-color: {GREEN} !important;
}}

/* ── Scrollbar ─────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: {BG_APP}; }}
::-webkit-scrollbar-thumb {{ background: {BORDER_LIGHT}; border-radius: 3px; }}

/* ── Dark Card Utility Class ───────────────────── */
.aiz-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 22px;
    padding: 20px 22px;
    margin-bottom: 14px;
    transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}}
.aiz-card:hover {{
    transform: translateY(-2px);
    border-color: {BORDER_LIGHT};
    box-shadow: 0 10px 24px rgba(0,0,0,0.35);
}}
.aiz-card-glow-red {{
    border-color: {RED} !important;
    box-shadow: 0 0 18px {RED_GLOW} !important;
    animation: pulse-red 2.5s infinite;
}}
.aiz-card-glow-amber {{
    border-color: {AMBER} !important;
    box-shadow: 0 0 18px {AMBER_GLOW} !important;
    animation: pulse-amber 2.5s infinite;
}}

/* ── Animation keyframes ───────────────────────── */
@keyframes pulse-green {{
    0%   {{ box-shadow: 0 0 0 0 {GREEN_GLOW}; }}
    70%  {{ box-shadow: 0 0 0 6px rgba(31,181,137,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(31,181,137,0); }}
}}
@keyframes pulse-red {{
    0%   {{ box-shadow: 0 0 0 0 {RED_GLOW}; }}
    70%  {{ box-shadow: 0 0 0 8px rgba(240,85,63,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(240,85,63,0); }}
}}
@keyframes pulse-amber {{
    0%   {{ box-shadow: 0 0 0 0 {AMBER_GLOW}; }}
    70%  {{ box-shadow: 0 0 0 8px rgba(245,165,36,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(245,165,36,0); }}
}}
@keyframes gauge-fill {{
    from {{ stroke-dashoffset: 282.74; }}
}}
@keyframes ring-fill {{
    from {{ stroke-dashoffset: 251.33; }}
}}
</style>
"""


# ── HTML card wrapper ────────────────────────────────────────────
def card(content: str, *, pad: str = "20px 22px", extra_style: str = "") -> str:
    """Wrap HTML content in a styled dark card with hover lift."""
    return (
        f'<div style="background:{BG_CARD}; border:1px solid {BORDER};'
        f' border-radius:20px; padding:{pad}; margin-bottom:14px;'
        f' transition: transform 0.2s ease, border-color 0.2s ease;'
        f' {extra_style}"'
        f' onmouseover="this.style.transform=\'translateY(-2px)\';'
        f' this.style.borderColor=\'{BORDER_LIGHT}\';"'
        f' onmouseout="this.style.transform=\'translateY(0)\';'
        f' this.style.borderColor=\'{BORDER}\';"'
        f'>{content}</div>'
    )

def pill(label: str, color: str = GREEN, *, bg: str = "", font_size: str = "0.72rem") -> str:
    """Rounded pill / badge."""
    _bg = bg or f"rgba({_hex_to_rgb(color)},0.12)"
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'padding:3px 10px;border-radius:20px;font-size:{font_size};'
        f'font-weight:600;color:{color};background:{_bg};'
        f'border:1px solid rgba({_hex_to_rgb(color)},0.25);'
        f'font-family:Poppins,sans-serif;">{label}</span>'
    )

def section_title(title: str, subtitle: str = "") -> str:
    sub_html = f'<div style="font-size:0.78rem;color:{TEXT_MUTED};margin-top:2px;">{subtitle}</div>' if subtitle else ""
    return (
        f'<div style="margin-bottom:14px;">'
        f'<div style="font-size:1.05rem;font-weight:600;color:{TEXT_HEADING};'
        f'font-family:Poppins,sans-serif;">{title}</div>{sub_html}</div>'
    )

# ── SVG: Health ring gauge ───────────────────────────────────────
def svg_health_ring(score: float, color: str, size: int = 110) -> str:
    """Semi-transparent circular gauge ring with center score."""
    r = 45
    circumference = 2 * 3.14159 * r
    offset = circumference * (1 - score / 100.0)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<circle cx="{size//2}" cy="{size//2}" r="{r}" fill="none"'
        f' stroke="{BORDER}" stroke-width="8"/>'
        f'<circle cx="{size//2}" cy="{size//2}" r="{r}" fill="none"'
        f' stroke="{color}" stroke-width="8" stroke-linecap="round"'
        f' stroke-dasharray="{circumference:.2f}"'
        f' stroke-dashoffset="{offset:.2f}"'
        f' transform="rotate(-90 {size//2} {size//2})"'
        f' style="animation: gauge-fill 1.2s ease-out;"/>'
        f'<text x="{size//2}" y="{size//2+2}" text-anchor="middle"'
        f' dominant-baseline="middle" fill="{TEXT_HEADING}"'
        f' font-size="1.4rem" font-weight="700"'
        f' font-family="Poppins,sans-serif">{score:.0f}%</text>'
        f'</svg>'
    )

# ── SVG: Concentric sensor rings ─────────────────────────────────
def svg_sensor_rings(values: list[tuple[str, float, float, str]], size: int = 140,
                     center_text: str = "OK", center_color: str = GREEN) -> str:
    """Concentric donut rings for sensor load fractions with center status badge."""
    cx, cy = size // 2, size // 2
    rings = ""
    radii = [56, 47, 38, 29, 20] if len(values) >= 5 else [52, 42, 32, 22]
    stroke_w = "4" if len(values) >= 5 else "5"
    for i, (label, val, mx, color) in enumerate(values[:len(radii)]):
        r = radii[i]
        circ = 2 * math.pi * r
        try:
            val_f = float(val) if val is not None and not (isinstance(val, float) and math.isnan(val)) else 0.0
        except (ValueError, TypeError):
            val_f = 0.0
        frac = min(1.0, max(0.0, val_f / mx)) if mx > 0 else 0
        offset = circ * (1 - frac)
        rings += (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none"'
            f' stroke="{BORDER}" stroke-width="{stroke_w}" opacity="0.45"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none"'
            f' stroke="{color}" stroke-width="{stroke_w}" stroke-linecap="round"'
            f' stroke-dasharray="{circ:.2f}"'
            f' stroke-dashoffset="{offset:.2f}"'
            f' transform="rotate(-90 {cx} {cy})"'
            f' style="animation: ring-fill 1s ease-out;"/>'
        )
    center_r = 13 if len(values) >= 5 else 15
    center_elem = (
        f'<circle cx="{cx}" cy="{cy}" r="{center_r}" fill="{BG_CARD_ALT}"/>'
        f'<text x="{cx}" y="{cy + 3}" text-anchor="middle" fill="{center_color}"'
        f' font-size="8" font-weight="700" font-family="Poppins">{center_text}</text>'
    )
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{rings}{center_elem}</svg>'


# ── SVG: Anomaly progress bar ────────────────────────────────────
def svg_anomaly_bar(score: float, width: int = 320, height: int = 24) -> str:
    """Horizontal segmented anomaly progress bar with zone markers."""
    bar_w = width - 20
    fill = max(2, bar_w * score / 100.0)

    # Zone boundaries
    z1 = bar_w * 30 / 100  # Healthy zone end
    z2 = bar_w * 65 / 100  # Warning zone end

    if score < 30:
        bar_col = GREEN
    elif score < 65:
        bar_col = AMBER
    else:
        bar_col = RED

    return (
        f'<svg width="{width}" height="{height + 22}" viewBox="0 0 {width} {height + 22}">'
        # Background track
        f'<rect x="10" y="4" width="{bar_w}" height="{height}" rx="{height//2}" fill="{BG_INPUT}"/>'
        # Zone separators
        f'<line x1="{10+z1}" y1="4" x2="{10+z1}" y2="{4+height}" stroke="{BORDER_LIGHT}" stroke-width="1" stroke-dasharray="3,2"/>'
        f'<line x1="{10+z2}" y1="4" x2="{10+z2}" y2="{4+height}" stroke="{BORDER_LIGHT}" stroke-width="1" stroke-dasharray="3,2"/>'
        # Fill
        f'<rect x="10" y="4" width="{fill}" height="{height}" rx="{height//2}" fill="{bar_col}"/>'
        # Labels
        f'<text x="{10+z1/2}" y="{height+18}" text-anchor="middle" fill="{TEXT_SUBTLE}" font-size="9" font-family="Poppins">Healthy</text>'
        f'<text x="{10+(z1+z2)/2}" y="{height+18}" text-anchor="middle" fill="{TEXT_SUBTLE}" font-size="9" font-family="Poppins">Warning</text>'
        f'<text x="{10+(z2+bar_w)/2}" y="{height+18}" text-anchor="middle" fill="{TEXT_SUBTLE}" font-size="9" font-family="Poppins">Fault</text>'
        f'</svg>'
    )

# ── SVG: Semi-circle gauge with tick marks ───────────────────────
def svg_semicircle_gauge(value: float, color: str, label: str = "", size: int = 180) -> str:
    """Segmented/tick-mark semi-circle gauge (like Retention rate in AIZCRM)."""
    cx, cy = size // 2, size // 2 + 8
    r = 58
    half_circ = math.pi * r
    val_clamped = max(0, min(100, value))
    offset = half_circ * (1 - val_clamped / 100.0)

    # Generate radial tick marks around the outer perimeter (180° to 360°)
    ticks = ""
    for deg in range(180, 361, 10):
        rad = math.radians(deg)
        t1 = r + 8
        t2 = r + 14
        x1 = cx + t1 * math.cos(rad)
        y1 = cy + t1 * math.sin(rad)
        x2 = cx + t2 * math.cos(rad)
        y2 = cy + t2 * math.sin(rad)
        is_active = (deg - 180) / 180.0 <= (val_clamped / 100.0)
        t_col = color if is_active else BORDER
        t_w = "2" if is_active else "1"
        ticks += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t_col}" stroke-width="{t_w}" stroke-linecap="round"/>'

    return (
        f'<svg width="{size}" height="{size//2 + 32}" viewBox="0 0 {size} {size//2 + 32}">'
        f'{ticks}'
        # Background arc
        f'<path d="M {cx-r} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" '
        f'fill="none" stroke="{BORDER}" stroke-width="8" stroke-linecap="round"/>'
        # Filled arc
        f'<path d="M {cx-r} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" '
        f'fill="none" stroke="{color}" stroke-width="8" stroke-linecap="round"'
        f' stroke-dasharray="{half_circ:.2f}" stroke-dashoffset="{offset:.2f}"'
        f' style="animation: gauge-fill 1s ease-out;"/>'
        # Center number
        f'<text x="{cx}" y="{cy - 12}" text-anchor="middle" fill="{TEXT_HEADING}"'
        f' font-size="1.7rem" font-weight="700" font-family="Poppins">{val_clamped:.0f}%</text>'
        # Label
        f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" fill="{TEXT_MUTED}"'
        f' font-size="0.68rem" font-family="Poppins">{label}</text>'
        f'</svg>'
    )

# ── Gantt bar helper ─────────────────────────────────────────────
def gantt_bar(label: str, pct: float, color: str, width: int = 260) -> str:
    """Single horizontal Gantt bar row with hatched remainder."""
    pct_clamped = max(0.0, min(100.0, pct))
    return (
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
        f'<span style="font-size:0.75rem;color:{TEXT_MUTED};width:115px;'
        f'text-align:right;font-family:Poppins,sans-serif;flex-shrink:0;">{label}</span>'
        f'<div style="flex:1;display:flex;height:12px;border-radius:6px;overflow:hidden;'
        f'background:repeating-linear-gradient(45deg, {BG_INPUT}, {BG_INPUT} 4px, {BG_CARD} 4px, {BG_CARD} 8px);'
        f'border:1px solid {BORDER};">'
        f'<div style="width:{pct_clamped}%;background:{color};border-radius:6px;'
        f'transition:width 0.6s ease;box-shadow:0 0 8px rgba({_hex_to_rgb(color)},0.4);"></div>'
        f'</div>'
        f'<span style="font-size:0.72rem;color:{TEXT_PRIMARY};width:36px;'
        f'font-family:Poppins,sans-serif;font-weight:600;text-align:right;">{pct_clamped:.0f}%</span>'
        f'</div>'
    )


# ── Plotly dark template ─────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Poppins, sans-serif", color=TEXT_MUTED, size=11),
    margin=dict(l=40, r=16, t=32, b=32),
    xaxis=dict(
        showgrid=True, gridcolor=BORDER, gridwidth=1, zeroline=False,
        tickfont=dict(size=10, color=TEXT_SUBTLE),
    ),
    yaxis=dict(
        showgrid=True, gridcolor=BORDER, gridwidth=1, zeroline=False,
        tickfont=dict(size=10, color=TEXT_SUBTLE),
    ),
    legend=dict(
        font=dict(size=10, color=TEXT_MUTED),
        bgcolor="rgba(0,0,0,0)",
    ),
    hoverlabel=dict(
        bgcolor=BG_CARD, bordercolor=BORDER,
        font=dict(family="Poppins", color=TEXT_PRIMARY, size=12),
    ),
)

# ── private helpers ──────────────────────────────────────────────
def _hex_to_rgb(hex_color: str) -> str:
    """Convert '#RRGGBB' to 'R,G,B'."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"
