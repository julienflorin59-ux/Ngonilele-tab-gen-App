import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import io
import os

# ==============================================================================
# ⚙️ CONFIGURATION DE LA PAGE
# ==============================================================================
st.set_page_config(page_title="Générateur Tablature Ngonilélé", layout="wide", page_icon="🪕")

st.title("🪕 Générateur de Tablature Ngonilélé")
st.markdown("Créez vos partitions, réglez l'accordage et téléchargez le résultat.")

# ==============================================================================
# 🧠 MOTEUR LOGIQUE
# ==============================================================================

# --- Données par défaut ---
TEXTE_DEFAUT = """
1   4D   I
+   4G   I
+   5D   I
+   5G   I
+   4G   I
=   2D   P
+   3G   P
+   6D   I x2
+   2G   P
=   5G   I
+   PAGE
+   TXT  Partie 2
+   4D   I
"""

POSITIONS_X = {
    '1G': -1, '2G': -2, '3G': -3, '4G': -4, '5G': -5, '6G': -6,
    '1D': 1,  '2D': 2,  '3D': 3,  '4D': 4,  '5D': 5,  '6D': 6
}
COULEURS_CORDES_REF = {
    'C': '#FF0000', 'D': '#FF8C00', 'E': '#FFD700', 'F': '#32CD32',
    'G': '#00BFFF', 'A': '#00008B', 'B': '#9400D3'
}
TRADUCTION_NOTES = {'C':'do', 'D':'ré', 'E':'mi', 'F':'fa', 'G':'sol', 'A':'la', 'B':'si'}
AUTOMATIC_FINGERING = {'1G':'P','2G':'P','3G':'P','1D':'P','2D':'P','3D':'P','4G':'I','5G':'I','6G':'I','4D':'I','5D':'I','6D':'I'}

# --- Chemins ---
CHEMIN_POLICE = 'ML.ttf' 
CHEMIN_ICON_POUCE = 'icon_pouce.png'
CHEMIN_ICON_INDEX = 'icon_index.png'
CHEMIN_IMAGE_FOND = 'texture_ngonilele.png'

def get_font(size, weight='normal', style='normal'):
    if os.path.exists(CHEMIN_POLICE):
        return fm.FontProperties(fname=CHEMIN_POLICE, size=size, weight=weight, style=style)
    return fm.FontProperties(family='sans-serif', size=size, weight=weight, style=style)

def parser_texte(texte):
    data = []
    dernier_temps = 0
    for ligne in texte.strip().split('\n'):
        parts = ligne.strip().split(maxsplit=2)
        if not parts: continue
        try:
            col1 = parts[0]
            if col1 == '+': t = dernier_temps + 1
            elif col1 == '=': t = dernier_temps
            elif col1.isdigit(): t = int(col1)
            else: continue
            if col1 != '=': dernier_temps = t
            corde_valide = parts[1].upper()
            if corde_valide == 'TXT':
                msg = parts[2] if len(parts) > 2 else ""
                data.append({'temps': t, 'corde': 'TEXTE', 'message': msg}); continue
            elif corde_valide == 'PAGE':
                data.append({'temps': t, 'corde': 'PAGE_BREAK'}); continue
            corde_valide = 'SILENCE' if corde_valide=='S' else 'SEPARATOR' if corde_valide=='SEP' else corde_valide
            doigt = None; repetition = 1
            if len(parts) > 2:
                for p in parts[2].split():
                    p_upper = p.upper()
                    if p_upper.startswith('X') and p_upper[1:].isdigit(): repetition = int(p_upper[1:])
                    elif p_upper in ['I', 'P']: doigt = p_upper
            if not doigt and corde_valide in AUTOMATIC_FINGERING: doigt = AUTOMATIC_FINGERING[corde_valide]
            for i in range(repetition):
                current_time = t + i
                note = {'temps': current_time, 'corde': corde_valide}
                if doigt: note['doigt'] = doigt
                data.append(note)
                if i > 0: dernier_temps = current_time
        except: pass
    data.sort(key=lambda x: x['temps'])
    return data

# ==============================================================================
# 🎨 MOTEUR D'AFFICHAGE
# ==============================================================================

def dessiner_contenu_legende(ax, y_pos, styles):
    c_txt = styles['TEXTE']; c_fond = styles['LEGENDE_FOND']; c_bulle = styles['PERLE_FOND']
    prop_annotation = get_font(16, 'bold'); prop_legende = get_font(12, 'bold')
    
    # Cadre
    rect = patches.FancyBboxPatch((-7.5, y_pos - 3.6), 15, 3.3, boxstyle="round,pad=0.1", linewidth=1.5, edgecolor=c_txt, facecolor=c_fond, zorder=0)
    ax.add_patch(rect)
    ax.text(0, y_