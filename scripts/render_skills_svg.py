#!/usr/bin/env python3
"""
Render skills.svg: a terminal-window card listing the tech stack, grouped by
category, in the same visual language as the contribution graph / stats card.

Every chip is something actually used in the repos on github.com/jinayajmera
(see the SOURCE comments), so the card stays honest -- edit SKILLS below to
add / remove things, then:

    python scripts/render_skills_svg.py [output.svg]

Rows slide in one after another (CSS keyframes -- GitHub runs those inside
<img> SVGs, never JS), then hold.
"""
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "skills.svg")
HANDLE = "jinay"

# (command-style label, accent colour, chips)
SKILLS = [
    # SOURCE: repo language mix + Arduino/embedded coursework projects
    ("languages", "#39d353",
     ["Python", "TypeScript", "JavaScript", "SQL", "HTML5", "CSS3", "C", "C++", "Java"]),
    # SOURCE: CouchBeam, VulneraSanenetur/RoboSurge
    ("frontend", "#22d3ee",
     ["React", "Vite", "Tailwind CSS", "Three.js", "React Router"]),
    # SOURCE: CouchBeam (ws, zod), RoboSurge (Express, FastAPI), E.V. (Flask)
    ("backend", "#58a6ff",
     ["Node.js", "Express", "Flask", "FastAPI", "WebSockets", "REST APIs", "Zod", "JWT"]),
    # SOURCE: E.V. (MySQL + procedures/triggers/views), RoboSurge (SQLite)
    ("databases", "#f2cc60",
     ["MySQL", "SQLite", "Stored procedures", "Triggers & views", "ACID transactions"]),
    # SOURCE: RoboSurge vision + planning pipeline; SDN traffic-engineering DRL project
    ("ai & ml", "#d2a8ff",
     ["PyTorch", "Deep RL (PPO / A2C)", "Stable-Baselines3", "Gymnasium", "YOLOv8 pose",
      "OpenCV", "NumPy", "LLM agents (Groq)", "Sensor fusion"]),
    # SOURCE: RoboSurge (ESP32, serial, IK), Arduino smart-parking, Tinkercad
    ("robotics & embedded", "#ff7b72",
     ["ESP32", "Arduino Uno", "PySerial", "Inverse kinematics", "Ultrasonic sensors", "Tinkercad"]),
    # SOURCE: E.V. (bcrypt, CSRF, CSP, lockout), RoboSurge backend (helmet)
    ("security", "#ffa657",
     ["bcrypt", "CSRF + CSP", "Helmet", "Rate limiting", "Input validation"]),
    # SOURCE: CyberCrimeReport (NCRB state/UT analysis, forecasting); SDN project dashboard
    ("data & research", "#79c0ff",
     ["Pandas", "SciPy", "NetworkX", "Matplotlib", "Plotly", "Streamlit",
      "Statistical testing", "Forecasting", "Data validation", "Technical reporting"]),
    # SOURCE: CouchBeam (CI, CodeQL, Dependabot, Docker, devcontainer), SDN (uv, pytest)
    ("devops & tooling", "#7ee787",
     ["Git", "GitHub Actions", "Docker", "Docker Compose", "CodeQL", "Dependabot",
      "Vitest", "pytest", "tsup", "npm workspaces", "uv", "Dev Containers"]),
]

W = 860
PAD = 22
TITLEBAR_H = 30
LABEL_W = 200
CHIP_H = 26
CHIP_GAP_X = 8
CHIP_GAP_Y = 8
CHAR_W = 7.25            # 12px monospace advance, close enough for layout
CHIP_PAD_X = 12
ROW_GAP = 18
ROW_PAD_Y = 16

BG, BG2, FRAME = "#0d1117", "#111722", "#30363d"
MUTED, INK = "#7d8590", "#e6edf3"

chips_x0 = PAD + LABEL_W
chips_w = W - PAD - chips_x0


def layout(chips):
    """flow chips into lines inside chips_w -> list of (text, x, line, width)"""
    out, x, line = [], 0.0, 0
    for c in chips:
        w = len(c) * CHAR_W + CHIP_PAD_X * 2
        if x + w > chips_w and x > 0:
            x, line = 0.0, line + 1
        out.append((c, x, line, w))
        x += w + CHIP_GAP_X
    return out, line + 1


rows, y = [], TITLEBAR_H + ROW_PAD_Y + 10
for label, color, chips in SKILLS:
    placed, n_lines = layout(chips)
    h = n_lines * CHIP_H + (n_lines - 1) * CHIP_GAP_Y
    rows.append((label, color, placed, y, h))
    y += h + ROW_GAP
H = int(y - ROW_GAP + ROW_PAD_Y + 12)

p = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" role="img" '
    'aria-label="Tech stack: ' + html.escape(", ".join(c for _, _, cs in SKILLS for c in cs)) + '">',
    '<style>'
    '.r{opacity:0;animation:in .5s ease-out both}'
    '@keyframes in{0%{opacity:0;transform:translateY(10px)}100%{opacity:1;transform:translateY(0)}}'
    '@media (prefers-reduced-motion: reduce){.r{opacity:1!important;transform:none!important;animation:none!important}}'
    '</style>',
    '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
    f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>',
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
]
for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    p.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dot}"/>')
p.append(f'<text x="{W/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12" '
         f'text-anchor="middle">{HANDLE}@github: ~$ ./skills.sh --list</text>')

for i, (label, color, placed, ry, rh) in enumerate(rows):
    p.append(f'<g class="r" style="animation-delay:{i*0.12:.2f}s">')
    p.append(f'<text x="{PAD}" y="{ry + 17}" font-size="13" fill="{MUTED}">$ '
             f'<tspan fill="{color}" font-weight="700">{html.escape(label)}</tspan></text>')
    for text, cx, line, w in placed:
        x = chips_x0 + cx
        cy = ry + line * (CHIP_H + CHIP_GAP_Y)
        p.append(f'<rect x="{x:.1f}" y="{cy}" width="{w:.1f}" height="{CHIP_H}" rx="6" '
                 f'fill="{color}" fill-opacity="0.10" stroke="{color}" stroke-opacity="0.45"/>')
        p.append(f'<text x="{x + w/2:.1f}" y="{cy + 17}" font-size="12" fill="{INK}" '
                 f'text-anchor="middle">{html.escape(text)}</text>')
    p.append('</g>')

p.append('</svg>')
svg = "".join(p)
with open(OUT, "w") as f:
    f.write(svg)
print(f"wrote {OUT}: {W} x {H}, {len(svg)//1024} KB, "
      f"{sum(len(c) for _, _, c in SKILLS)} skills in {len(SKILLS)} groups")
