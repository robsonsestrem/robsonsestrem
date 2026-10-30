import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from collections import defaultdict
import os
import urllib.request
from PIL import Image
import io

USERNAME = "robsonsestrem"
TOKEN = os.getenv("GITHUB_TOKEN", "")
TOP_N = 7

# Mapeamento de linguagens para ícones (PNG de alta qualidade do Devicon)
ICON_URLS = {
    "Python": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.png",
    "JavaScript": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/javascript/javascript-original.png",
    "TypeScript": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/typescript/typescript-original.png",
    "HTML": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/html5/html5-original.png",
    "CSS": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/css3/css3-original.png",
    "Java": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/java/java-original.png",
    "C++": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/cplusplus/cplusplus-original.png",
    "C": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/c/c-original.png",
    "Shell": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/bash/bash-original.png",
    "Go": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/go/go-original.png",
    "Rust": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/rust/rust-original.png",
    "PHP": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/php/php-original.png",
    "Ruby": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/ruby/ruby-original.png",
    "Swift": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/swift/swift-original.png",
    "Kotlin": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/kotlin/kotlin-original.png",
    "Dart": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/dart/dart-original.png",
    "Vue": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vuejs/vuejs-original.png",
    "Jupyter Notebook": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/jupyter/jupyter-original.png"
}

headers = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner"
repos = requests.get(repos_url, headers=headers).json()

# Filtra apenas repos originais (não-forks) e que não são vazios
repos = [r for r in repos if not r.get("fork") and r.get("size", 0) > 0]

lang_bytes = defaultdict(int)
for repo in repos:
    lang_url = repo["languages_url"]
    langs = requests.get(lang_url, headers=headers).json()
    for lang, bytes_count in langs.items():
        lang_bytes[lang] += bytes_count

df = pd.DataFrame(list(lang_bytes.items()), columns=['Linguagem', 'Bytes'])
df = df.sort_values(by='Bytes', ascending=False).reset_index(drop=True)

# Agrupa o excedente em "Outras" para manter o gráfico limpo
if len(df) > TOP_N:
    top_langs = df.head(TOP_N - 1).copy()
    others_bytes = df.iloc[TOP_N - 1:]['Bytes'].sum()
    others_df = pd.DataFrame([['Outras', others_bytes]], columns=['Linguagem', 'Bytes'])
    df = pd.concat([top_langs, others_df], ignore_index=True)
else:
    df = df.head(TOP_N)

fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

# Gradiente de cores
colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(df)))

# Plotagem das barras
bars = ax.barh(df['Linguagem'], df['Bytes'], color=colors, height=0.6, edgecolor='none')
ax.invert_yaxis()

# Remover grade e bordas desnecessárias (Clean Look)
ax.grid(False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['left'].set_visible(False)

# Configuração de texto e eixos
ax.set_title(f'Top {TOP_N} Linguagens no GitHub de @{USERNAME}', color='#ffffff', fontsize=16, fontweight='bold', pad=20)
ax.tick_params(axis='x', colors='#8b949e', labelsize=10)
ax.tick_params(axis='y', colors='#ffffff', labelsize=12, length=0)

# Adicionar ícones e rótulos de valor
for i, bar in enumerate(bars):
    lang = df['Linguagem'].iloc[i]
    width = bar.get_width()
    mb = width / (1024 * 1024)
    label = f'{mb:.1f} MB' if mb >= 1 else f'{width/1024:.1f} KB'
    
    # Texto do valor ao lado da barra
    ax.text(width + (df['Bytes'].max() * 0.02), bar.get_y() + bar.get_height()/2, 
            label, va='center', color='#8b949e', fontsize=11, fontweight='medium')
    
    # Tentar adicionar o ícone da linguagem
    if lang in ICON_URLS:
        try:
            # Baixar a imagem
            req = urllib.request.Request(ICON_URLS[lang], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as url:
                img_data = url.read()
            
            # Processar com PIL para garantir compatibilidade
            image = Image.open(io.BytesIO(img_data)).convert("RGBA")
            # Redimensionar para caber bem na barra (proporcional à altura)
            zoom_size = int(bar.get_height() * 100) 
            image = image.resize((zoom_size, zoom_size), Image.Resampling.LANCZOS)
            
            # Criar o box da imagem e posicionar à esquerda da barra
            img_box = OffsetImage(image, zoom=1)
            ab = AnnotationBbox(img_box, (width * -0.05, bar.get_y() + bar.get_height()/2), 
                                frameon=False, xycoords='data', box_alignment=(1, 0.5))
            ax.add_artist(ab)
        except Exception:
            pass

plt.subplots_adjust(left=0.25, right=0.85, top=0.9, bottom=0.1)

# Salvar em SVG
plt.savefig('github_languages.svg', format='svg', bbox_inches='tight', facecolor=fig.get_facecolor())
print("✅ Gráfico premium gerado com sucesso: github_languages.svg")
