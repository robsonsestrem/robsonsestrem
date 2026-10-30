import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.transforms import blended_transform_factory
from matplotlib.ticker import FuncFormatter
from collections import defaultdict
import os
import urllib.request
import io
from PIL import Image

USERNAME = "robsonsestrem"
TOKEN = os.getenv("GITHUB_TOKEN", "")
TOP_N = 7

# Linguagens que NÃO devem entrar na análise
EXCLUDE_LANGUAGES = {"HTML"}

# Ícones em PNG
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

headers = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner"
repos = requests.get(repos_url, headers=headers).json()
repos = [r for r in repos if not r.get("fork") and r.get("size", 0) > 0]

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

fig, ax = plt.subplots(figsize=(10, 6))
fig.dpi = 100
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(df)))
bars = ax.barh(df['Linguagem'], df['Bytes'], color=colors, height=0.6, edgecolor='none')
ax.invert_yaxis()

# Clean look: sem grade, sem bordas, sem ticks do Y (rótulos serão desenhados à mão)
ax.grid(False)
for spine in ax.spines.values():
    spine.set_visible(False)
ax.set_yticks([])
ax.set_xlim(0, df['Bytes'].max() * 1.18)

# Eixo X formatado em MB
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v/1e6:.1f} MB' if v else '0'))
ax.tick_params(axis='x', colors='#8b949e', labelsize=10, length=0)

ax.set_title(f'Top {TOP_N} Linguagens no GitHub de @{USERNAME}',
             color='#ffffff', fontsize=16, fontweight='bold', pad=20)

# Transformação mista: X em fração dos eixos (coluna de ícones/rótulos), Y em dados
trans = blended_transform_factory(ax.transAxes, ax.transData)

def fetch_icon(lang):
    """Baixa o PNG da linguagem. Retorna None se todas as tentativas falharem."""
    for name in ICON_CANDIDATES.get(lang, []):
        url = ICON_BASE.format(name)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            print(f"   [ICON] OK: {lang} -> {name}.png")
            return img
        except Exception as e:
            print(f"   [ICON] Falhou {name}.png ({e.__class__.__name__})")
    return None

icon_report = []
for i, bar in enumerate(bars):
    lang = df['Linguagem'].iloc[i]
    width = bar.get_width()
    y_center = bar.get_y() + bar.get_height() / 2
    mb = width / (1024 * 1024)
    label = f'{mb:.1f} MB' if mb >= 1 else f'{width/1024:.1f} KB'

    # Valor ao lado da barra
    ax.text(width + (df['Bytes'].max() * 0.02), y_center, label,
            va='center', color='#8b949e', fontsize=11)

    # Nome da linguagem
    ax.text(-0.04, y_center, lang, transform=trans, ha='right', va='center',
            color='#ffffff', fontsize=12)

    img = fetch_icon(lang)
    if img is not None:
        img = img.resize((48, 48), Image.Resampling.LANCZOS)
        ab = AnnotationBbox(OffsetImage(img, zoom=1), (-0.115, y_center),
                            xycoords=trans, frameon=False, box_alignment=(0.5, 0.5))
        ax.add_artist(ab)
        icon_report.append(f"{lang}: ícone OK")
    else:
        initials = ''.join(w[0] for w in lang.split()[:2]).upper()[:2]
        ax.text(-0.115, y_center, initials, transform=trans, ha='center', va='center',
                color='white', fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='circle,pad=0.4', fc=colors[i], ec='none'))
        icon_report.append(f"{lang}: monograma (fallback)")

plt.subplots_adjust(left=0.30, right=0.90, top=0.90, bottom=0.08)
plt.savefig('github_languages.svg', format='svg', bbox_inches='tight',
            facecolor=fig.get_facecolor())

print("\n--- RELATÓRIO DE ÍCONES ---")
for line in icon_report:
    print("  ", line)
print("✅ Gráfico premium gerado com sucesso: github_languages.svg")
