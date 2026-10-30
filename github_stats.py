import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import os

# --- CONFIGURAÇÃO ---
USERNAME = "robsonsestrem"
TOKEN = os.getenv("GITHUB_TOKEN", "")
TOP_N = 7

# --- 1. COLETA DE DADOS ---
headers = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner"
repos = requests.get(repos_url, headers=headers).json()

# Filtra apenas repos originais (não-forks) e que não são vazios
repos = [r for r in repos if not r.get("fork") and r.get("size", 0) > 0]

# --- 2. PROCESSAMENTO ---
lang_bytes = defaultdict(int)

for repo in repos:
    lang_url = repo["languages_url"]
    langs = requests.get(lang_url, headers=headers).json()
    for lang, bytes_count in langs.items():
        lang_bytes[lang] += bytes_count

# Converte para DataFrame e ordena
df = pd.DataFrame(list(lang_bytes.items()), columns=['Linguagem', 'Bytes'])
df = df.sort_values(by='Bytes', ascending=False).reset_index(drop=True)

# Pega o Top N e agrupa o resto em "Outras" (Opcional, mas recomendado)
if len(df) > TOP_N:
    top_langs = df.head(TOP_N - 1)
    others_bytes = df.iloc[TOP_N - 1:]['Bytes'].sum()
    others_df = pd.DataFrame([['Outras', others_bytes]], columns=['Linguagem', 'Bytes'])
    df = pd.concat([top_langs, others_df], ignore_index=True)
else:
    df = df.head(TOP_N)

# --- 3. VISUALIZAÇÃO ---
# Configuração de tema escuro
sns.set_theme(style="darkgrid", palette="muted")
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

colors = ['#3572A5', '#f1e05a', '#e34c26', '#563d7c', '#89e051', '#f34b7d', '#666666']

# Plotagem
bars = ax.barh(df['Linguagem'], df['Bytes'], color=colors[:len(df)])
ax.invert_yaxis() # Inverte para a maior ficar no topo

# Formatação dos eixos
ax.set_title(f'Top {TOP_N} Linguagens no GitHub de {USERNAME}', color='white', fontsize=16, pad=15)
ax.set_xlabel('Bytes de Código', color='white')
ax.set_ylabel('')
ax.tick_params(axis='x', colors='white')
ax.tick_params(axis='y', colors='white', labelsize=12)

# Adiciona os valores em KB/MB nas barras
for bar in bars:
    width = bar.get_width()
    mb = width / (1024 * 1024)
    label = f'{mb:.1f} MB' if mb >= 1 else f'{width/1024:.1f} KB'
    ax.text(width + (df['Bytes'].max() * 0.01), bar.get_y() + bar.get_height()/2, 
            label, va='center', color='white', fontsize=10)

plt.tight_layout()

plt.savefig('github_languages.svg', format='svg', bbox_inches='tight', facecolor=fig.get_facecolor())
print("Gráfico gerado com sucesso: github_languages.svg")
