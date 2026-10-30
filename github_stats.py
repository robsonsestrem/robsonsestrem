import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.transforms import blended_transform_factory
from matplotlib.ticker import FuncFormatter
from matplotlib.font_manager import FontProperties, findfont
from collections import defaultdict
import os
import urllib.request
import io
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURAÇÃO ---
USERNAME = "robsonsestrem"
TOKEN = os.getenv("GITHUB_TOKEN", "")
TOP_N = 7

EXCLUDE_LANGUAGES = {"HTML"}  # linguagens fora da análise

ICON_CANDIDATES = {
    "Python": ["python"],
    "JavaScript": ["javascript"],
    "TypeScript": ["typescript"],
    "Java": ["java"],
    "C++": ["cplusplus", "c-plus-plus"],
    "C": ["c"],
    "C#": ["csharp", "c-sharp"],
    "Shell": ["bash", "shell"],
    "Go": ["go"],
    "Rust": ["rust"],
    "PHP": ["php"],
    "Ruby": ["ruby"],
    "Swift": ["swift"],
    "Kotlin": ["kotlin"],
    "Dart": ["dart"],
    "Vue": ["vue"],
    "TSQL": ["microsoft-sql-server", "mssql"],
    "SQL": ["microsoft-sql-server", "mssql"],
    "PLpgSQL": ["postgresql"],
    "PLSQL": ["oracle"],
    "Jupyter Notebook": ["jupyter"],
}
ICON_BASE = "https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{}.png"

# --- DIMENSIONAMENTO DE ÍCONES ---
ICON_DISP_PX = 42
SS = 4
CANVAS_PX = ICON_DISP_PX * SS
PAD_TITLE_BAR = 16
GAP_ICON_TITLE = 18

# --- CLAREAMENTO DE ÍCONES ESCUROS (gamma > 1 clareia preservando o tom) ---
ICON_GAMMA = {
    "Java": 2.0,   # azul-escuro do logo some no fundo dark
    "TSQL": 2.2,   # vinho do SQL Server some no fundo dark
    "SQL": 2.2,
}
AUTO_LUM_THRESHOLD = 0.30  # luminância média < isso => gamma automático 1.8
AUTO_GAMMA = 1.8

FONT_PATH = findfont(FontProperties(family="DejaVu Sans", weight="bold"))

# --- 1. COLETA DE DADOS ---
headers = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner"
repos = requests.get(repos_url, headers=headers).json()
repos = [r for r in repos if not r.get("fork") and r.get("size", 0) > 0]

# --- 2. PROCESSAMENTO ---
lang_bytes = defaultdict(int)
for repo in repos:
    langs = requests.get(repo["languages_url"], headers=headers).json()
    for lang, bytes_count in langs.items():
        if lang not in EXCLUDE_LANGUAGES:
            lang_bytes[lang] += bytes_count

df = pd.DataFrame(list(lang_bytes.items()), columns=['Linguagem', 'Bytes'])
df = df.sort_values(by='Bytes', ascending=False).reset_index(drop=True)

if len(df) > TOP_N:
    top_langs = df.head(TOP_N - 1).copy()
    others_bytes = df.iloc[TOP_N - 1:]['Bytes'].sum()
    others_df = pd.DataFrame([['Outras', others_bytes]], columns=['Linguagem', 'Bytes'])
    df = pd.concat([top_langs, others_df], ignore_index=True)
else:
    df = df.head(TOP_N)

# --- FUNÇÕES DE ÍCONE ---
def fetch_icon(lang):
    for name in ICON_CANDIDATES.get(lang, []):
        url = ICON_BASE.format(name)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            print(f"   [ICON] OK: {lang} -> {name}.png")
            return Image.open(io.BytesIO(data))
        except Exception as e:
            print(f"   [ICON] Falhou {name}.png ({e.__class__.__name__})")
    return None

def normalize_icon(img, canvas=CANVAS_PX):
    """Recorta transparência, mantém proporção e centraliza em canvas quadrado."""
    img = img.convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    w, h = img.size
    usable = int(canvas * 0.88)
    scale = min(usable / w, usable / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    out.paste(img, ((canvas - nw) // 2, (canvas - nh) // 2), img)
    return out

def mean_luminance(img):
    """Luminância percebida média dos pixels visíveis (alpha > 10%)."""
    arr = np.array(img.convert("RGBA")).astype(np.float32) / 255.0
    mask = arr[..., 3] > 0.1
    if not mask.any():
        return 1.0
    lum = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return float(lum[mask].mean())

def brighten(img, gamma):
    """Correção gamma só no RGB (alpha intacto): clareia sem lavar as cores."""
    if gamma == 1.0:
        return img
    arr = np.array(img.convert("RGBA")).astype(np.float32) / 255.0
    arr[..., :3] = np.clip(arr[..., :3] ** (1.0 / gamma), 0.0, 1.0)
    return Image.fromarray((arr * 255).astype(np.uint8), "RGBA")

def make_monogram(initials, rgba, canvas=CANVAS_PX):
    """Fallback com o MESMO tamanho de canvas dos ícones (uniformidade)."""
    r, g, b = [int(c * 255) for c in rgba[:3]]
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = int(canvas * 0.06)
    d.ellipse([m, m, canvas - m, canvas - m], fill=(r, g, b, 255))
    font = ImageFont.truetype(FONT_PATH, int(canvas * 0.42))
    tb = d.textbbox((0, 0), initials, font=font)
    d.text(((canvas - (tb[2] - tb[0])) / 2 - tb[0],
            (canvas - (tb[3] - tb[1])) / 2 - tb[1]),
           initials, font=font, fill=(255, 255, 255, 255))
    return img

# --- 3. VISUALIZAÇÃO ---
fig, ax = plt.subplots(figsize=(10, 6))
fig.dpi = 100
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(df)))
bars = ax.barh(df['Linguagem'], df['Bytes'], color=colors, height=0.6, edgecolor='none')
ax.invert_yaxis()

ax.grid(False)
for spine in ax.spines.values():
    spine.set_visible(False)
ax.set_yticks([])
ax.set_xlim(0, df['Bytes'].max() * 1.18)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v/1e6:.1f} MB' if v else '0'))
ax.tick_params(axis='x', colors='#8b949e', labelsize=10, length=0)
ax.set_title(f'Top {TOP_N} Linguagens no GitHub de @{USERNAME}',
             color='#ffffff', fontsize=16, fontweight='bold', pad=20)

plt.subplots_adjust(left=0.24, right=0.90, top=0.90, bottom=0.08)

fig.canvas.draw()
renderer = fig.canvas.get_renderer()
axw = ax.get_window_extent(renderer).width
prop = FontProperties(size=12)
title_max_px = max(renderer.get_text_width_height_descent(s, prop, False)[0]
                   for s in df['Linguagem'])

trans = blended_transform_factory(ax.transAxes, ax.transData)
title_x = -PAD_TITLE_BAR / axw
icon_right_x = -(PAD_TITLE_BAR + title_max_px + GAP_ICON_TITLE) / axw

icon_report = []
for i, bar in enumerate(bars):
    lang = df['Linguagem'].iloc[i]
    width = bar.get_width()
    y_center = bar.get_y() + bar.get_height() / 2
    mb = width / (1024 * 1024)
    label = f'{mb:.1f} MB' if mb >= 1 else f'{width/1024:.1f} KB'

    ax.text(width + (df['Bytes'].max() * 0.02), y_center, label,
            va='center', color='#8b949e', fontsize=11)

    ax.text(title_x, y_center, lang, transform=trans, ha='right', va='center',
            color='#ffffff', fontsize=12)

    raw = fetch_icon(lang)
    if raw is not None:
        img = normalize_icon(raw)
        lum = mean_luminance(img)
        gamma = ICON_GAMMA.get(lang, 1.0)               
        if gamma == 1.0 and lum < AUTO_LUM_THRESHOLD:
            gamma = AUTO_GAMMA
        img = brighten(img, gamma)
        icon_report.append(f"{lang}: ícone OK (lum={lum:.2f}, gamma={gamma})")
    else:
        initials = ''.join(w[0] for w in lang.split()[:2]).upper()[:2]
        img = make_monogram(initials, colors[i])
        icon_report.append(f"{lang}: monograma (fallback)")

    ab = AnnotationBbox(OffsetImage(img, zoom=1/SS), (icon_right_x, y_center),
                        xycoords=trans, frameon=False, box_alignment=(1.0, 0.5))
    ax.add_artist(ab)

plt.savefig('github_languages.svg', format='svg', bbox_inches='tight',
            facecolor=fig.get_facecolor())

print("\n--- RELATÓRIO DE ÍCONES ---")
for line in icon_report:
    print("  ", line)
print("✅ Gráfico premium gerado com sucesso: github_languages.svg")
