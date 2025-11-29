import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import io
import os
import urllib.parse
import numpy as np
import shutil

# ==============================================================================
# ⚙️ CONFIGURATION & CHEMINS
# ==============================================================================
CHEMIN_POLICE = 'ML.ttf' 
CHEMIN_IMAGE_FOND = 'texture_ngonilele.png'
CHEMIN_ICON_POUCE = 'icon_pouce.png'
CHEMIN_ICON_INDEX = 'icon_index.png'
CHEMIN_ICON_POUCE_BLANC = 'icon_pouce_blanc.png'
CHEMIN_ICON_INDEX_BLANC = 'icon_index_blanc.png'
CHEMIN_LOGO_APP = 'ico_ngonilele.png'
DOSSIER_SAMPLES = 'samples'

icon_page = CHEMIN_LOGO_APP if os.path.exists(CHEMIN_LOGO_APP) else "🪕"

# Configuration de la page
st.set_page_config(
    page_title="Générateur Tablature Ngonilélé", 
    layout="wide", 
    page_icon=icon_page,
    initial_sidebar_state="collapsed" # Le menu est fermé au départ
)

# ==============================================================================
# 🎨 CSS HACK : MENU ROUGE (CIBLAGE PRÉCIS)
# ==============================================================================
st.markdown("""
    <style>
    /* 1. Cible UNIQUEMENT le bouton qui ouvre la sidebar (à gauche) */
    [data-testid="stSidebarCollapsedControl"] {
        background-color: #FF4B4B !important;
        border: 2px solid white !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 5px !important;
        margin-top: 5px !important;
        margin-left: 5px !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.5) !important;
        z-index: 100000 !important;
        display: flex !important;
        align-items: center !important;
        width: auto !important; /* Laisse la largeur s'adapter au texte */
    }

    /* 2. Force l'icône de la flèche en blanc */
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: white !important;
        stroke: white !important;
    }

    /* 3. Ajoute le mot MENU à côté de la flèche */
    [data-testid="stSidebarCollapsedControl"]::after {
        content: "MENU";
        font-weight: 900;
        font-size: 14px;
        color: white;
        margin-left: 8px;
        margin-right: 5px;
        padding-top: 2px;
    }

    /* 4. Protection pour Mobile : Assure que le header est visible */
    @media (max-width: 640px) {
        [data-testid="stHeader"] {
            display: block !important;
            visibility: visible !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🚨 MESSAGE D'AIDE
# ==============================================================================
if st.session_state.get('first_run', True):
    st.info("👈 **CLIQUEZ SUR LE BOUTON ROUGE 'MENU' EN HAUT À GAUCHE** pour choisir un morceau ou changer l'accordage !")

# ==============================================================================
# 🎵 BANQUE DE DONNÉES
# ==============================================================================
BANQUE_TABLATURES = {
    "--- Nouveau / Vide ---": """
1   4D
+   4G
""",
    "Manitoumani -M- & Lamomali": """
1   4D
+   4G
+   5D
+   5G
+   4G
=   2D
+   3G
+   6D   x2
+   2G
=   5G
+  3G
+  6D   x2
+  2G
=  5G
+ 3G
+ 6D   x2
+ 2G
= 5G
+   TXT  REPETER 2x
+   PAGE
+   4D
+   4G
+   5D
+   5G
+   4G
=   1D
+   2G
+   6D   x2
+   2G
=   4G
+   1D
+   2G
+   6D   x2
+   2G
=   4G
+ S
+ S
+ PAGE
+   1G
+   3D
+   3G
+   5D
+   1G
+   3D
+   3G
+   5D
+ S
+ S
+ S
+ S
+ S
+ S
+ S
+ 4D
+ PAGE
+   4G
+   5D
+   5G
+   4G
=   2D
+   3G
+   6D   x2
+   2G
=   5G
+  3G
+  6D   x2
+  2G
=  5G
+ 3G
+ 6D   x2
+ 2G
= 5G
"""
}

# En-tête
col_logo, col_titre = st.columns([1, 5])
with col_logo:
    if os.path.exists(CHEMIN_LOGO_APP): st.image(CHEMIN_LOGO_APP, width=100)
    else: st.header("🪕")
with col_titre:
    st.title("Générateur de Tablature Ngonilélé")
    st.markdown("Créez vos partitions, réglez l'accordage et téléchargez le résultat.")

# ==============================================================================
# 🧠 MOTEUR LOGIQUE
# ==============================================================================
# IMPORTS SÉCURISÉS
HAS_MOVIEPY = False
try:
    from moviepy.editor import ImageClip, CompositeVideoClip, AudioFileClip
    HAS_MOVIEPY = True
except: pass

HAS_PYDUB = False
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except: pass

POSITIONS_X = {'1G': -1, '2G': -2, '3G': -3, '4G': -4, '5G': -5, '6G': -6, '1D': 1, '2D': 2, '3D': 3, '4D': 4, '5D': 5, '6D': 6}
COULEURS_CORDES_REF = {'C': '#FF0000', 'D': '#FF8C00', 'E': '#FFD700', 'F': '#32CD32', 'G': '#00BFFF', 'A': '#00008B', 'B': '#9400D3'}
TRADUCTION_NOTES = {'C':'do', 'D':'ré', 'E':'mi', 'F':'fa', 'G':'sol', 'A':'la', 'B':'si'}
AUTOMATIC_FINGERING = {'1G':'P','2G':'P','3G':'P','1D':'P','2D':'P','3D':'P','4G':'I','5G':'I','6G':'I','4D':'I','5D':'I','6D':'I'}

def get_font(size, weight='normal', style='normal'):
    if os.path.exists(CHEMIN_POLICE): return fm.FontProperties(fname=CHEMIN_POLICE, size=size, weight=weight, style=style)
    return fm.FontProperties(family='sans-serif', size=size, weight=weight, style=style)

def parser_texte(texte):
    data = []
    dernier_temps = 0
    if not texte: return []
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
            if not doigt and corde_