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
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# 📱 OPTIMISATION CSS : FORCE BRUTE & LÉGENDE RESPONSIVE
# ==============================================================================
@st.cache_resource
def load_css_styles():
    return """
<style>
    /* 1. CONTENEUR PRINCIPAL */
    .stApp { overflow-x: hidden !important; }
    div[data-testid="block-container"] {
        padding-top: 1rem !important;
        padding-left: 0.2rem !important; padding-right: 0.2rem !important;
        max-width: 100% !important;
    }

    /* ============================================================
       LÉGENDE RESPONSIVE (Nouveauté)
    ============================================================ */
    /* Par défaut (PC) : On affiche les pastilles, on cache le texte mobile */
    .legende-pc-container {
        display: flex !important;
        flex-direction: row;
        justify-content: space-around;
        align-items: center;
        flex-wrap: wrap;
        background-color: rgba(255,255,255,0.1);
        padding: 10px;
        border-radius: 10px;
    }
    .legende-mobile-text {
        display: none !important;
    }

    /* SUR MOBILE (< 600px) : On inverse ! */
    @media (max-width: 600px) {
        .legende-pc-container {
            display: none !important;
        }
        .legende-mobile-text {
            display: block !important;
            text-align: center;
            font-weight: bold;
            font-size: 1.1rem;
            padding: 10px;
            /* CHANGEMENT ICI : COULEUR BEIGE + BORDURE */
            background-color: #e5c4a3; 
            border: 1px solid #A67C52;
            color: black;
            border-radius: 8px;
            line-height: 1.8 !important;
        }
    }

    /* ============================================================
       GESTION DES LAYOUTS MOBILES (Code précédent conservé)
    ============================================================ */
    @media (max-width: 950px) {
        /* Structure (Editeur/Aperçu) en colonne */
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(2)):not(:has(> div[data-testid="column"]:nth-child(3))) {
            flex-direction: column !important;
            gap: 2rem !important;
        }

        /* Grilles de boutons en ligne avec scroll */
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(3)) {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            justify-content: flex-start !important;
            gap: 4px !important;
            padding-bottom: 10px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(3)) > div[data-testid="column"] {
            min-width: 45px !important;
            max-width: 45px !important;
            width: 45px !important;
            flex: 0 0 auto !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(3)) button {
            padding: 0px !important;
            font-size: 0.7rem !important;
            overflow: hidden !important;
        }
        /* Exception onglet boutons */
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(3)):not(:has(> div[data-testid="column"]:nth-child(6))) > div[data-testid="column"] {
             min-width: 30vw !important;
             width: 30vw !important;
             max-width: none !important;
        }
    }

    /* ============================================================
       ESTHÉTIQUE GÉNÉRALE
    ============================================================ */
    .stButton button { width: 100%; line-height: 1.2; white-space: nowrap; border-radius: 4px; }
    div[data-testid="column"] button p { font-weight: bold; }
    
    button[data-testid="stTab"] { 
        padding: 5px 10px !important; font-size: 0.8rem !important;
        border: 1px solid #A67C52; border-radius: 5px; margin-right: 2px; 
        background-color: #e5c4a3; color: black; opacity: 0.9; 
    }
    button[data-testid="stTab"][aria-selected="true"] { 
        background-color: #d4b08c; border: 2px solid #A67C52; font-weight: bold; opacity: 1; 
    }
    [data-testid='stFileDropzone'] { background-color: #e5c4a3 !important; color: black !important; border: none !important; padding: 1rem; }
    [data-testid='stFileDropzone']::after { content: "📂 Charger projet"; color: black; font-weight: bold; display: block; text-align: center; font-size: 0.8rem; }
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

# --- CONSTANTES RYTHMIQUES (BASE 12) ---
TICKS_NOIRE = 12; TICKS_CROCHE = 6; TICKS_TRIOLET = 4; TICKS_DOUBLE = 3
SYMBOLES_DUREE = {'+': TICKS_NOIRE, '♪': TICKS_CROCHE, '🎶': TICKS_TRIOLET, '♬': TICKS_DOUBLE}

# --- COULEURS & LOGIQUE ---
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
# 📦 GESTION DE LA PERSISTANCE
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
# 🧠 MOTEUR LOGIQUE (Audio/Vidéo/Graphisme)
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

def parser_texte(texte):
    data = []
    current_tick = 0
    last_note_tick = 0
    last_note_duration = TICKS_NOIRE 
    if not texte: return []
    for ligne in texte.strip().split('\n'):
        parts = ligne.strip().split(maxsplit=2)
        if not parts: continue
        try:
            col1 = parts[0]
            if col1 == '=':
                this_start = last_note_tick; this_duration = last_note_duration
            elif col1.isdigit():
                this_start = 0 if col1 == '1' else current_tick
                this_duration = TICKS_NOIRE
                current_tick = this_start + this_duration
            elif col1 in SYMBOLES_DUREE:
                this_duration = SYMBOLES_DUREE[col1]; this_start = current_tick
                current_tick += this_duration
            else:
                if col1 == '+': this_duration = TICKS_NOIRE; this_start = current_tick; current_tick += this_duration
                else: continue
            last_note_tick = this_start; last_note_duration = this_duration
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
            temp_cursor = this_start
            for i in range(repetition):
                note = {'tick': temp_cursor, 'duration': this_duration, 'corde': corde_valide}
                if doigt: note['doigt'] = doigt
                data.append(note)
                if i < repetition - 1:
                    temp_cursor += this_duration
                    current_tick = temp_cursor + this_duration
        except: pass
    data.sort(key=lambda x: x['tick'])
    return data

def compiler_arrangement(structure_str, blocks_dict):
    full_text = ""
    parts = [p.strip() for p in structure_str.split('+') if p.strip()]
    for part in parts:
        match = re.match(r"(.+?)\s*[xX]\s*(\d+)", part)
        if match:
            block_name = match.group(1).strip(); repeat_count = int(match.group(2))
        else:
            block_name = part; repeat_count = 1
        if block_name in blocks_dict:
            content = blocks_dict[block_name].strip()
            for _ in range(repeat_count): full_text += content + "\n"
        else: full_text += f"+ TXT [Bloc '{block_name}' introuvable]\n"
    return full_text

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
                samples_loaded[corde] = AudioSegment.from_mp3(chemin); loaded = True
            else:
                chemin_def = os.path.join(DOSSIER_SAMPLES, f"{corde}.mp3")
                if os.path.exists(chemin_def): samples_loaded[corde] = AudioSegment.from_mp3(chemin_def); loaded = True
        if not loaded:
            freq = get_note_freq(note_name); duration = 1000 
            tone = Sine(freq).to_audio_segment(duration=duration).apply_gain(-5)
            samples_loaded[corde] = tone 
    if not samples_loaded: return None
    ms_par_tick = (60000 / bpm) / TICKS_NOIRE
    dernier_tick = sequence[-1]['tick'] + sequence[-1]['duration']
    duree_totale_ms = int(dernier_tick * ms_par_tick) + 1000
    mix = AudioSegment.silent(duration=duree_totale_ms)
    for n in sequence:
        corde = n['corde']
        if corde in samples_loaded:
            start_ms = int(n['tick'] * ms_par_tick); duration_ticks = n['duration']
            note_ms = int(duration_ticks * ms_par_tick); original_sample = samples_loaded[corde]
            len_to_keep = note_ms
            if preview_mode and len_to_keep > 2000: len_to_keep = 2000
            if len(original_sample) > len_to_keep: played_sample = original_sample[:len_to_keep].fade_out(15)
            else: played_sample = original_sample
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
    buffer = io.BytesIO(); metronome_track.export(buffer, format="mp3", bitrate="32k", parameters=["-preset", "ultrafast"]); buffer.seek(0)
    return buffer

def dessiner_contenu_legende(ax, y_pos, styles, mode_white=False):
    c_txt = styles['TEXTE']; c_fond = styles['LEGENDE_FOND']
    prop_annotation = get_font_cached(16, 'bold'); prop_legende = get_font_cached(12, 'bold')
    img_pouce = load_image_asset(CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE)
    img_index = load_image_asset(CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX)
    rect = patches.FancyBboxPatch((-7.5, y_pos - 3.6), 15, 3.3, boxstyle="round,pad=0.1", linewidth=1.5, edgecolor=c_txt, facecolor=c_fond, zorder=0); ax.add_patch(rect)
    ax.text(0, y_pos - 0.6, "LÉGENDE", ha='center', va='center', fontsize=14, fontweight='bold', color=c_txt, fontproperties=prop_annotation)
    x_icon_center = -5.5; x_text_align = -4.5; y_row1 = y_pos - 1.2; y_row2 = y_pos - 1.8; y_row3 = y_pos - 2.4
    if img_pouce is not None: ab = AnnotationBbox(OffsetImage(img_pouce, zoom=0.045), (x_icon_center, y_row1), frameon=False); ax.add_artist(ab)
    ax.text(x_text_align, y_row1, "= Pouce", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    if img_index is not None: ab = AnnotationBbox(OffsetImage(img_index, zoom=0.045), (x_icon_center, y_row2), frameon=False); ax.add_artist(ab)
    ax.text(x_text_align, y_row2, "= Index", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    ax.text(0, y_row3, "RYTHMES :  + = Noire  |  ♪ = Croche  |  🎶 = Triolet  |  ♬ = Double", ha='center', va='center', fontsize=12, fontweight='bold', color=c_txt)
    x_droite = 1.5; y_text_top = y_pos - 1.2; line_height = 0.45
    ax.plot([x_droite + 0.5, 6.0], [y_text_top + 0.2, y_text_top + 0.2], color='black', lw=2)
    ax.text(x_droite + 0.2, y_text_top + 0.2, "G", ha='right', va='center', fontsize=14, fontweight='bold', color=c_txt)
    ax.text(6.3, y_text_top + 0.2, "D", ha='left', va='center', fontsize=14, fontweight='bold', color=c_txt)
    ax.text(x_droite, y_text_top - line_height, "1G = 1ère corde à gauche", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    ax.text(x_droite, y_text_top - line_height*2, "2G = 2ème corde à gauche", ha='left', va='center', fontproperties=prop_legende, color=c_txt)

def generer_page_1_legende(titre, styles, mode_white=False):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; prop_titre = get_font_cached(32, 'bold')
    fig = Figure(figsize=(16, 8), facecolor=c_fond)
    ax = fig.subplots(); ax.set_facecolor(c_fond)
    ax.text(0, 2.5, titre, ha='center', va='bottom', fontproperties=prop_titre, color=c_txt)
    dessiner_contenu_legende(ax, 0.5, styles, mode_white)
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(-6, 4); ax.axis('off')
    return fig

def generer_page_notes(notes_page, idx, titre, config_acc, styles, options_visuelles, mode_white=False):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    img_pouce = load_image_asset(CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE)
    img_index = load_image_asset(CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX)
    tick_min = notes_page[0]['tick']; tick_max = notes_page[-1]['tick'] + 12 
    hauteur_unites = (tick_max - tick_min) / 12.0; hauteur_fig = max(6, (hauteur_unites * 0.75) + 6)
    fig = Figure(figsize=(16, hauteur_fig), facecolor=c_fond)
    ax = fig.subplots(); ax.set_facecolor(c_fond)
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
        x = props['x']; note = props['n']; c = get_color_for_note(note)
        ax.text(x, y_top_cordes + 1.3, code, ha='center', color='gray', fontproperties=prop_numero)
        ax.text(x, y_top_cordes + 0.7, note, ha='center', color=c, fontproperties=prop_note_us)
        ax.text(x, y_top_cordes + 0.1, TRADUCTION_NOTES.get(note[0].upper(), '?'), ha='center', color=c, fontproperties=prop_note_eu)
        ax.vlines(x, y_bot, y_top_cordes, colors=c, lw=3, zorder=1)
    start_beat_tick = (tick_min // 12) * 12
    for t in range(start_beat_tick, tick_max + 12, 12):
        y = - ((t - tick_min) / 12.0); ax.axhline(y=y, color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)
    map_labels = {}; last_sep_tick = tick_min - 12; processed_t = set()
    for n in notes_page:
        t = n['tick']
        if n['corde'] in ['SEPARATOR', 'TEXTE']: last_sep_tick = t
        elif t % 12 == 0 and t not in processed_t:
            num_temps = (t - last_sep_tick) // 12
            if num_temps > 0: map_labels[t] = str(num_temps)
            processed_t.add(t)
    notes_par_tick = {}; rayon = 0.30
    for n in notes_page:
        tick_absolu = n['tick']; y = - ((tick_absolu - tick_min) / 12.0)
        if y not in notes_par_tick: notes_par_tick[y] = []
        notes_par_tick[y].append(n); code = n['corde']
        if code == 'TEXTE': 
            bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt, lw=2)
            ax.text(0, y, n.get('message',''), ha='center', va='center', color='black', fontproperties=prop_annotation, bbox=bbox, zorder=10)
        elif code == 'SEPARATOR': ax.axhline(y, color=c_txt, lw=3, zorder=4)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']; c = get_color_for_note(props['n'])
            ax.add_patch(patches.Circle((x, y), rayon, color=c_perle, zorder=3))
            ax.add_patch(patches.Circle((x, y), rayon, fill=False, edgecolor=c, lw=3, zorder=4))
            label = map_labels.get(tick_absolu, ""); ax.text(x, y, label, ha='center', va='center', color='black', fontproperties=prop_standard, zorder=6)
            if 'doigt' in n:
                doigt = n['doigt']; current_img = img_index if doigt == 'I' else img_pouce
                if current_img is not None:
                    try: ab = AnnotationBbox(OffsetImage(current_img, zoom=0.045), (x - 0.70, y + 0.1), frameon=False, zorder=8); ax.add_artist(ab)
                    except: pass
                else: ax.text(x - 0.70, y, doigt, ha='center', va='center', color=c_txt, fontproperties=prop_standard, zorder=7)
    for y, group in notes_par_tick.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)
    sorted_notes = sorted([n for n in notes_page if n['corde'] in config_acc], key=lambda x: x['tick'])
    for i in range(len(sorted_notes) - 1):
        n1 = sorted_notes[i]; n2 = sorted_notes[i+1]
        if n1['duration'] < 12 and n2['duration'] < 12:
            beat1 = n1['tick'] // 12; beat2 = n2['tick'] // 12
            if beat1 == beat2:
                y1 = - ((n1['tick'] - tick_min) / 12.0); y2 = - ((n2['tick'] - tick_min) / 12.0)
                lw_link = 3 if n1['duration'] <= 4 else 1.5; color_link = '#A67C52'
                if n1['duration'] == 3:
                      ax.plot([-0.2, -0.2], [y1, y2], color=color_link, lw=lw_link, zorder=2, alpha=0.7)
                      ax.plot([-0.3, -0.3], [y1, y2], color=color_link, lw=lw_link, zorder=2, alpha=0.7)
                else: ax.plot([-0.2, -0.2], [y1, y2], color=color_link, lw=lw_link, zorder=2, alpha=0.7)
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(y_bot, y_top + 5); ax.axis('off')
    return fig

def generer_image_longue_calibree(sequence, config_acc, styles, dpi=72):
    if not sequence: return None, 0, 0
    t_min = sequence[0]['tick']; t_max = sequence[-1]['tick']
    hauteur_unites = (t_max - t_min) / 12.0; y_max_header = 3.0; y_min_footer = -hauteur_unites - 2.0
    FIG_WIDTH = 16; FIG_HEIGHT = (y_max_header - y_min_footer) * 0.8; DPI = dpi
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    fig = Figure(figsize=(FIG_WIDTH, FIG_HEIGHT), dpi=DPI, facecolor=c_fond)
    ax = fig.subplots(); ax.set_facecolor(c_fond); ax.set_ylim(y_min_footer, y_max_header); ax.set_xlim(-7.5, 7.5)
    y_top = 2.0; y_bot = y_min_footer + 1.0 
    prop_note_us = get_font_cached(24, 'bold'); prop_note_eu = get_font_cached(18, 'normal', 'italic'); prop_numero = get_font_cached(14, 'bold'); prop_standard = get_font_cached(14, 'bold'); prop_annotation = get_font_cached(16, 'bold')
    img_pouce = load_image_asset(CHEMIN_ICON_POUCE_BLANC if c_fond == 'white' else CHEMIN_ICON_POUCE)
    img_index = load_image_asset(CHEMIN_ICON_INDEX_BLANC if c_fond == 'white' else CHEMIN_ICON_INDEX)
    ax.vlines(0, y_bot, y_top + 1.8, color=c_txt, lw=5, zorder=2)
    for code, props in config_acc.items():
        x = props['x']; note = props['n']; c = get_color_for_note(note)
        ax.text(x, y_top + 1.3, code, ha='center', color='gray', fontproperties=prop_numero); ax.text(x, y_top + 0.7, note, ha='center', color=c, fontproperties=prop_note_us); ax.text(x, y_top + 0.1, TRADUCTION_NOTES.get(note[0].upper(), '?'), ha='center', color=c, fontproperties=prop_note_eu); ax.vlines(x, y_bot, y_top, colors=c, lw=3, zorder=1)
    start_beat = (t_min // 12) * 12
    for t in range(start_beat, t_max + 12, 12):
        y = - ((t - t_min) / 12.0); ax.axhline(y=y, color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)
    notes_par_tick = {}; rayon = 0.30
    for n in sequence:
        if n['corde'] == 'PAGE_BREAK': continue 
        t_absolu = n['tick']; y = - ((t_absolu - t_min) / 12.0)
        if y not in notes_par_tick: notes_par_tick[y] = []
        notes_par_tick[y].append(n); code = n['corde']
        if code == 'TEXTE': bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt, lw=2); ax.text(0, y, n.get('message',''), ha='center', va='center', color='black', fontproperties=prop_annotation, bbox=bbox, zorder=10)
        elif code == 'SEPARATOR': ax.axhline(y, color=c_txt, lw=3, zorder=4)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']; c = get_color_for_note(props['n'])
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
    px_y_t0 = ax.transData.transform((0, 0))[1]; px_y_t1 = ax.transData.transform((0, -1))[1] 
    total_h_px = FIG_HEIGHT * DPI; pixels_par_temps = px_y_t0 - px_y_t1; offset_premiere_note_px = total_h_px - px_y_t0
    buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=DPI, facecolor=c_fond, bbox_inches=None); buf.seek(0); plt.close(fig) 
    return buf, pixels_par_temps, offset_premiere_note_px

def creer_video_avec_son_calibree(image_buffer, audio_buffer, duration_sec, metrics, bpm, fps=15):
    pixels_par_temps, offset_premiere_note_px = metrics
    temp_img_path = None; temp_audio_path = None; output_filename = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f_img:
            f_img.write(image_buffer.getbuffer()); temp_img_path = f_img.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f_audio:
            f_audio.write(audio_buffer.getbuffer()); temp_audio_path = f_audio.name 
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f_vid:
            output_filename = f_vid.name
        clip_img = ImageClip(temp_img_path); w, h = clip_img.size; video_h = 480; bar_y = 100
        start_y = bar_y - offset_premiere_note_px; speed_px_sec = pixels_par_temps * (bpm / 60.0)
        def scroll_func(t): return ('center', start_y - (speed_px_sec * t))
        moving_clip = clip_img.set_position(scroll_func).set_duration(duration_sec)
        try:
            bar_height = int(pixels_par_temps)
            highlight_bar = ColorClip(size=(w, bar_height), color=(255, 215, 0)).set_opacity(0.3).set_position(('center', bar_y - bar_height/2)).set_duration(duration_sec)
            bg_clip = ColorClip(size=(w, video_h), color=(229, 196, 163)).set_duration(duration_sec) 
            video_visual = CompositeVideoClip([bg_clip, moving_clip, highlight_bar], size=(w, video_h))
        except: video_visual = CompositeVideoClip([moving_clip], size=(w, video_h))
        audio_clip = AudioFileClip(temp_audio_path).subclip(0, duration_sec)
        final = video_visual.set_audio(audio_clip); final.fps = fps
        final.write_videofile(output_filename, codec='libx264', audio_codec='aac', preset='ultrafast', ffmpeg_params=['-pix_fmt', 'yuv420p'], logger=None)
        audio_clip.close(); video_visual.close(); clip_img.close(); final.close()
        return output_filename
    except Exception as e: st.error(f"Erreur vidéo : {e}"); return None
    finally:
        if temp_img_path and os.path.exists(temp_img_path): os.remove(temp_img_path)
        if temp_audio_path and os.path.exists(temp_audio_path): os.remove(temp_audio_path)

def generer_pdf_livret(buffers, titre):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    for item in buffers:
        pdf.add_page()
        temp_img = f"temp_pdf_{item['type']}_{item.get('idx', 0)}_{random.randint(0,1000)}.png"
        item['buf'].seek(0)
        with open(temp_img, "wb") as f: f.write(item['buf'].read()) 
        pdf.image(temp_img, x=10, y=10, w=190)
        if os.path.exists(temp_img): os.remove(temp_img)
    buf = io.BytesIO(); pdf_output = pdf.output(dest='S').encode('latin-1'); buf.write(pdf_output); buf.seek(0)
    return buf

# ==============================================================================
# 🎛️ INTERFACE STREAMLIT
# ==============================================================================
if len(BANQUE_TABLATURES) > 0: PREMIER_TITRE = list(BANQUE_TABLATURES.keys())[0]
else: PREMIER_TITRE = "Défaut"; BANQUE_TABLATURES[PREMIER_TITRE] = ""
if st.session_state.code_actuel == "": st.session_state.code_actuel = BANQUE_TABLATURES[PREMIER_TITRE].strip()
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
        gc.collect()
        nom_gamme_a_charger = ASSOCIATIONS_MORCEAUX_GAMMES.get(titre, "1. Pentatonique Fondamentale")
        if nom_gamme_a_charger in GAMMES_PRESETS:
            notes_str = GAMMES_PRESETS[nom_gamme_a_charger]
            parsed = parse_gamme_string(notes_str)
            if len(parsed) == 12:
                for idx, k in enumerate(ORDRE_MAPPING_GAMME): st.session_state[f"acc_{k}"] = parsed[idx]
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
    ajouter_texte(txt); st.toast(f"Ajouté : {label_toast}", icon="✅")

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
        if st.button("Sauvegarder", key=f"btn_save_{suffix}"):
            if b_name_btn and st.session_state.code_actuel:
                st.session_state.stored_blocks[b_name_btn] = st.session_state.code_actuel
                st.toast(f"Bloc '{b_name_btn}' créé !", icon="📦")

bg_color = "#e5c4a3"; use_bg_img = True; bg_alpha = 0.2; force_white_print = True

with st.sidebar:
    st.header("🎚️ Réglages")
    st.markdown("### 📚 Banque de Morceaux")
    tous_les_titres = list(BANQUE_TABLATURES.keys())
    titres_exos = [k for k in tous_les_titres if "Exercice" in k or "Démonstration" in k]
    titres_morceaux = [k for k in tous_les_titres if k not in titres_exos]
    if "--- Nouveau / Vide ---" in titres_morceaux and "--- Nouveau / Vide ---" not in titres_exos: titres_exos.insert(0, "--- Nouveau / Vide ---")

    tab_b1, tab_b2 = st.tabs(["🎵 Morceaux", "💪 Exercices"])
    with tab_b1:
        choix_morceau = st.selectbox("Morceau :", options=titres_morceaux, key='sel_morceau')
        if st.button("Charger Morceau", use_container_width=True): charger_element_banque(choix_morceau)
    with tab_b2:
        choix_exo = st.selectbox("Exercice :", options=titres_exos, key='sel_exo')
        if st.button("Charger Exercice", use_container_width=True): charger_element_banque(choix_exo)
    st.caption("⚠️ Remplacera le texte actuel.")
    st.markdown("---")
    st.markdown("### 🤝 Contribuer")
    st.markdown(f'<a href="mailto:julienflorin59@gmail.com?subject=Proposition de partition" target="_blank"><button style="width:100%; background-color:#A67C52; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">📧 Proposer une partition</button></a>', unsafe_allow_html=True)
    st.markdown(f'<a href="mailto:julienflorin59@gmail.com?subject=Proposition de morceau" target="_blank"><button style="width:100%; background-color:#A67C52; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; font-weight:bold; margin-top:5px;">🎵 Proposer un morceau</button></a>', unsafe_allow_html=True)
    
    current_scale_info = ""
    for k in ORDRE_MAPPING_GAMME:
        note = st.session_state.get(f"acc_{k}", "?")
        current_scale_info += f"{k}: {note}%0A"
    mailto_gamme = f"mailto:julienflorin59@gmail.com?subject=Proposition de nouvelle gamme Ngonilélé&body=Bonjour,%0A%0AVoici une proposition de nouvelle gamme :%0A%0A{current_scale_info}%0A%0ANom suggéré : ..."
    st.markdown(f'<a href="{mailto_gamme}" target="_blank"><button style="width:100%; background-color:#A67C52; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; font-weight:bold; margin-top:5px;">📧 Proposer une gamme</button></a>', unsafe_allow_html=True)

    if st.button("🔗 Créer un lien de partage"):
        url_share = f"https://share.streamlit.io/votre_app?code={urllib.parse.quote(st.session_state.code_actuel)}"
        st.code(url_share, language="text")
    
    st.markdown("---")
    with st.expander("📖 Guide & Légende", expanded=False):
        st.markdown("""
        ### 🚀 Démarrage Rapide
        1. **⚙️ Accordage** : Choisissez d'abord votre gamme.
        2. **📝 Éditeur** : Composez votre morceau.
        3. **🔄 Générer** : Créez la partition PDF.
        4. **🎥 Créer** : Créez votre tablature video ou audio !
        """)
    st.markdown("---")
    st.markdown(f'<a href="mailto:julienflorin59@gmail.com?subject=Rapport de Bug - Ngonilélé App" target="_blank"><button style="width:100%; background-color:#800020; color:white; padding:8px; border:none; border-radius:5px; cursor:pointer;">🐞 Reporter un bug</button></a>', unsafe_allow_html=True)

tab_acc, tab_edit, tab_video, tab_audio = st.tabs(["⚙️ Accordage", "📝 Éditeur & Partition", "🎬 Vidéo (Bêta)", "🎧 Audio & Groove"])

with tab_acc:
    st.subheader("Gamme & Accordage")
    st.markdown("##### 1. Choisir une Gamme Préfinie")
    selected_preset_key = st.selectbox("Sélectionner la gamme :", list(GAMMES_PRESETS.keys()), index=0, key="gamme_selector")
    
    col_apply, col_listen = st.columns(2)
    with col_apply:
        if st.button("Appliquer cette gamme", type="primary", use_container_width=True):
            notes_str = GAMMES_PRESETS[selected_preset_key]
            parsed_notes = parse_gamme_string(notes_str)
            if len(parsed_notes) == 12:
                for idx, corde_key in enumerate(ORDRE_MAPPING_GAMME):
                    st.session_state[f"acc_{corde_key}"] = parsed_notes[idx]
                st.toast(f"Gamme appliquée : {selected_preset_key}", icon="✅")
                st.rerun()

    with col_listen:
        if st.button("🎧 Écouter la gamme", use_container_width=True):
            notes_str_preview = GAMMES_PRESETS[selected_preset_key]
            parsed_notes_preview = parse_gamme_string(notes_str_preview)
            if len(parsed_notes_preview) == 12:
                temp_acc_config = {}
                temp_sequence = []
                for idx, corde_key in enumerate(ORDRE_MAPPING_GAMME):
                    note = parsed_notes_preview[idx]
                    temp_acc_config[corde_key] = {'n': note, 'x': 0} 
                    temp_sequence.append({'temps': idx + 1, 'corde': corde_key})
                with st.spinner("Génération de l'aperçu..."):
                    preview_buffer = generer_audio_mix(temp_sequence, 100, temp_acc_config, preview_mode=True)
                    if preview_buffer: st.audio(preview_buffer, format='audio/mp3', autoplay=True)

    st.markdown("---")
    st.markdown("##### Code Couleur des Notes")
    
    # --- INTEGRATION LÉGENDE RESPONSIVE (HTML/CSS) ---
    html_legende = '<div class="legende-pc-container">'
    for note, color in COULEURS_CORDES_REF.items():
        html_legende += f"<div style='text-align:center; line-height:1.2;'><span style='display:inline-block; width:15px; height:15px; background-color:{color}; border-radius:50%;'></span><br><small>{note}</small></div>"
    html_legende += '</div>'
    
    # Version mobile (phrase)
    map_names = {'C':'Do', 'D':'Ré', 'E':'Mi', 'F':'Fa', 'G':'Sol', 'A':'La', 'B':'Si'}
    items_mobile = []
    for note_char, color in COULEURS_CORDES_REF.items():
        nom = map_names.get(note_char, note_char)
        items_mobile.append(f"<span style='color:{color}'>{nom}</span>")
    
    html_legende += f"<div class='legende-mobile-text'>{' - '.join(items_mobile)}</div>"
    
    st.markdown(html_legende, unsafe_allow_html=True)
    # -------------------------------------------------

    st.markdown("<div style='text-align:center; font-size:0.8em; color:gray; margin-top:5px;'>(Les notes dièses # et bémols b gardent la couleur de leur note racine)</div>", unsafe_allow_html=True)
    st.write("")

    st.markdown("---")
    with st.expander("➕ Créer / Personnaliser une gamme", expanded=True):
        col_g, col_sep, col_d = st.columns([1, 0.2, 1]) 
        acc_config = {}
        def on_change_tuning(): pass

        with col_g:
            st.write("**Main Gauche** (G)")
            for i in range(1, 7):
                k = f"{i}G"
                current_val = st.session_state.get(f"acc_{k}", DEF_ACC[k])
                c_code = get_color_for_note(current_val)
                c1, c2 = st.columns([1, 4])
                with c1: st.markdown(f"<div style='margin-top:20px; width:20px; height:20px; background-color:{c_code}; border-radius:50%; border:1px solid #ccc;'></div>", unsafe_allow_html=True)
                with c2:
                    valid_notes = get_valid_notes_for_string(k)
                    if current_val not in valid_notes: valid_notes.insert(0, current_val)
                    val = st.selectbox(f"Corde {k}", valid_notes, index=valid_notes.index(current_val) if current_val in valid_notes else 0, key=f"acc_{k}", on_change=on_change_tuning)
                acc_config[k] = {'x': POSITIONS_X[k], 'n': val}
        
        with col_d:
            st.write("**Main Droite** (D)")
            for i in range(1, 7):
                k = f"{i}D"
                current_val = st.session_state.get(f"acc_{k}", DEF_ACC[k])
                c_code = get_color_for_note(current_val)
                c1, c2 = st.columns([1, 4])
                with c1: st.markdown(f"<div style='margin-top:20px; width:20px; height:20px; background-color:{c_code}; border-radius:50%; border:1px solid #ccc;'></div>", unsafe_allow_html=True)
                with c2:
                    valid_notes = get_valid_notes_for_string(k)
                    if current_val not in valid_notes: valid_notes.insert(0, current_val)
                    val = st.selectbox(f"Corde {k}", valid_notes, index=valid_notes.index(current_val) if current_val in valid_notes else 0, key=f"acc_{k}", on_change=on_change_tuning)
                acc_config[k] = {'x': POSITIONS_X[k], 'n': val}
        
        st.write("")
        if st.button("🎧 Écouter la gamme personnalisée", use_container_width=True):
             temp_sequence = []
             for idx, corde_key in enumerate(ORDRE_MAPPING_GAMME):
                 temp_sequence.append({'temps': idx + 1, 'corde': corde_key})
             with st.spinner("Génération..."):
                 preview_buffer = generer_audio_mix(temp_sequence, 100, acc_config, preview_mode=True)
                 if preview_buffer: st.audio(preview_buffer, format='audio/mp3', autoplay=True)
    st.markdown("---")

with tab_edit:
    titre_partition = st.text_input("Titre de la partition", "Tablature Ngonilélé")
    col_input, col_view = st.columns([1, 1.5])
    with col_input:
        st.subheader("Éditeur")
        subtab_btn, subtab_visu, subtab_seq, subtab_blocs = st.tabs(["🔘 Boutons", "🎨 Visuel", "🎹 Séquenceur", "📦 Structure"])

        def get_suffixe_doigt(corde, mode_key):
            mode = st.session_state[mode_key]
            if mode == "👍 Force Pouce (P)": return " P", " (Pouce)"
            if mode == "👆 Force Index (I)": return " I", " (Index)"
            if corde in ['1G','2G','3G','1D','2D','3D']: return " P", " (Pouce)"
            return " I", " (Index)"

        with subtab_btn:
            c_head, c_doigt = st.columns([1, 2])
            with c_head: st.caption("🎹 **Saisie Rapide**") 
            with c_doigt: st.radio("Doigté :", ["🖐️ Auto", "👍 P", "👆 I"], key="btn_mode_doigt", horizontal=True, label_visibility="collapsed")

            def ajouter_note_boutons(corde):
                suffixe, nom_doigt = get_suffixe_doigt(corde, "btn_mode_doigt")
                ajouter_texte(f"+ {corde}{suffixe}"); st.toast(f"✅ {corde} ajoutée", icon="🎵")
            
            def add_symbol_only(s): st.session_state.code_actuel += f"\n{s} "

            col_g, col_d, col_tools = st.columns([1, 1, 2])
            with col_g:
                st.markdown("**Gauche**", unsafe_allow_html=True)
                for c in ['1G','2G','3G','4G','5G','6G']: st.button(c, key=f"btn_{c}", on_click=ajouter_note_boutons, args=(c,), use_container_width=True)
            with col_d:
                st.markdown("**Droite**", unsafe_allow_html=True)
                for c in ['1D','2D','3D','4D','5D','6D']: st.button(c, key=f"btn_{c}", on_click=ajouter_note_boutons, args=(c,), use_container_width=True)

            with col_tools:
                st.markdown("**Rythme**", unsafe_allow_html=True)
                c_r1, c_r2, c_r3, c_r4 = st.columns(4)
                with c_r1: st.button("♩", on_click=add_symbol_only, args=("+",), use_container_width=True)
                with c_r2: st.button("♪", on_click=add_symbol_only, args=("♪",), use_container_width=True)
                with c_r3: st.button("🎶", on_click=add_symbol_only, args=("🎶",), use_container_width=True)
                with c_r4: st.button("♬", on_click=add_symbol_only, args=("♬",), use_container_width=True)

                st.markdown("**Actions**", unsafe_allow_html=True)
                c_t1, c_t2, c_t3, c_t4 = st.columns(4)
                with c_t1: st.button("=", on_click=ajouter_avec_feedback, args=("=", "Simul."), use_container_width=True)
                with c_t2: st.button("x2", on_click=ajouter_avec_feedback, args=("x2", "x2"), use_container_width=True)
                with c_t3: st.button("S", on_click=ajouter_avec_feedback, args=("+ S", "Silence"), use_container_width=True)
                with c_t4: st.button("⌫", key="btn_undo", on_click=annuler_derniere_ligne, use_container_width=True)

                st.write("") 
                c_s1, c_s2 = st.columns(2)
                with c_s1: st.button("📄 Page", key="btn_page", on_click=ajouter_avec_feedback, args=("+ PAGE", "Page"), use_container_width=True)
                with c_s2: st.button("📝 Texte", key="btn_txt", on_click=ajouter_avec_feedback, args=("+ TXT Msg", "Texte"), use_container_width=True)

                with st.expander("💾 Sauver Bloc", expanded=False):
                    b_name = st.text_input("Nom", key="name_blk_btn", label_visibility="collapsed", placeholder="Nom du bloc")
                    if st.button("Sauver", key="btn_save_btn"):
                        if b_name and st.session_state.code_actuel:
                            st.session_state.stored_blocks[b_name] = st.session_state.code_actuel
                            st.toast(f"Bloc '{b_name}' créé !", icon="📦")

        with subtab_visu:
            afficher_header_style("🎨 Mode Visuel")
            c_doigt, c_rythme = st.columns(2)
            with c_doigt: st.radio("Doigté :", ["🖐️ Auto", "👍 Pouce (P)", "👆 Index (I)"], key="visu_mode_doigt", horizontal=True)
            with c_rythme: st.radio("Rythme par défaut :", ["+", "♪", "🎶", "♬"], key="visu_mode_rythme", horizontal=True, index=0)
            
            def ajouter_note_visuelle(corde):
                suffixe, nom_doigt = get_suffixe_doigt(corde, "visu_mode_doigt"); symbol = st.session_state.visu_mode_rythme
                ajouter_texte(f"{symbol} {corde}{suffixe}"); st.toast(f"✅ {corde} ajoutée ({symbol})", icon="🎵")
            def outil_visuel_wrapper(action, txt_code, msg_toast):
                if action == "ajouter": ajouter_texte(txt_code)
                elif action == "undo": annuler_derniere_ligne()
                st.toast(msg_toast, icon="🛠️")
                
            st.write("") 
            col_head_g, col_head_sep, col_head_d = st.columns([6, 0.2, 6])
            with col_head_g: st.markdown("<div style='text-align:center; font-weight:bold; color:#A67C52; margin-bottom:5px;'>Cordes de gauche</div>", unsafe_allow_html=True)
            with col_head_d: st.markdown("<div style='text-align:center; font-weight:bold; color:#A67C52; margin-bottom:5px;'>Cordes de droite</div>", unsafe_allow_html=True)

            cols_visu = st.columns([1,1,1,1,1,1, 0.2, 1,1,1,1,1,1])
            cordes_gauche = ['6G', '5G', '4G', '3G', '2G', '1G']
            for i, corde in enumerate(cordes_gauche):
                with cols_visu[i]:
                    st.button(corde, key=f"visu_{corde}", on_click=ajouter_note_visuelle, args=(corde,), use_container_width=True)
                    c = COLORS_VISU.get(corde, 'gray')
                    st.markdown(f"<div style='margin:0 auto; width:15px; height:15px; border-radius:50%; background-color:{c};'></div><div style='margin:0 auto; width:2px; height:60px; background-color:{c};'></div>", unsafe_allow_html=True)
            with cols_visu[6]: st.markdown("<div style='height:100px; width:4px; background-color:black; margin:0 auto; border-radius:2px;'></div>", unsafe_allow_html=True)
            cordes_droite = ['1D', '2D', '3D', '4D', '5D', '6D']
            for i, corde in enumerate(cordes_droite):
                with cols_visu[i+7]:
                    st.button(corde, key=f"visu_{corde}", on_click=ajouter_note_visuelle, args=(corde,), use_container_width=True)
                    c = COLORS_VISU.get(corde, 'gray')
                    st.markdown(f"<div style='margin:0 auto; width:15px; height:15px; border-radius:50%; background-color:{c};'></div><div style='margin:0 auto; width:2px; height:60px; background-color:{c};'></div>", unsafe_allow_html=True)
            
            st.write("")
            c_tools = st.columns(6)
            with c_tools[0]: st.button("↩️", key="v_undo", on_click=outil_visuel_wrapper, args=("undo", "", "Annulé !"), use_container_width=True)
            with c_tools[1]: st.button("🟰", key="v_simul", on_click=outil_visuel_wrapper, args=("ajouter", "=", "Simultané"), use_container_width=True)
            with c_tools[2]: st.button("🔁", key="v_x2", on_click=outil_visuel_wrapper, args=("ajouter", "x2", "Doublé"), use_container_width=True)
            with c_tools[3]: st.button("🔇", key="v_sil", on_click=outil_visuel_wrapper, args=("ajouter", "+ S", "Silence"), use_container_width=True)
            with c_tools[4]: st.button("📄", key="v_page", on_click=outil_visuel_wrapper, args=("ajouter", "+ PAGE", "Page"), use_container_width=True)
            with c_tools[5]: st.button("📝", key="v_txt", on_click=outil_visuel_wrapper, args=("ajouter", "+ TXT Message", "Texte"), use_container_width=True)
            afficher_section_sauvegarde_bloc("visu")

        with subtab_seq:
            afficher_header_style("🎹 Séquenceur")
            seq_res = st.radio("Pas de la grille :", ["Noire (+)", "Croche (♪)", "Triolet (🎶)", "Double (♬)"], horizontal=True, key="seq_resolution")
            symbol_map = {"Noire (+)": "+", "Croche (♪)": "♪", "Triolet (🎶)": "🎶", "Double (♬)": "♬"}
            current_seq_symbol = symbol_map[seq_res]
            nb_temps = st.number_input("Nombre de colonnes", min_value=4, max_value=64, value=8, step=4)
            cols = st.columns([0.8] + [1]*12) 
            cordes_list = ['6G', '5G', '4G', '3G', '2G', '1G', '1D', '2D', '3D', '4D', '5D', '6D']
            with cols[0]: st.write("**T**")
            for i, c in enumerate(cordes_list):
                with cols[i+1]: st.markdown(f"**{c}**")
            with st.container(height=400):
                for t in range(nb_temps):
                    cols = st.columns([0.8] + [1]*12)
                    with cols[0]: st.write(""); st.caption(f"**{t+1}**")
                    for i, c in enumerate(cordes_list):
                        key = f"T{t}_{c}"
                        if key not in st.session_state.seq_grid: st.session_state.seq_grid[key] = False
                        with cols[i+1]: st.session_state.seq_grid[key] = st.checkbox(" ", key=key, value=st.session_state.seq_grid[key], label_visibility="collapsed")
            st.write("")
            col_seq_btn, col_seq_reset = st.columns([3, 1])
            with col_seq_btn:
                if st.button("📥 Insérer la séquence", type="primary", use_container_width=True):
                    texte_genere = ""
                    for t in range(nb_temps):
                        notes_activees = []
                        for c in cordes_list:
                            if st.session_state.seq_grid[f"T{t}_{c}"]: notes_activees.append(c)
                        if not notes_activees: texte_genere += f"{current_seq_symbol} S\n"
                        else:
                            premier = True
                            for note in notes_activees:
                                prefix = current_seq_symbol if premier else "= "
                                doigt = " P" if note in ['1G','2G','3G','1D','2D','3D'] else " I"
                                texte_genere += f"{prefix}{note}{doigt}\n"
                                premier = False
                    ajouter_texte(texte_genere); st.toast("Séquence ajoutée !", icon="🎹")
            with col_seq_reset:
                if st.button("🗑️", help="Vide toute la grille"):
                    for k in st.session_state.seq_grid: st.session_state.seq_grid[k] = False
                    st.rerun()
            afficher_section_sauvegarde_bloc("seq")

        with subtab_blocs:
            afficher_header_style("📦 Blocs")
            c_bloc_1, c_bloc_2 = st.columns(2)
            with c_bloc_1:
                new_block_name = st.text_input("Nom (ex: Refrain)", placeholder="Refrain")
                new_block_content = st.text_area("Contenu", height=150, placeholder="+ 4G\n= 1D...")
                if st.button("💾 Créer Bloc"):
                    if new_block_name and new_block_content:
                        st.session_state.stored_blocks[new_block_name] = new_block_content
                        st.toast(f"Bloc '{new_block_name}' sauvegardé !", icon="💾")
            with c_bloc_2:
                st.write("**Blocs existants :**")
                if st.session_state.stored_blocks:
                    for b_name in st.session_state.stored_blocks: st.info(f"📦 {b_name}")
                else: st.caption("Aucun.")
            st.markdown("---")
            st.markdown("#### 🏗️ Assembler")
            structure_input = st.text_input("Structure (ex: Refrain x2 + Couplet)", placeholder="Refrain x2 + Couplet")
            if st.button("🚀 Générer tout", type="primary"):
                if structure_input:
                    full_code = compiler_arrangement(structure_input, st.session_state.stored_blocks)
                    st.session_state.code_actuel = full_code
                    st.session_state.widget_input = full_code
                    st.toast("Partition assemblée !", icon="🚀"); st.rerun()

        st.markdown("---")
        st.caption("💡 Astuce : Vous pouvez agrandir la zone de texte en tirant le coin inférieur droit.")
        st.text_area("Code", height=150, key="widget_input", on_change=mise_a_jour_texte, label_visibility="collapsed")
        
        col_play_btn, col_play_bpm = st.columns([1, 1])
        with col_play_bpm: bpm_preview = st.number_input("BPM", 40, 200, 100)
        with col_play_btn:
            st.write(""); st.write("")
            if st.button("🎧 Écouter"):
                with st.status("🎵 ...", expanded=False) as status:
                    seq_prev = parser_texte(st.session_state.code_actuel)
                    audio_prev = generer_audio_mix(seq_prev, bpm_preview, acc_config)
                    status.update(label="Prêt", state="complete")
                if audio_prev: st.audio(audio_prev, format="audio/mp3")

        with st.expander("Gérer le fichier (Sauvegarde & Projet)"):
            tab_txt, tab_proj = st.tabs(["📄 Texte", "📦 Projet Complet"])
            with tab_txt:
                st.download_button(label="💾 Sauvegarder (.txt)", data=st.session_state.code_actuel, file_name=f"{titre_partition}.txt", mime="text/plain", use_container_width=True)
                uploaded_txt = st.file_uploader("Charger .txt", type="txt", key="load_txt")
                if uploaded_txt:
                    content = io.StringIO(uploaded_txt.getvalue().decode("utf-8")).read()
                    st.session_state.code_actuel = content
                    st.session_state.widget_input = content
                    st.toast("Fichier chargé !", icon="✅"); st.rerun()
            with tab_proj:
                projet_data = { "titre": titre_partition, "code": st.session_state.code_actuel, "blocs": st.session_state.stored_blocks, "version": "1.0" }
                json_str = json.dumps(projet_data, indent=4)
                st.download_button(label="💾 Sauvegarder votre projet", data=json_str, file_name=f"{titre_partition}.ngoni", mime="application/json", use_container_width=True)
                uploaded_proj = st.file_uploader("Charger votre projet sauvegardé", type=["ngoni", "json"], key="load_proj")
                if uploaded_proj:
                    try:
                        data = json.load(uploaded_proj)
                        st.session_state.code_actuel = data.get("code", "")
                        st.session_state.widget_input = data.get("code", "")
                        st.session_state.stored_blocks = data.get("blocs", {})
                        st.toast("Projet restauré (Code + Blocs) !", icon="🎉"); st.rerun()
                    except Exception as e: st.error(f"Erreur : {e}")
       
    with col_view:
        st.subheader("Aperçu")
        view_container = st.container()
        visuals_rendered_this_run = False 
        def afficher_visuels(container):
            with container:
                for item in st.session_state.partition_buffers:
                    if item['type'] == 'legende': st.markdown("#### Page 1 : Légende"); st.pyplot(item['img_ecran'])
                    elif item['type'] == 'page': st.markdown(f"#### Page {item['idx']}"); st.pyplot(item['img_ecran'])
        def afficher_bouton_pdf(container):
            with container:
                 if st.session_state.pdf_buffer:
                    st.markdown("---")
                    st.download_button(label="📕 Télécharger PDF", data=st.session_state.pdf_buffer, file_name=f"{titre_partition}.pdf", mime="application/pdf", type="primary", use_container_width=True)

        if st.button("🔄 Générer", type="primary", use_container_width=True):
            st.session_state.partition_buffers = [] 
            st.session_state.pdf_buffer = None
            DPI_PDF_OPTIMISE = 150 
            styles_ecran = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
            styles_print = {'FOND': 'white', 'TEXTE': 'black', 'PERLE_FOND': 'white', 'LEGENDE_FOND': 'white'}
            options_visuelles = {'use_bg': use_bg_img, 'alpha': bg_alpha}
            
            with st.status("📸 Traitement en cours...", expanded=True) as status:
                prog_bar = st.progress(0, text="Analyse du texte...")
                sequence = parser_texte(st.session_state.code_actuel)
                status.write("📘 Génération de la Légende...")
                fig_leg_ecran = generer_page_1_legende(titre_partition, styles_ecran, mode_white=False)
                if force_white_print:
                    fig_leg_dl = generer_page_1_legende(titre_partition, styles_print, mode_white=True)
                    buf_leg = io.BytesIO(); fig_leg_dl.savefig(buf_leg, format="png", dpi=DPI_PDF_OPTIMISE, facecolor=styles_print['FOND'], bbox_inches='tight'); buf_leg.seek(0); plt.close(fig_leg_dl)
                else:
                    fig_leg_dl = fig_leg_ecran
                    buf_leg = io.BytesIO(); fig_leg_dl.savefig(buf_leg, format="png", dpi=DPI_PDF_OPTIMISE, facecolor=styles_ecran['FOND'], bbox_inches='tight'); buf_leg.seek(0)
                st.session_state.partition_buffers.append({'type':'legende', 'buf': buf_leg, 'img_ecran': fig_leg_ecran})
                pages_data = []; current_page = []
                for n in sequence:
                    if n['corde'] == 'PAGE_BREAK':
                        if current_page: pages_data.append(current_page); current_page = []
                    else: current_page.append(n)
                if current_page: pages_data.append(current_page)
                if not pages_data: st.warning("Vide."); prog_bar.progress(100, text="Terminé (Vide).")
                else:
                    total_steps = len(pages_data)
                    for idx, page in enumerate(pages_data):
                        p_cent = int(((idx) / total_steps) * 90)
                        prog_bar.progress(p_cent + 10, text=f"Dessin de la page {idx+1}/{total_steps}...")
                        fig_ecran = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_ecran, options_visuelles, mode_white=False)
                        if force_white_print:
                            fig_dl = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_print, options_visuelles, mode_white=True)
                            buf = io.BytesIO(); fig_dl.savefig(buf, format="png", dpi=DPI_PDF_OPTIMISE, facecolor=styles_print['FOND'], bbox_inches='tight'); buf.seek(0); plt.close(fig_dl)
                        else:
                            buf = io.BytesIO(); fig_ecran.savefig(buf, format="png", dpi=DPI_PDF_OPTIMISE, facecolor=styles_ecran['FOND'], bbox_inches='tight'); buf.seek(0)
                        st.session_state.partition_buffers.append({'type':'page', 'idx': idx+2, 'buf': buf, 'img_ecran': fig_ecran})
                        plt.close(fig_ecran)
                st.session_state.partition_generated = True
                visuals_rendered_this_run = True
                afficher_visuels(view_container)
                prog_bar.progress(95, text="Assemblage du livret PDF...")
                st.session_state.pdf_buffer = generer_pdf_livret(st.session_state.partition_buffers, titre_partition)
                prog_bar.progress(100, text="Terminé !")
                status.update(label="✅ Génération terminée !", state="complete", expanded=False)
                afficher_bouton_pdf(view_container)

        if st.session_state.partition_generated and not visuals_rendered_this_run:
            afficher_visuels(view_container)
            afficher_bouton_pdf(view_container)

with tab_video:
    st.subheader("Vidéo 🎥")
    st.warning("⚠️ Version Bêta.")
    if not HAS_MOVIEPY or not HAS_PYDUB: st.error("Modules manquants.")
    else:
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            bpm = st.slider("BPM", 30, 200, 60, key="bpm_video")
            seq = parser_texte(st.session_state.code_actuel)
            duree_estimee = ((seq[-1]['tick'] / 12) * (60/bpm)) + 4 if seq else 10 
            st.write(f"Durée : {int(duree_estimee)}s")
        with col_v2:
            if st.button("🎥 Créer Vidéo", type="primary", use_container_width=True):
                with st.status("🎬 Studio de montage...", expanded=True) as status:
                    v_bar = st.progress(0, text="Initialisation...")
                    sequence = parser_texte(st.session_state.code_actuel)
                    v_bar.progress(10, text="Mixage de l'audio...")
                    audio_buffer = generer_audio_mix(sequence, bpm, acc_config)
                    if audio_buffer:
                        v_bar.progress(30, text="Génération de la partition déroulante (HD)...")
                        styles_video = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
                        img_buffer, px, offset = generer_image_longue_calibree(sequence, acc_config, styles_video, dpi=90)
                        if img_buffer:
                            v_bar.progress(50, text="Encodage vidéo en cours...")
                            video_path = creer_video_avec_son_calibree(img_buffer, audio_buffer, duree_estimee, (px, offset), bpm, fps=12)
                            if video_path:
                                st.session_state.video_path = video_path 
                                v_bar.progress(100, text="Terminé !")
                                status.update(label="✅ Vidéo prête !", state="complete", expanded=False)
                            else: v_bar.progress(0, text="Erreur."); status.update(label="❌ Erreur encodage", state="error")
        
        if st.session_state.video_path and os.path.exists(st.session_state.video_path):
            st.video(st.session_state.video_path)
            with open(st.session_state.video_path, "rb") as file:
                st.download_button("⬇️ Télécharger MP4", data=file, file_name="ngoni_video.mp4", mime="video/mp4", type="primary")

with tab_audio:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🎧 Audio")
        if not HAS_PYDUB: st.error("Manque pydub")
        else:
            bpm_audio = st.slider("BPM", 30, 200, 100, key="bpm_audio")
            if st.button("🎵 Créer MP3", type="primary", use_container_width=True):
                seq = parser_texte(st.session_state.code_actuel)
                mp3 = generer_audio_mix(seq, bpm_audio, acc_config)
                if mp3: st.session_state.audio_buffer = mp3
            if st.session_state.audio_buffer:
                st.audio(st.session_state.audio_buffer, format="audio/mp3")
                st.download_button("⬇️ MP3", data=st.session_state.audio_buffer, file_name="ngoni.mp3", mime="audio/mpeg", type="primary")
    with c2:
        st.subheader("🥁 Métronome")
        sig = st.radio("Sig", ["4/4", "3/4"], horizontal=True)
        bpm_m = st.slider("BPM", 30, 200, 80, key="bpm_metro")
        dur = st.slider("Sec", 10, 300, 60)
        if st.button("▶️ Start", type="primary"):
            mb = generer_metronome(bpm_m, dur, sig)
            if mb: st.session_state.metronome_buffer = mb
        if st.session_state.metronome_buffer: st.audio(st.session_state.metronome_buffer, format="audio/mp3")