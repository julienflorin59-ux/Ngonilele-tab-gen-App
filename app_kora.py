import streamlit as st
import os
import io
import re
import gc
import json
import glob
import random
import base64
import urllib.parse
import tempfile
import numpy as np

# --- OPTIMISATION VITESSE 1 : BACKEND NON-INTERACTIF ---
import matplotlib
matplotlib.use('Agg') 

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
from matplotlib.figure import Figure
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from fpdf import FPDF

# ==============================================================================
# ⚙️ CONFIGURATION & CHEMINS
# ==============================================================================
st.set_page_config(
    page_title="Générateur Tablature Ngonilélé",
    layout="wide",
    page_icon="ico_ngonilele.png",
    initial_sidebar_state="collapsed" # Sidebar fermée par défaut sur mobile pour gagner de la place
)

# ==============================================================================
# 📱 OPTIMISATION CSS : MODE HYBRIDE (PC / MOBILE)
# ==============================================================================
@st.cache_resource
def load_css_styles():
    return """
<style>
    /* ============================================================
       1. CONTENEUR PRINCIPAL ADAPTATIF
    ============================================================ */
    .stApp {
        overflow-x: hidden !important; 
    }
    
    div[data-testid="block-container"] {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-top: 2rem !important;
        max-width: 100% !important;
    }

    /* ============================================================
       2. GESTION INTELLIGENTE DES COLONNES (MOBILE)
    ============================================================ */
    
    @media (max-width: 640px) {
    
        /* PAR DÉFAUT : On empile les colonnes verticalement (Stack) 
           Cela permet à l'Aperçu de passer EN DESSOUS des Éditeurs */
        div[data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 1rem !important;
        }

        /* EXCEPTION : Si le bloc contient 3 colonnes ou plus (ex: Les boutons de cordes, le séquenceur),
           alors on FORCE l'affichage en ligne (Row) pour garder G et D côte à côte */
        div[data-testid="stHorizontalBlock"]:has(div[data-testid="column"]:nth-child(3)) {
            flex-direction: row !important; /* Ligne forcée */
            flex-wrap: nowrap !important;   /* Pas de retour à la ligne */
            overflow-x: auto !important;    /* Scroll si ça dépasse */
            gap: 0.2rem !important;
        }

        /* Ajustement de la largeur des colonnes UNIQUEMENT quand elles sont en ligne */
        div[data-testid="stHorizontalBlock"]:has(div[data-testid="column"]:nth-child(3)) div[data-testid="column"] {
            min-width: 0 !important;        
            flex: 1 1 0 !important;         
            width: auto !important;
        }
    }

    /* ============================================================
       3. BOUTONS COMPACTS (TAILLE RÉDUITE)
    ============================================================ */
    .stButton button {
        width: 100% !important;
        padding: 0.2rem 0.1rem !important; 
        font-size: 0.85rem !important;     
        min-height: 0px !important;        
        height: auto !important;
        line-height: 1.2 !important;
        white-space: nowrap !important;    
    }
    
    div[data-testid="column"] button p {
        font-weight: bold;
    }

    /* ============================================================
       4. ESTHÉTIQUE GÉNÉRALE
    ============================================================ */
    button[data-testid="stTab"] { 
        padding: 5px 10px !important;
        font-size: 0.8rem !important;
    }

    button[data-testid="stTab"] { 
        border: 1px solid #A67C52; border-radius: 5px; margin-right: 2px; 
        background-color: #e5c4a3; color: black; opacity: 0.9; 
    }
    button[data-testid="stTab"][aria-selected="true"] { 
        background-color: #d4b08c; border: 2px solid #A67C52; font-weight: bold; opacity: 1; 
    }
    .stDownloadButton button { background-color: #e5c4a3 !important; color: black !important; border: none !important; }
    [data-testid='stFileDropzone'] { background-color: #e5c4a3 !important; color: black !important; border: none !important; padding: 1rem; }
    [data-testid='stFileDropzone']::after { content: "📂 Charger projet"; color: black; font-weight: bold; display: block; text-align: center; font-size: 0.8rem; }

    div[data-testid="stTooltipContent"] {
        background-color: #333 !important;
        color: white !important;
        font-size: 0.8rem !important;
    }

</style>
"""

st.markdown(load_css_styles(), unsafe_allow_html=True)

# --- CONSTANTES & RESOURCES ---
CHEMIN_POLICE = 'ML.ttf'
CHEMIN_IMAGE_FOND = 'texture_ngonilele.png'
CHEMIN_ICON_POUCE = 'icon_pouce.png'
CHEMIN_ICON_INDEX = 'icon_index.png'
CHEMIN_ICON_POUCE_BLANC = 'icon_pouce_blanc.png'
CHEMIN_ICON_INDEX_BLANC = 'icon_index_blanc.png'
CHEMIN_LOGO_APP = 'ico_ngonilele.png'
CHEMIN_HEADER_IMG = 'texture_ngonilele_2.png'
DOSSIER_SAMPLES = 'samples'

# --- NOUVELLES CONSTANTES RYTHMIQUES (BASE 12) ---
TICKS_NOIRE = 12        # 1 temps
TICKS_CROCHE = 6        # 1/2 temps
TICKS_TRIOLET = 4       # 1/3 temps
TICKS_DOUBLE = 3        # 1/4 temps

SYMBOLES_DUREE = {
    '+': TICKS_NOIRE,
    '♪': TICKS_CROCHE,   # Croche (1 note)
    '🎶': TICKS_TRIOLET, # Triolet (3 notes)
    '♬': TICKS_DOUBLE    # Double (2 notes)
}

# --- COULEURS & CONSTANTES LOGIQUES ---
POSITIONS_X = {'1G': -1, '2G': -2, '3G': -3, '4G': -4, '5G': -5, '6G': -6, '1D': 1, '2D': 2, '3D': 3, '4D': 4, '5D': 5, '6D': 6}
COULEURS_CORDES_REF = {'C': '#FF0000', 'D': '#FF8C00', 'E': '#FFD700', 'F': '#32CD32', 'G': '#00BFFF', 'A': '#00008B', 'B': '#9400D3'}
COLORS_VISU = {'6G':'#00BFFF','5G':'#FF4B4B','4G':'#00008B','3G':'#FFD700','2G':'#FF4B4B','1G':'#00BFFF','1D':'#32CD32','2D':'#00008B','3D':'#FFA500','4D':'#00BFFF','5D':'#9400D3','6D':'#FFD700'}
TRADUCTION_NOTES = {'C':'do', 'D':'ré', 'E':'mi', 'F':'fa', 'G':'sol', 'A':'la', 'B':'si'}
AUTOMATIC_FINGERING = {'1G':'P','2G':'P','3G':'P','1D':'P','2D':'P','3D':'P','4G':'I','5G':'I','6G':'I','4D':'I','5D':'I','6D':'I'}

NOTES_GAMME = [
    'C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'F', 'F#', 'Gb', 'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B',
    'C3', 'D3', 'D#3', 'E3', 'F3', 'G3', 'G#3', 'A3', 'A#3', 'B3',
    'C4', 'D4', 'D#4', 'E4', 'F4', 'G4', 'G#4', 'A4', 'A#4', 'B4',
    'C5', 'D5', 'D#5', 'E5', 'F5', 'G5', 'A5', 'B5'
]

GAMMES_PRESETS = {
    "1. Pentatonique Fondamentale": "E3G3A3C4D4E4G4A4C5D5E5G5",
    "2. Pentatonique (Descente Basse)": "F3G3A3C4D4E4G4A4C5D5E5G5",
    "3. Manitoumani (Standard)": "F3G3A3C4D4E4G4A4B4C5E5G5",
    "4. Orientale Sahara": "F3A3B3D4E4F4G#4A4B4C5E5F5",
    "5. Fa Blues Augmenté Nyama": "F3G#3A#3C4D#4F4G4G#4A#4C5D#5F5",
    "6. Fa Ionien": "F3A3A#3C4D4E4F4G4A4C5D5F5",
    "7. Une Âme": "F3G3G#3C4D4D#4F4G#4A#4C5D#5F5",
    "8. Impressionniste": "E3F3A3B3C4E4G4A4B4C5E5G5"
}
ORDRE_MAPPING_GAMME = ['1D', '1G', '2D', '2G', '3D', '3G', '4D', '4G', '5D', '5G', '6D', '6G']

BASE_TUNING_HARDWARE = {
    '1D': 'E3', '1G': 'G3', '2D': 'A3', '2G': 'C4', '3D': 'D4', '3G': 'E4',
    '4D': 'G4', '4G': 'A4', '5D': 'C5', '5G': 'D5', '6D': 'E5', '6G': 'G5'
}
DEF_ACC = BASE_TUNING_HARDWARE.copy()
ASSOCIATIONS_MORCEAUX_GAMMES = {"Manitoumani -M- & Lamomali": "3. Manitoumani (Standard)"}

BANQUE_TABLATURES = {
    "--- Nouveau / Vide ---": "",
    "Exercice Débutant 1 : Montée et descente de Gamme": "1   1D\n+   S\n+   1G\n+   S\n+   2D\n+   S\n+   2G\n+   S\n+   3D\n+   S\n+   3G\n+   S\n+   4D\n+   S\n+   4G\n+   S\n+   5D\n+   S\n+   5G\n+   S\n+   6D\n+   S\n+   6G\n+   S\n+   TXT  DESCENTE\n+   6G\n+   S\n+   6D\n+   S\n+   5G\n+   S\n+   5D\n+   S\n+   4G\n+   S\n+   4D\n+   S\n+   3G\n+   S\n+   3D\n+   S\n+   2G\n+   S\n+   2D\n+   S\n+   1G\n+   S\n+   1D",
    "Exercice Débutant 2 : Montée et descente de Gamme en triolets": "1   1D\n+   1G\n+   2D\n+   S\n+   1G\n+   2D\n+   2G\n+   S\n+   2D\n+   2G\n+   3D\n+   S\n+   2G\n+   3D\n+   3G\n+   S\n+   3D\n+   3G\n+   4D\n+   S\n+   3G\n+   4D\n+   4G\n+   S\n+   4D\n+   4G\n+   5D\n+   S\n+   4G\n+   5D\n+   5G\n+   S\n+   5D\n+   5G\n+   6D\n+   S\n+   5G\n+   6D\n+   6G\n+   S\n+   TXT  DESCENTE\n+   6G\n+   6D\n+   5G\n+   S\n+   6D\n+   5G\n+   5D\n+   S\n+   5G\n+   5D\n+   4G\n+   S\n+   5D\n+   4G\n+   4D\n+   S\n+   4G\n+   4D\n+   3G\n+   S\n+   4D\n+   3G\n+   3D\n+   S\n+   3G\n+   3D\n+   2G\n+   S\n+   3D\n+   2G\n+   2D\n+   S\n+   2G\n+   2D\n+   1G\n+   S\n+   2D\n+   1G\n+   1D",
    "Manitoumani -M- & Lamomali": "1   4D\n+   4G\n+   5D\n+   5G\n+   4G\n=   2D\n+   3G\n+   6D   x2\n+   2G\n=   5G\n+  3G\n+  6D   x2\n+  2G\n=  5G\n+ 3G\n+ 6D   x2\n+ 2G\n= 5G\n+   TXT  REPETER 2x\n+   PAGE\n+   4D\n+   4G\n+   5D\n+   5G\n+   4G\n=   1D\n+   2G\n+   6D   x2\n+   2G\n=   4G\n+   1D\n+   2G\n+   6D   x2\n+   2G\n=   4G\n+ S\n+ S\n+ PAGE\n+   1G\n+   3D\n+   3G\n+   5D\n+   1G\n+   3D\n+   3G\n+   5D\n+ S\n+ S\n+ S\n+ S\n+ S\n+ S\n+ S\n+ 4D\n+ PAGE\n+   4G\n+   5D\n+   5G\n+   4G\n=   2D\n+   3G\n+   6D   x2\n+   2G\n=   5G\n+  3G\n+  6D   x2\n+  2G\n=  5G\n+ 3G\n+ 6D   x2\n+ 2G\n= 5G",
    "Exercice 3 : Les Tierces": "1   1G\n+   3G\n+   2G\n+   4G\n+   3G\n+   5G\n+   4G\n+   6G\n+   S\n+   TXT  COTE DROIT\n+   1D\n+   3D\n+   2D\n+   4D\n+   3D\n+   5D\n+   4D\n+   6D\n+   S\n+   TXT  FINAL\n+   6G\n=   6D",
    "Démonstration Rythmes": "1   6G\n+   TXT  NOIRES (+)\n+   6D\n+   5G\n+   5D\n+   S\n+   TXT  CROCHES (♪)\n♪   4G\n♪   4D\n♪   3G\n♪   3D\n+   S\n+   TXT  TRIOLETS (🎶)\n🎶   2G\n🎶   2D\n🎶   1G\n🎶   1D\n🎶   2G\n🎶   2D\n+   S\n+   TXT  DOUBLES (♬)\n♬ 6G\n♬ 6D\n♬ 5G\n♬ 5D\n♬ 4G\n♬ 4D\n♬ 3G\n♬ 3D"
}

# ==============================================================================
# 🚀 FONCTIONS UTILES
# ==============================================================================
@st.cache_resource
def load_font_properties():
    if os.path.exists(CHEMIN_POLICE):
        return fm.FontProperties(fname=CHEMIN_POLICE)
    return fm.FontProperties(family='sans-serif')

@st.cache_resource
def load_image_asset(path):
    if os.path.exists(path):
        return mpimg.imread(path)
    return None

def afficher_header_style(titre):
    st.markdown(f"""
    <div style="background-color: #d4b08c; padding: 5px 10px; border-radius: 5px; border-left: 5px solid #A67C52; color: black; margin-bottom: 10px;">
        <strong>{titre}</strong>
    </div>
    """, unsafe_allow_html=True)

def parse_gamme_string(gamme_str):
    return re.findall(r"[A-G][#b]?[0-9]*", gamme_str)

def get_color_for_note(note):
    base_note = note[0].upper() 
    return COULEURS_CORDES_REF.get(base_note, '#000000')

def get_note_value(note_str):
    semitones = {'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3, 'E': 4, 'F': 5, 'F#': 6, 'GB': 6, 'G': 7, 'G#': 8, 'AB': 8, 'A': 9, 'A#': 10, 'BB': 10, 'B': 11}
    match = re.match(r"^([A-G][#b]?)([0-9]+)$", note_str.upper())
    if not match: return -1
    note_name = match.group(1)
    octave = int(match.group(2))
    return semitones.get(note_name, 0) + (octave * 12)

def get_valid_notes_for_string(string_key):
    base_note = BASE_TUNING_HARDWARE.get(string_key)
    if not base_note: return NOTES_GAMME
    base_val = get_note_value(base_note)
    if base_val == -1: return NOTES_GAMME
    max_val = base_val + 2 
    min_val = base_val - 3
    valid_list = []
    for n in NOTES_GAMME:
        val = get_note_value(n)
        if val != -1 and min_val <= val <= max_val:
            valid_list.append(n)
    return valid_list if valid_list else [base_note]

# ==============================================================================
# 📦 GESTION DE LA PERSISTANCE (Initialisation groupée)
# ==============================================================================
if 'init_done' not in st.session_state:
    st.session_state.partition_buffers = []
    st.session_state.partition_generated = False
    st.session_state.video_path = None
    st.session_state.audio_buffer = None
    st.session_state.metronome_buffer = None
    st.session_state.code_actuel = ""
    st.session_state.pdf_buffer = None
    st.session_state.seq_grid = {}
    st.session_state.stored_blocks = {}
    for k, v in DEF_ACC.items():
        if f"acc_{k}" not in st.session_state:
            st.session_state[f"acc_{k}"] = v
    st.session_state.init_done = True

# --- EN-TETE ---
col_logo, col_titre = st.columns([1, 5])
with col_logo:
    if os.path.exists(CHEMIN_HEADER_IMG): st.image(CHEMIN_HEADER_IMG, width=100)
    elif os.path.exists(CHEMIN_LOGO_APP): st.image(CHEMIN_LOGO_APP, width=100)
    else: st.header("🪕")
with col_titre:
    st.title("Générateur Tablature Ngonilélé")
    base_text = "Composez, Écoutez et Exportez."
    pdf_path = "Livret_Ngonilélé.pdf"
    link_html = ""
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            b64_pdf = base64.b64encode(f.read()).decode('utf-8')
        link_html = f'&nbsp;&nbsp;|&nbsp;&nbsp;<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_path}" style="color:#A67C52; text-decoration:none; font-weight:bold;">📥 Télécharger le livret PDF Ngonilélé</a>'
    st.markdown(f"{base_text}{link_html}", unsafe_allow_html=True)

# ==============================================================================
# 🧠 MOTEUR LOGIQUE
# ==============================================================================
HAS_MOVIEPY = False
try:
    from moviepy.editor import ImageClip, CompositeVideoClip, AudioFileClip, ColorClip
    HAS_MOVIEPY = True
except ImportError:
    try:
        from moviepy.editor import ImageClip, CompositeVideoClip, AudioFileClip
        from moviepy.video.VideoClip import ColorClip
        HAS_MOVIEPY = True
    except: HAS_MOVIEPY = False

HAS_PYDUB = False
try:
    from pydub import AudioSegment
    from pydub.generators import Sine, WhiteNoise
    HAS_PYDUB = True
except: pass

def get_font_cached(size, weight='normal', style='normal'):
    prop = load_font_properties().copy()
    prop.set_size(size)
    prop.set_weight(weight)
    prop.set_style(style)
    return prop

# --- NOUVEAU PARSER (COMPATIBLE BASE 12) ---
def parser_texte(texte):
    data = []
    current_tick = 0
    last_note_tick = 0
    last_note_duration = TICKS_NOIRE # Durée par défaut = Noire
    
    if not texte: return []
    
    for ligne in texte.strip().split('\n'):
        parts = ligne.strip().split(maxsplit=2)
        if not parts: continue
        try:
            col1 = parts[0]
            
            # 1. DÉTECTION DU RYTHME
            if col1 == '=':
                this_start = last_note_tick
                this_duration = last_note_duration
            elif col1.isdigit():
                # Cas "1" (début) ou chiffre => on reset ou on avance d'une noire
                this_start = 0 if col1 == '1' else current_tick
                this_duration = TICKS_NOIRE
                current_tick = this_start + this_duration
            elif col1 in SYMBOLES_DUREE:
                # C'est un symbole (+, ♪, etc.)
                this_duration = SYMBOLES_DUREE[col1]
                this_start = current_tick
                current_tick += this_duration
            else:
                # Cas par défaut (si l'utilisateur a tapé une vieille syntaxe sans symbole)
                # On assume que c'est une Noire si ça ressemble à un '+' ou chiffre
                if col1 == '+': 
                    this_duration = TICKS_NOIRE
                    this_start = current_tick
                    current_tick += this_duration
                else: continue

            last_note_tick = this_start
            last_note_duration = this_duration

            # 2. ANALYSE DU CONTENU
            corde_valide = parts[1].upper()
            
            if corde_valide == 'TXT':
                msg = parts[2] if len(parts) > 2 else ""
                data.append({'tick': this_start, 'duration': this_duration, 'corde': 'TEXTE', 'message': msg}); continue
            elif corde_valide == 'PAGE':
                data.append({'tick': this_start, 'duration': 0, 'corde': 'PAGE_BREAK'}); continue
            
            corde_valide = 'SILENCE' if corde_valide=='S' else 'SEPARATOR' if corde_valide=='SEP' else corde_valide
            
            doigt = None; repetition = 1
            if len(parts) > 2:
                for p in parts[2].split():
                    p_upper = p.upper()
                    if p_upper.startswith('X') and p_upper[1:].isdigit(): repetition = int(p_upper[1:])
                    elif p_upper in ['I', 'P']: doigt = p_upper
            
            if not doigt and corde_valide in AUTOMATIC_FINGERING: doigt = AUTOMATIC_FINGERING[corde_valide]
            
            # Gestion répétition
            temp_cursor = this_start
            for i in range(repetition):
                note = {'tick': temp_cursor, 'duration': this_duration, 'corde': corde_valide}
                if doigt: note['doigt'] = doigt
                data.append(note)
                
                if i < repetition - 1:
                    temp_cursor += this_duration
                    current_tick = temp_cursor + this_duration # Mise à jour du curseur global si répétition

        except: pass
        
    data.sort(key=lambda x: x['tick'])
    return data

def compiler_arrangement(structure_str, blocks_dict):
    full_text = ""
    parts = [p.strip() for p in structure_str.split('+') if p.strip()]
    for part in parts:
        match = re.match(r"(.+?)\s*[xX]\s*(\d+)", part)
        if match:
            block_name = match.group(1).strip()
            repeat_count = int(match.group(2))
        else:
            block_name = part
            repeat_count = 1
        if block_name in blocks_dict:
            content = blocks_dict[block_name].strip()
            for _ in range(repeat_count): full_text += content + "\n"
        else: full_text += f"+ TXT [Bloc '{block_name}' introuvable]\n"
    return full_text

# ==============================================================================
# 🎹 MOTEUR AUDIO (NOUVEAU - SLICING)
# ==============================================================================
def get_note_freq(note_name):
    base_freqs = {'C': 261.63, 'C#': 277.18, 'D': 293.66, 'Eb': 311.13, 'E': 329.63, 'F': 349.23, 'F#': 369.99, 'G': 392.00, 'G#': 415.30, 'A': 440.00, 'Bb': 466.16, 'B': 493.88}
    return base_freqs.get(note_name[0].upper(), 440.0)

@st.cache_data(show_spinner=False)
def generer_audio_mix(sequence, bpm, acc_config, preview_mode=False):
    if not HAS_PYDUB: return None
    if not sequence: return None
    
    samples_loaded = {}
    cordes_utilisees = set([n['corde'] for n in sequence if n['corde'] in POSITIONS_X])
    
    for corde in cordes_utilisees:
        loaded = False
        note_name = acc_config.get(corde, {'n':'C'})['n']
        chemin = os.path.join(DOSSIER_SAMPLES, f"{note_name}.mp3")
        
        if os.path.exists(DOSSIER_SAMPLES):
            if os.path.exists(chemin): 
                sound = AudioSegment.from_mp3(chemin) # Pas de fade in/out ici, on le fait après
                samples_loaded[corde] = sound
                loaded = True
            else:
                chemin_def = os.path.join(DOSSIER_SAMPLES, f"{corde}.mp3")
                if os.path.exists(chemin_def):
                    sound = AudioSegment.from_mp3(chemin_def)
                    samples_loaded[corde] = sound
                    loaded = True

        if not loaded:
            freq = get_note_freq(note_name)
            duration = 1000 # On génère un son long qu'on coupera
            tone = Sine(freq).to_audio_segment(duration=duration).apply_gain(-5)
            samples_loaded[corde] = tone 
            
    if not samples_loaded: return None
    
    # Calcul temps base 12
    # 1 temps (Noire = 12 ticks) = 60000/BPM ms
    ms_par_tick = (60000 / bpm) / TICKS_NOIRE
    
    dernier_tick = sequence[-1]['tick'] + sequence[-1]['duration']
    duree_totale_ms = int(dernier_tick * ms_par_tick) + 1000 # Marge
    mix = AudioSegment.silent(duration=duree_totale_ms)
    
    for n in sequence:
        corde = n['corde']
        if corde in samples_loaded:
            start_ms = int(n['tick'] * ms_par_tick)
            duration_ticks = n['duration']
            
            # Durée théorique
            note_ms = int(duration_ticks * ms_par_tick)
            
            original_sample = samples_loaded[corde]
            
            # SLICING INTELLIGENT
            # Si note rapide (croche ou moins), on coupe
            # Sinon on laisse sonner un peu
            len_to_keep = note_ms
            if preview_mode and len_to_keep > 2000: len_to_keep = 2000
            
            if len(original_sample) > len_to_keep:
                # On coupe et on fade out pour éviter le clic
                played_sample = original_sample[:len_to_keep].fade_out(15)
            else:
                played_sample = original_sample

            mix = mix.overlay(played_sample, position=start_ms)
    
    buffer = io.BytesIO(); mix.export(buffer, format="mp3", bitrate="128k"); buffer.seek(0)
    return buffer

@st.cache_data(show_spinner=False)
def generer_metronome(bpm, duration_sec=30, signature="4/4"):
    if not HAS_PYDUB: return None
    shaker_acc = WhiteNoise().to_audio_segment(duration=60).fade_out(50)
    click_acc = Sine(1500).to_audio_segment(duration=20).fade_out(20).apply_gain(-10)
    sound_accent = shaker_acc.overlay(click_acc).apply_gain(-2)
    sound_normal = WhiteNoise().to_audio_segment(duration=40).fade_out(35).apply_gain(-8)
    ms_per_beat = 60000 / bpm
    silence_acc = max(0, ms_per_beat - len(sound_accent))
    silence_norm = max(0, ms_per_beat - len(sound_normal))
    beat_accent = sound_accent + AudioSegment.silent(duration=silence_acc)
    beat_normal = sound_normal + AudioSegment.silent(duration=silence_norm)
    if signature == "3/4": measure_block = beat_accent + beat_normal + beat_normal
    else: measure_block = beat_accent + beat_normal + beat_normal + beat_normal
    nb_mesures = int((duration_sec * 1000) / len(measure_block)) + 1
    metronome_track = (measure_block * nb_mesures)[:int(duration_sec*1000)]
    buffer = io.BytesIO()
    metronome_track.export(buffer, format="mp3", bitrate="32k", parameters=["-preset", "ultrafast"])
    buffer.seek(0)
    return buffer

# ==============================================================================
# 🎨 MOTEUR AFFICHAGE (NOUVEAU - TICKS & LIGATURES)
# ==============================================================================
def dessiner_contenu_legende(ax, y_pos, styles, mode_white=False):
    c_txt = styles['TEXTE']; c_fond = styles['LEGENDE_FOND']; c_bulle = styles['PERLE_FOND']
    prop_annotation = get_font_cached(16, 'bold'); prop_legende = get_font_cached(12, 'bold')
    
    img_pouce = load_image_asset(CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE)
    img_index = load_image_asset(CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX)

    rect = patches.FancyBboxPatch((-7.5, y_pos - 3.6), 15, 3.3, boxstyle="round,pad=0.1", linewidth=1.5, edgecolor=c_txt, facecolor=c_fond, zorder=0); ax.add_patch(rect)
    ax.text(0, y_pos - 0.6, "LÉGENDE", ha='center', va='center', fontsize=14, fontweight='bold', color=c_txt, fontproperties=prop_annotation)
    x_icon_center = -5.5; x_text_align = -4.5; y_row1 = y_pos - 1.2; y_row2 = y_pos - 1.8; y_row3 = y_pos - 2.4; y_row4 = y_pos - 3.0
    
    if img_pouce is not None: ab = AnnotationBbox(OffsetImage(img_pouce, zoom=0.045), (x_icon_center, y_row1), frameon=False); ax.add_artist(ab)
    ax.text(x_text_align, y_row1, "= Pouce", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    
    if img_index is not None: ab = AnnotationBbox(OffsetImage(img_index, zoom=0.045), (x_icon_center, y_row2), frameon=False); ax.add_artist(ab)
    ax.text(x_text_align, y_row2, "= Index", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    
    # AJOUT VISUEL DES RYTHMES
    ax.text(0, y_row3, "RYTHMES :  + = Noire  |  ♪ = Croche  |  🎶 = Triolet  |  ♬ = Double", ha='center', va='center', fontsize=12, fontweight='bold', color=c_txt)

    x_droite = 1.5; y_text_top = y_pos - 1.2; line_height = 0.45
    
    # --- MODIFICATION: Ligne horizontale avec Flexbox-like drawing en Matplotlib ---
    # On dessine une ligne noire au milieu
    ax.plot([x_droite + 0.5, 6.0], [y_text_top + 0.2, y_text_top + 0.2], color='black', lw=2)
    # Lettre G à gauche
    ax.text(x_droite + 0.2, y_text_top + 0.2, "G", ha='right', va='center', fontsize=14, fontweight='bold', color=c_txt)
    # Lettre D à droite
    ax.text(6.3, y_text_top + 0.2, "D", ha='left', va='center', fontsize=14, fontweight='bold', color=c_txt)
    
    # Texte explicatif dessous (inchangé)
    ax.text(x_droite, y_text_top - line_height, "1G = 1ère corde à gauche", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    ax.text(x_droite, y_text_top - line_height*2, "2G = 2ème corde à gauche", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    # ... suite des textes ...

def generer_page_1_legende(titre, styles, mode_white=False):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; prop_titre = get_font_cached(32, 'bold')
    fig = Figure(figsize=(16, 8), facecolor=c_fond)
    ax = fig.subplots()
    ax.set_facecolor(c_fond)
    ax.text(0, 2.5, titre, ha='center', va='bottom', fontproperties=prop_titre, color=c_txt)
    dessiner_contenu_legende(ax, 0.5, styles, mode_white)
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(-6, 4); ax.axis('off')
    return fig

def generer_page_notes(notes_page, idx, titre, config_acc, styles, options_visuelles, mode_white=False):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    img_pouce = load_image_asset(CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE)
    img_index = load_image_asset(CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX)
    
    # CALCUL BASE 12 (TICKS)
    tick_min = notes_page[0]['tick']
    tick_max = notes_page[-1]['tick'] + 12 # +1 temps de marge
    
    # Echelle Y : 1 temps (noire) = 1.0 unité graphique
    hauteur_unites = (tick_max - tick_min) / 12.0
    hauteur_fig = max(6, (hauteur_unites * 0.75) + 6)
    
    fig = Figure(figsize=(16, hauteur_fig), facecolor=c_fond)
    ax = fig.subplots()
    ax.set_facecolor(c_fond)
    
    y_top = 2.5; y_bot = - hauteur_unites - 1.5; y_top_cordes = y_top
    prop_titre = get_font_cached(32, 'bold'); prop_texte = get_font_cached(20, 'bold')
    prop_note_us = get_font_cached(24, 'bold'); prop_note_eu = get_font_cached(18, 'normal', 'italic')
    prop_numero = get_font_cached(14, 'bold'); prop_standard = get_font_cached(14, 'bold')
    prop_annotation = get_font_cached(16, 'bold')
    
    if not mode_white and options_visuelles['use_bg']:
        img_fond = load_image_asset(CHEMIN_IMAGE_FOND)
        if img_fond is not None:
            try:
                h_px, w_px = img_fond.shape[:2]; ratio = w_px / h_px
                largeur_finale = 15.0 * 0.7; hauteur_finale = (largeur_finale / ratio) * 1.4
                y_center = (y_top + y_bot) / 2
                extent = [-largeur_finale/2, largeur_finale/2, y_center - hauteur_finale/2, y_center + hauteur_finale/2]
                ax.imshow(img_fond, extent=extent, aspect='auto', zorder=-1, alpha=options_visuelles['alpha'])
            except: pass
            
    ax.text(0, y_top + 3.0, f"{titre} (Page {idx})", ha='center', va='bottom', fontproperties=prop_titre, color=c_txt)
    ax.text(-3.5, y_top_cordes + 2.0, "Cordes de Gauche", ha='center', va='bottom', fontproperties=prop_texte, color=c_txt)
    ax.text(3.5, y_top_cordes + 2.0, "Cordes de Droite", ha='center', va='bottom', fontproperties=prop_texte, color=c_txt)
    ax.vlines(0, y_bot, y_top_cordes + 1.8, color=c_txt, lw=5, zorder=2)
    
    for code, props in config_acc.items():
        x = props['x']; note = props['n']; 
        c = get_color_for_note(note)
        ax.text(x, y_top_cordes + 1.3, code, ha='center', color='gray', fontproperties=prop_numero)
        ax.text(x, y_top_cordes + 0.7, note, ha='center', color=c, fontproperties=prop_note_us)
        ax.text(x, y_top_cordes + 0.1, TRADUCTION_NOTES.get(note[0].upper(), '?'), ha='center', color=c, fontproperties=prop_note_eu)
        ax.vlines(x, y_bot, y_top_cordes, colors=c, lw=3, zorder=1)
    
    # LIGNES HORIZONTALES (TEMPS) - Tous les 12 ticks
    start_beat_tick = (tick_min // 12) * 12
    for t in range(start_beat_tick, tick_max + 12, 12):
        y = - ((t - tick_min) / 12.0)
        ax.axhline(y=y, color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)

    map_labels = {}; last_sep_tick = tick_min - 12
    processed_t = set()
    
    # Labels de temps (1, 2, 3...)
    for n in notes_page:
        t = n['tick']
        if n['corde'] in ['SEPARATOR', 'TEXTE']: last_sep_tick = t
        # On affiche le numéro si c'est le début d'un temps (multiple de 12)
        elif t % 12 == 0 and t not in processed_t:
            num_temps = (t - last_sep_tick) // 12
            if num_temps > 0: map_labels[t] = str(num_temps)
            processed_t.add(t)
            
    notes_par_tick = {}; rayon = 0.30
    for n in notes_page:
        tick_absolu = n['tick']
        y = - ((tick_absolu - tick_min) / 12.0)
        
        if y not in notes_par_tick: notes_par_tick[y] = []
        notes_par_tick[y].append(n); code = n['corde']
        
        if code == 'TEXTE': 
            bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt, lw=2)
            ax.text(0, y, n.get('message',''), ha='center', va='center', color='black', fontproperties=prop_annotation, bbox=bbox, zorder=10)
        elif code == 'SEPARATOR': 
            ax.axhline(y, color=c_txt, lw=3, zorder=4)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']; 
            c = get_color_for_note(props['n'])
            
            ax.add_patch(patches.Circle((x, y), rayon, color=c_perle, zorder=3))
            ax.add_patch(patches.Circle((x, y), rayon, fill=False, edgecolor=c, lw=3, zorder=4))
            
            # Numéro de temps seulement sur les temps pleins
            label = map_labels.get(tick_absolu, "")
            ax.text(x, y, label, ha='center', va='center', color='black', fontproperties=prop_standard, zorder=6)
            
            if 'doigt' in n:
                doigt = n['doigt']; current_img = img_index if doigt == 'I' else img_pouce
                if current_img is not None:
                    try: ab = AnnotationBbox(OffsetImage(current_img, zoom=0.045), (x - 0.70, y + 0.1), frameon=False, zorder=8); ax.add_artist(ab)
                    except: pass
                else: ax.text(x - 0.70, y, doigt, ha='center', va='center', color=c_txt, fontproperties=prop_standard, zorder=7)
    
    # ACCORDS (Ligne horizontale)
    for y, group in notes_par_tick.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)

    # LIGATURES (Beams) pour les groupes rythmiques
    sorted_notes = sorted([n for n in notes_page if n['corde'] in config_acc], key=lambda x: x['tick'])
    for i in range(len(sorted_notes) - 1):
        n1 = sorted_notes[i]
        n2 = sorted_notes[i+1]
        
        # Si notes courtes (< Noire) et dans le même temps
        if n1['duration'] < 12 and n2['duration'] < 12:
            beat1 = n1['tick'] // 12
            beat2 = n2['tick'] // 12
            if beat1 == beat2:
                y1 = - ((n1['tick'] - tick_min) / 12.0)
                y2 = - ((n2['tick'] - tick_min) / 12.0)
                
                lw_link = 3 if n1['duration'] <= 4 else 1.5
                color_link = '#A67C52'
                
                # Double barre pour les doubles croches (durée 3 ticks)
                if n1['duration'] == 3:
                      ax.plot([-0.2, -0.2], [y1, y2], color=color_link, lw=lw_link, zorder=2, alpha=0.7)
                      ax.plot([-0.3, -0.3], [y1, y2], color=color_link, lw=lw_link, zorder=2, alpha=0.7)
                else:
                      ax.plot([-0.2, -0.2], [y1, y2], color=color_link, lw=lw_link, zorder=2, alpha=0.7)
            
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(y_bot, y_top + 5); ax.axis('off')
    return fig

def generer_image_longue_calibree(sequence, config_acc, styles, dpi=72):
    if not sequence: return None, 0, 0
    t_min = sequence[0]['tick']; t_max = sequence[-1]['tick']
    
    # Conversion Ticks -> Unités
    hauteur_unites = (t_max - t_min) / 12.0
    y_max_header = 3.0; y_min_footer = -hauteur_unites - 2.0
    
    FIG_WIDTH = 16; FIG_HEIGHT = (y_max_header - y_min_footer) * 0.8; DPI = dpi
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    fig = Figure(figsize=(FIG_WIDTH, FIG_HEIGHT), dpi=DPI, facecolor=c_fond)
    ax = fig.subplots()
    ax.set_facecolor(c_fond)
    ax.set_ylim(y_min_footer, y_max_header); ax.set_xlim(-7.5, 7.5)
    y_top = 2.0; y_bot = y_min_footer + 1.0 
    prop_note_us = get_font_cached(24, 'bold'); prop_note_eu = get_font_cached(18, 'normal', 'italic'); prop_numero = get_font_cached(14, 'bold'); prop_standard = get_font_cached(14, 'bold'); prop_annotation = get_font_cached(16, 'bold')
    img_pouce = load_image_asset(CHEMIN_ICON_POUCE_BLANC if c_fond == 'white' else CHEMIN_ICON_POUCE)
    img_index = load_image_asset(CHEMIN_ICON_INDEX_BLANC if c_fond == 'white' else CHEMIN_ICON_INDEX)

    ax.vlines(0, y_bot, y_top + 1.8, color=c_txt, lw=5, zorder=2)
    for code, props in config_acc.items():
        x = props['x']; note = props['n']; 
        c = get_color_for_note(note)
        ax.text(x, y_top + 1.3, code, ha='center', color='gray', fontproperties=prop_numero); ax.text(x, y_top + 0.7, note, ha='center', color=c, fontproperties=prop_note_us); ax.text(x, y_top + 0.1, TRADUCTION_NOTES.get(note[0].upper(), '?'), ha='center', color=c, fontproperties=prop_note_eu); ax.vlines(x, y_bot, y_top, colors=c, lw=3, zorder=1)
    
    # Lignes temps
    start_beat = (t_min // 12) * 12
    for t in range(start_beat, t_max + 12, 12):
        y = - ((t - t_min) / 12.0)
        ax.axhline(y=y, color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)
        
    notes_par_tick = {}; rayon = 0.30
    for n in sequence:
        if n['corde'] == 'PAGE_BREAK': continue 
        t_absolu = n['tick']; y = - ((t_absolu - t_min) / 12.0)
        if y not in notes_par_tick: notes_par_tick[y] = []
        notes_par_tick[y].append(n); code = n['corde']
        
        if code == 'TEXTE': bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt, lw=2); ax.text(0, y, n.get('message',''), ha='center', va='center', color='black', fontproperties=prop_annotation, bbox=bbox, zorder=10)
        elif code == 'SEPARATOR': ax.axhline(y, color=c_txt, lw=3, zorder=4)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']; 
            c = get_color_for_note(props['n'])
            ax.add_patch(patches.Circle((x, y), rayon, color=c_perle, zorder=3)); ax.add_patch(patches.Circle((x, y), rayon, fill=False, edgecolor=c, lw=3, zorder=4))
            
            if 'doigt' in n:
                doigt = n['doigt']; current_img = img_index if doigt == 'I' else img_pouce
                if current_img is not None:
                    try: ab = AnnotationBbox(OffsetImage(current_img, zoom=0.045), (x - 0.70, y + 0.1), frameon=False, zorder=8); ax.add_artist(ab)
                    except: pass
                else: ax.text(x - 0.70, y, doigt, ha='center', va='center', color=c_txt, fontproperties=prop_standard, zorder=7)
    for y, group in notes_par_tick.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]; 
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)
    ax.axis('off')
    
    px_y_t0 = ax.transData.transform((0, 0))[1]
    px_y_t1 = ax.transData.transform((0, -1))[1] # 1 temps
    total_h_px = FIG_HEIGHT * DPI
    pixels_par_temps = px_y_t0 - px_y_t1
    offset_premiere_note_px = total_h_px - px_y_t0
    buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=DPI, facecolor=c_fond, bbox_inches=None)
    buf.seek(0)
    plt.close(fig) 
    return buf, pixels_par_temps, offset_premiere_note_px

def creer_video_avec_son_calibree(image_buffer, audio_buffer, duration_sec, metrics, bpm, fps=15):
    pixels_par_temps, offset_premiere_note_px = metrics
    temp_img_path = None; temp_audio_path = None; output_filename = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f_img:
            f_img.write(image_buffer.getbuffer())
            temp_img_path = f_img.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f_audio:
            f_audio.write(audio_buffer.getbuffer())
            temp_audio_path = f_audio.name 
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f_vid:
            output_filename = f_vid.name
        clip_img = ImageClip(temp_img_path)
        w, h = clip_img.size
        video_h = 480 
        bar_y = 100
        start_y = bar_y - offset_premiere_note_px
        speed_px_sec = pixels_par_temps * (bpm / 60.0)
        def scroll_func(t):
            current_y = start_y - (speed_px_sec * t)
            return ('center', current_y)
        moving_clip = clip_img.set_position(scroll_func).set_duration(duration_sec)
        try:
            bar_height = int(pixels_par_temps)
            highlight_bar = ColorClip(size=(w, bar_height), color=(255, 215, 0)).set_opacity(0.3).set_position(('center', bar_y - bar_height/2)).set_duration(duration_sec)
            bg_clip = ColorClip(size=(w, video_h), color=(229, 196, 163)).set_duration(duration_sec) 
            video_visual = CompositeVideoClip([bg_clip, moving_clip, highlight_bar], size=(w, video_h))
        except:
            video_visual = CompositeVideoClip([moving_clip], size=(w, video_h))
        audio_clip = AudioFileClip(temp_audio_path).subclip(0, duration_sec)
        final = video_visual.set_audio(audio_clip)
        final.fps = fps
        final.write_videofile(output_filename, codec='libx264', audio_codec='aac', preset='ultrafast', ffmpeg_params=['-pix_fmt', 'yuv420p'], logger=None)
        audio_clip.close(); video_visual.close(); clip_img.close(); final.close()
        return output_filename
    except Exception as e:
        st.error(f"Erreur vidéo : {e}")
        return None
    finally:
        if temp_img_path and os.path.exists(temp_img_path): os.remove(temp_img_path)
        if temp_audio_path and os.path.exists(temp_audio_path): os.remove(temp_audio_path)

def generer_pdf_livret(buffers, titre):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    for item in buffers:
        pdf.add_page()
        temp_img = f"temp_pdf_{item['type']}_{item.get('idx', 0)}_{random.randint(0,1000)}.png"
        item['buf'].seek(0)
        with open(temp_img, "wb") as f:
            f.write(item['buf'].read()) 
        pdf.image(temp_img, x=10, y=10, w=190)
        if os.path.exists(temp_img): os.remove(temp_img)
    buf = io.BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    buf.write(pdf_output)
    buf.seek(0)
    return buf

# ==============================================================================
# 🎛️ INTERFACE STREAMLIT
# ==============================================================================
if len(BANQUE_TABLATURES) > 0: PREMIER_TITRE = list(BANQUE_TABLATURES.keys())[0]
else: PREMIER_TITRE = "Défaut"; BANQUE_TABLATURES[PREMIER_TITRE] = ""

if st.session_state.code_actuel == "":
    st.session_state.code_actuel = BANQUE_TABLATURES[PREMIER_TITRE].strip()

query_params = st.query_params
if "code" in query_params and st.session_state.code_actuel == BANQUE_TABLATURES[PREMIER_TITRE].strip():
    try: st.session_state.code_actuel = query_params["code"]
    except: pass

def charger_element_banque(titre):
    if titre in BANQUE_TABLATURES:
        nouveau = BANQUE_TABLATURES[titre].strip()
        st.session_state.code_actuel = nouveau
        st.session_state.widget_input = nouveau
        st.session_state.partition_generated = False
        st.session_state.video_path = None
        st.session_state.audio_buffer = None
        st.session_state.pdf_buffer = None
        st.session_state.seq_grid = {}
        
        # Nettoyage mémoire agressif uniquement lors du chargement d'un nouveau morceau
        gc.collect()
        
        # Gestion de la gamme
        nom_gamme_a_charger = ASSOCIATIONS_MORCEAUX_GAMMES.get(titre, "1. Pentatonique Fondamentale")
        if nom_gamme_a_charger in GAMMES_PRESETS:
            notes_str = GAMMES_PRESETS[nom_gamme_a_charger]
            parsed = parse_gamme_string(notes_str)
            if len(parsed) == 12:
                for idx, k in enumerate(ORDRE_MAPPING_GAMME):
                    st.session_state[f"acc_{k}"] = parsed[idx]
                st.session_state['gamme_selector'] = nom_gamme_a_charger
                st.toast(f"Gamme chargée : {nom_gamme_a_charger}", icon="🎸")

def mise_a_jour_texte(): 
    st.session_state.code_actuel = st.session_state.widget_input
    st.session_state.partition_generated = False
    st.session_state.video_path = None
    st.session_state.audio_buffer = None
    st.session_state.pdf_buffer = None

def ajouter_texte(txt):
    if 'code_actuel' in st.session_state: st.session_state.code_actuel += "\n" + txt
    else: st.session_state.code_actuel = txt
    st.session_state.widget_input = st.session_state.code_actuel

def ajouter_avec_feedback(txt, label_toast):
    ajouter_texte(txt)
    st.toast(f"Ajouté : {label_toast}", icon="✅")

def annuler_derniere_ligne():
    lines = st.session_state.code_actuel.strip().split('\n')
    if len(lines) > 0:
        st.session_state.code_actuel = "\n".join(lines[:-1])
        st.session_state.widget_input = st.session_state.code_actuel
        st.toast("Dernière note effacée", icon="🗑️")

def afficher_section_sauvegarde_bloc(suffix):
    st.markdown("---")
    with st.expander("Sauvegarder ce motif en bloc"):
        b_name_btn = st.text_input("Nom du bloc", key=f"name_blk_{suffix}", help="Donnez un nom unique à ce bloc pour l'utiliser dans la structure.")
        if st.button("Sauvegarder", key=f"btn_save_{suffix}", help="Enregistre la séquence actuelle comme un bloc réutilisable"):
            if b_name_btn and st.session_state.code_actuel:
                st.session_state.stored_blocks[b_name_btn] = st.session_state.code_actuel
                st.toast(f"Bloc '{b_name_btn}' créé !", icon="📦")

# CONSTANTES VARIABLES
bg_color = "#e5c4a3"
use_bg_img = True
bg_alpha = 0.2
force_white_print = True

with st.sidebar:
    st.header("🎚️ Réglages")
    st.markdown("### 📚 Banque de Morceaux")
    
    # --- MODIFICATION SIDEBAR (ONGLETS) ---
    tous_les_titres = list(BANQUE_TABLATURES.keys())
    titres_exos = [k for k in tous_les_titres if "Exercice" in k or "Démonstration" in k]
    titres_morceaux = [k for k in tous_les_titres if k not in titres_exos]
    
    # Ajout du "Nouveau" dans les exos s'il n'y est pas, pour praticité
    if "--- Nouveau / Vide ---" in titres_morceaux and "--- Nouveau / Vide ---" not in titres_exos:
        titres_exos.insert(0, "--- Nouveau / Vide ---")

    tab_b1, tab_b2 = st.tabs(["🎵 Morceaux", "💪 Exercices"])

    with tab_b1:
        choix_morceau = st.selectbox("Morceau :", options=titres_morceaux, key='sel_morceau', help="Sélectionnez un morceau existant pour le charger")
        if st.button("Charger Morceau", use_container_width=True, help="Remplace l'éditeur actuel par le morceau choisi"):
            charger_element_banque(choix_morceau)

    with tab_b2:
        choix_exo = st.selectbox("Exercice :", options=titres_exos, key='sel_exo', help="Sélectionnez un exercice pour vous entraîner")
        if st.button("Charger Exercice", use_container_width=True, help="Charge l'exercice sélectionné"):
            charger_element_banque(choix_exo)
    
    st.caption("⚠️ Remplacera le texte actuel.")
    st.markdown("---")
    # --- FIN MODIFICATION ---
    
    st.markdown("### 🤝 Contribuer")
    st.markdown(f'<a href="mailto:julienflorin59@gmail.com?subject=Proposition de partition" target="_blank"><button title="Envoyez vos créations par email au développeur" style="width:100%; background-color:#A67C52; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">📧 Proposer une partition</button></a>', unsafe_allow_html=True)
    st.markdown(f'<a href="mailto:julienflorin59@gmail.com?subject=Proposition de morceau" target="_blank"><button title="Suggérer un morceau à ajouter" style="width:100%; background-color:#A67C52; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; font-weight:bold; margin-top:5px;">🎵 Proposer un morceau</button></a>', unsafe_allow_html=True)
    
    current_scale_info = ""
    for k in ORDRE_MAPPING_GAMME:
        note = st.session_state.get(f"acc_{k}", "?")
        current_scale_info += f"{k}: {note}%0A"