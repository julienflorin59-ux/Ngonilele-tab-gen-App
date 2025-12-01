import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
from matplotlib.figure import Figure
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import io
import os
import urllib.parse
import numpy as np
from fpdf import FPDF
import random
import re
import gc
import glob
import json
import tempfile

# ==============================================================================
# ⚙️ CONFIGURATION & CHEMINS
# ==============================================================================
st.set_page_config(
    page_title="Générateur Tablature Ngonilélé",
    layout="wide",
    page_icon="ico_ngonilele.png",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 📱 OPTIMISATION MOBILE (CSS HACK)
# ==============================================================================
st.markdown("""
<style>
    /* Sur mobile uniquement (écrans < 640px) */
    @media (max-width: 640px) {
        /* 1. Réduire les marges et la taille du texte des boutons */
        .stButton button {
            padding: 0px 2px !important;
            font-size: 0.8rem !important;
            min-height: 40px !important;
            white-space: nowrap !important;
        }
        
        /* 2. Forcer l'affichage côte à côte pour les groupes de 2 colonnes */
        div[data-testid="column"] {
            width: calc(50% - 0.5rem) !important;
            flex: 1 1 calc(50% - 0.5rem) !important;
            min-width: calc(50% - 0.5rem) !important;
        }
        
        /* 3. Exception pour le Séquenceur et le Visuel (scroll horizontal) */
        div[data-testid="stHorizontalBlock"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTES & RESOURCES ---
CHEMIN_POLICE = 'ML.ttf'
CHEMIN_IMAGE_FOND = 'texture_ngonilele.png'
CHEMIN_ICON_POUCE = 'icon_pouce.png'
CHEMIN_ICON_INDEX = 'icon_index.png'
CHEMIN_ICON_POUCE_BLANC = 'icon_pouce_blanc.png'
CHEMIN_ICON_INDEX_BLANC = 'icon_index_blanc.png'
CHEMIN_LOGO_APP = 'ico_ngonilele.png'
DOSSIER_SAMPLES = 'samples'

# --- COULEURS & CONSTANTES LOGIQUES ---
POSITIONS_X = {'1G': -1, '2G': -2, '3G': -3, '4G': -4, '5G': -5, '6G': -6, '1D': 1, '2D': 2, '3D': 3, '4D': 4, '5D': 5, '6D': 6}
COULEURS_CORDES_REF = {'C': '#FF0000', 'D': '#FF8C00', 'E': '#FFD700', 'F': '#32CD32', 'G': '#00BFFF', 'A': '#00008B', 'B': '#9400D3'}
# Couleurs pour l'interface visuelle (Boutons)
COLORS_VISU = {'6G':'#00BFFF','5G':'#FF4B4B','4G':'#00008B','3G':'#FFD700','2G':'#FF4B4B','1G':'#00BFFF','1D':'#32CD32','2D':'#00008B','3D':'#FFA500','4D':'#00BFFF','5D':'#9400D3','6D':'#FFD700'}

TRADUCTION_NOTES = {'C':'do', 'D':'ré', 'E':'mi', 'F':'fa', 'G':'sol', 'A':'la', 'B':'si'}
AUTOMATIC_FINGERING = {'1G':'P','2G':'P','3G':'P','1D':'P','2D':'P','3D':'P','4G':'I','5G':'I','6G':'I','4D':'I','5D':'I','6D':'I'}
NOTES_GAMME = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
DEF_ACC = {'1G':'G','2G':'C','3G':'E','4G':'A','5G':'C','6G':'G','1D':'F','2D':'A','3D':'D','4D':'G','5D':'B','6D':'E'}

# ==============================================================================
# 🚀 FONCTIONS UTILES (CACHE & SYSTEME)
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
    """Fonction utilitaire pour afficher les titres stylisés"""
    st.markdown(f"""
    <div style="background-color: #d4b08c; padding: 5px 10px; border-radius: 5px; border-left: 5px solid #A67C52; color: black; margin-bottom: 10px;">
        <strong>{titre}</strong>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 📦 GESTION DE LA PERSISTANCE
# ==============================================================================
if 'partition_buffers' not in st.session_state: st.session_state.partition_buffers = []
if 'partition_generated' not in st.session_state: st.session_state.partition_generated = False
if 'video_path' not in st.session_state: st.session_state.video_path = None
if 'audio_buffer' not in st.session_state: st.session_state.audio_buffer = None
if 'metronome_buffer' not in st.session_state: st.session_state.metronome_buffer = None
if 'code_actuel' not in st.session_state: st.session_state.code_actuel = ""
if 'pdf_buffer' not in st.session_state: st.session_state.pdf_buffer = None
if 'seq_grid' not in st.session_state: st.session_state.seq_grid = {}
if 'stored_blocks' not in st.session_state: st.session_state.stored_blocks = {}

# ==============================================================================
# 🎵 BANQUE DE DONNÉES
# ==============================================================================
BANQUE_TABLATURES = {
    "--- Nouveau / Vide ---": "",
    "Exercice Débutant 1 : Montée et descente de Gamme": """
1   1D
+   S
+   1G
+   S
+   2D
+   S
+   2G
+   S
+   3D
+   S
+   3G
+   S
+   4D
+   S
+   4G
+   S
+   5D
+   S
+   5G
+   S
+   6D
+   S
+   6G
+   S
+   TXT  DESCENTE
+   6G
+   S
+   6D
+   S
+   5G
+   S
+   5D
+   S
+   4G
+   S
+   4D
+   S
+   3G
+   S
+   3D
+   S
+   2G
+   S
+   2D
+   S
+   1G
+   S
+   1D
""",
    "Exercice Débutant 2 : Montée et descente de Gamme en triolets": """
1   1D
+   1G
+   2D
+   S
+   1G
+   2D
+   2G
+   S
+   2D
+   2G
+   3D
+   S
+   2G
+   3D
+   3G
+   S
+   3D
+   3G
+   4D
+   S
+   3G
+   4D
+   4G
+   S
+   4D
+   4G
+   5D
+   S
+   4G
+   5D
+   5G
+   S
+   5D
+   5G
+   6D
+   S
+   5G
+   6D
+   6G
+   S
+   TXT  DESCENTE
+   6G
+   6D
+   5G
+   S
+   6D
+   5G
+   5D
+   S
+   5G
+   5D
+   4G
+   S
+   5D
+   4G
+   4D
+   S
+   4G
+   4D
+   3G
+   S
+   4D
+   3G
+   3D
+   S
+   3G
+   3D
+   2G
+   S
+   3D
+   2G
+   2D
+   S
+   2G
+   2D
+   1G
+   S
+   2D
+   1G
+   1D
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

# En-tête de l'application
# --- AJOUT AVERTISSEMENT ---
st.warning("🖥️ **Optimisé pour Ordinateur :** Ce site est conçu pour les grands écrans. L'utilisation sur téléphone mobile est déconseillée pour une expérience optimale.", icon="⚠️")
# ---------------------------

st.markdown("""
<div style="background-color: #d4b08c; color: black; padding: 10px; border-radius: 5px; border-left: 5px solid #A67C52; margin-bottom: 10px;">
    <strong>👈 Ouvrez le menu latéral</strong> (flèche en haut à gauche) pour : Charger un morceau, lire le Guide complet, ou 🐞 Signaler un bug !
</div>
""", unsafe_allow_html=True)

col_logo, col_titre = st.columns([1, 5])
with col_logo:
    if os.path.exists(CHEMIN_LOGO_APP): st.image(CHEMIN_LOGO_APP, width=100)
    else: st.header("🪕")
with col_titre:
    st.title("Générateur de Tablature Ngonilélé")
    st.markdown("Composez, Écoutez et Exportez.")

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
    except:
        HAS_MOVIEPY = False

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
            for _ in range(repeat_count):
                full_text += content + "\n"
        else:
            full_text += f"+ TXT [Bloc '{block_name}' introuvable]\n"
    return full_text

# ==============================================================================
# 🎹 MOTEUR AUDIO (OPTIMISÉ)
# ==============================================================================
def get_note_freq(note_name):
    base_freqs = {'C': 261.63, 'D': 293.66, 'E': 329.63, 'F': 349.23, 'G': 392.00, 'A': 440.00, 'B': 493.88}
    return base_freqs.get(note_name, 440.0)

@st.cache_data(show_spinner=False)
def generer_audio_mix(sequence, bpm, acc_config):
    if not HAS_PYDUB: return None
    if not sequence: return None
    samples_loaded = {}
    cordes_utilisees = set([n['corde'] for n in sequence if n['corde'] in POSITIONS_X])
    for corde in cordes_utilisees:
        loaded = False
        if os.path.exists(DOSSIER_SAMPLES):
            chemin = os.path.join(DOSSIER_SAMPLES, f"{corde}.mp3")
            if os.path.exists(chemin): samples_loaded[corde] = AudioSegment.from_mp3(chemin); loaded = True
            else:
                chemin_min = os.path.join(DOSSIER_SAMPLES, f"{corde.lower()}.mp3")
                if os.path.exists(chemin_min): samples_loaded[corde] = AudioSegment.from_mp3(chemin_min); loaded = True
        if not loaded:
            note_name = acc_config.get(corde, {'n':'C'})['n']
            freq = get_note_freq(note_name)
            tone = Sine(freq).to_audio_segment(duration=600).fade_out(400)
            samples_loaded[corde] = tone - 5 
    if not samples_loaded: return None
    ms_par_temps = 60000 / bpm
    dernier_t = sequence[-1]['temps']
    duree_totale_ms = int((dernier_t + 4) * ms_par_temps) 
    if duree_totale_ms < 1000: duree_totale_ms = 1000
    mix = AudioSegment.silent(duration=duree_totale_ms)
    for n in sequence:
        corde = n['corde']
        if corde in samples_loaded:
            t = n['temps']; pos_ms = int((t - 1) * ms_par_temps)
            if pos_ms < 0: pos_ms = 0
            mix = mix.overlay(samples_loaded[corde], position=pos_ms)
    
    # OPTIMISATION AUDIO: Export en bitrate réduit pour chargement rapide
    buffer = io.BytesIO(); mix.export(buffer, format="mp3", bitrate="64k"); buffer.seek(0)
    return buffer

# --- OPTIMISATION DU METRONOME (CACHE + BITRATE REDUIT) ---
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
    
    # OPTIMISATION AUDIO: Export en 32k pour vitesse maximale
    buffer = io.BytesIO()
    metronome_track.export(buffer, format="mp3", bitrate="32k", parameters=["-preset", "ultrafast"])
    buffer.seek(0)
    return buffer

# ==============================================================================
# 🎨 MOTEUR AFFICHAGE OPTIMISÉ (AVEC FIGURE)
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
    
    offsets = [-0.7, 0, 0.7]; 
    for i, off in enumerate(offsets): c = plt.Circle((x_icon_center + off, y_row3), 0.25, facecolor=c_bulle, edgecolor=c_txt, lw=2); ax.add_patch(c); ax.text(x_icon_center + off, y_row3, str(i+1), ha='center', va='center', fontsize=12, fontweight='bold', color=c_txt)
    ax.text(x_text_align, y_row3, "= Ordre de jeu", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    x_simul_end = x_icon_center + 1.4; ax.plot([x_icon_center - 0.7, x_simul_end - 0.7], [y_row4, y_row4], color=c_txt, lw=3, zorder=1)
    ax.add_patch(plt.Circle((x_icon_center - 0.7, y_row4), 0.25, facecolor=c_bulle, edgecolor=c_txt, lw=2, zorder=2)); ax.add_patch(plt.Circle((x_simul_end - 0.7, y_row4), 0.25, facecolor=c_bulle, edgecolor=c_txt, lw=2, zorder=2))
    ax.text(x_text_align, y_row4, "= Notes simultanées", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    x_droite = 1.5; y_text_top = y_pos - 1.2; line_height = 0.45
    ax.text(x_droite, y_text_top, "1G = 1ère corde à gauche", ha='left', va='center', fontproperties=prop_legende, color=c_txt); ax.text(x_droite, y_text_top - line_height, "2G = 2ème corde à gauche", ha='left', va='center', fontproperties=prop_legende, color=c_txt); ax.text(x_droite, y_text_top - line_height*2, "1D = 1ère corde à droite", ha='left', va='center', fontproperties=prop_legende, color=c_txt); ax.text(x_droite, y_text_top - line_height*3, "2D = 2ème corde à droite", ha='left', va='center', fontproperties=prop_legende, color=c_txt); ax.text(x_droite, y_text_top - line_height*4, "(Etc...)", ha='left', va='center', fontproperties=prop_legende, color=c_txt)

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
    t_min = notes_page[0]['temps']; t_max = notes_page[-1]['temps']
    lignes_sur_page = t_max - t_min + 1
    hauteur_fig = max(6, (lignes_sur_page * 0.75) + 6)
    fig = Figure(figsize=(16, hauteur_fig), facecolor=c_fond)
    ax = fig.subplots()
    ax.set_facecolor(c_fond)
    y_top = 2.5; y_bot = - (t_max - t_min) - 1.5; y_top_cordes = y_top
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
        x = props['x']; note = props['n']; c = COULEURS_CORDES_REF.get(note, '#000000')
        ax.text(x, y_top_cordes + 1.3, code, ha='center', color='gray', fontproperties=prop_numero)
        ax.text(x, y_top_cordes + 0.7, note, ha='center', color=c, fontproperties=prop_note_us)
        ax.text(x, y_top_cordes + 0.1, TRADUCTION_NOTES.get(note, '?'), ha='center', color=c, fontproperties=prop_note_eu)
        ax.vlines(x, y_bot, y_top_cordes, colors=c, lw=3, zorder=1)
    
    for t in range(t_min, t_max + 1):
        y = -(t - t_min)
        ax.axhline(y=y, color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)

    map_labels = {}; last_sep = t_min - 1; sorted_notes = sorted(notes_page, key=lambda x: x['temps'])
    processed_t = set()
    for n in sorted_notes:
        t = n['temps']
        if n['corde'] in ['SEPARATOR', 'TEXTE']: last_sep = t
        elif t not in processed_t: map_labels[t] = str(t - last_sep); processed_t.add(t)
            
    notes_par_temps_relatif = {}; rayon = 0.30
    for n in notes_page:
        t_absolu = n['temps']; y = -(t_absolu - t_min)
        if y not in notes_par_temps_relatif: notes_par_temps_relatif[y] = []
        notes_par_temps_relatif[y].append(n); code = n['corde']
        if code == 'TEXTE': 
            bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt, lw=2)
            ax.text(0, y, n.get('message',''), ha='center', va='center', color='black', fontproperties=prop_annotation, bbox=bbox, zorder=10)
        elif code == 'SEPARATOR': 
            ax.axhline(y, color=c_txt, lw=3, zorder=4)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']; c = COULEURS_CORDES_REF.get(props['n'], '#000000')
            ax.add_patch(plt.Circle((x, y), rayon, color=c_perle, zorder=3))
            ax.add_patch(plt.Circle((x, y), rayon, fill=False, edgecolor=c, lw=3, zorder=4))
            ax.text(x, y, map_labels.get(t_absolu, ""), ha='center', va='center', color='black', fontproperties=prop_standard, zorder=6)
            if 'doigt' in n:
                doigt = n['doigt']; current_img = img_index if doigt == 'I' else img_pouce
                if current_img is not None:
                    try: ab = AnnotationBbox(OffsetImage(current_img, zoom=0.045), (x - 0.70, y + 0.1), frameon=False, zorder=8); ax.add_artist(ab)
                    except: pass
                else: ax.text(x - 0.70, y, doigt, ha='center', va='center', color=c_txt, fontproperties=prop_standard, zorder=7)
                    
    for y, group in notes_par_temps_relatif.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)
            
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(y_bot, y_top + 5); ax.axis('off')
    return fig

def generer_image_longue_calibree(sequence, config_acc, styles, dpi=72): # DPI optimisé pour la vidéo
    if not sequence: return None, 0, 0
    t_min = sequence[0]['temps']; t_max = sequence[-1]['temps']
    y_max_header = 3.0; y_min_footer = -(t_max - t_min) - 2.0; hauteur_unites = y_max_header - y_min_footer
    FIG_WIDTH = 16; FIG_HEIGHT = hauteur_unites * 0.8; DPI = dpi
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
        x = props['x']; note = props['n']; c = COULEURS_CORDES_REF.get(note, '#000000')
        ax.text(x, y_top + 1.3, code, ha='center', color='gray', fontproperties=prop_numero); ax.text(x, y_top + 0.7, note, ha='center', color=c, fontproperties=prop_note_us); ax.text(x, y_top + 0.1, TRADUCTION_NOTES.get(note, '?'), ha='center', color=c, fontproperties=prop_note_eu); ax.vlines(x, y_bot, y_top, colors=c, lw=3, zorder=1)
    for t in range(t_min, t_max + 1):
        y = -(t - t_min)
        ax.axhline(y=y, color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)
    map_labels = {}; last_sep = t_min - 1; processed_t = set()
    for n in sequence:
        t = n['temps']; 
        if n['corde'] in ['SEPARATOR', 'TEXTE']: last_sep = t
        elif t not in processed_t: map_labels[t] = str(t - last_sep); processed_t.add(t)
    notes_par_temps = {}; rayon = 0.30
    for n in sequence:
        if n['corde'] == 'PAGE_BREAK': continue 
        t_absolu = n['temps']; y = -(t_absolu - t_min)
        if y not in notes_par_temps: notes_par_temps[y] = []
        notes_par_temps[y].append(n); code = n['corde']
        if code == 'TEXTE': bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt, lw=2); ax.text(0, y, n.get('message',''), ha='center', va='center', color='black', fontproperties=prop_annotation, bbox=bbox, zorder=10)
        elif code == 'SEPARATOR': ax.axhline(y, color=c_txt, lw=3, zorder=4)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']; c = COULEURS_CORDES_REF.get(props['n'], '#000000')
            ax.add_patch(plt.Circle((x, y), rayon, color=c_perle, zorder=3)); ax.add_patch(plt.Circle((x, y), rayon, fill=False, edgecolor=c, lw=3, zorder=4))
            ax.text(x, y, map_labels.get(t_absolu, ""), ha='center', va='center', color='black', fontproperties=prop_standard, zorder=6)
            if 'doigt' in n:
                doigt = n['doigt']; current_img = img_index if doigt == 'I' else img_pouce
                if current_img is not None:
                    try: ab = AnnotationBbox(OffsetImage(current_img, zoom=0.045), (x - 0.70, y + 0.1), frameon=False, zorder=8); ax.add_artist(ab)
                    except: pass
                else: ax.text(x - 0.70, y, doigt, ha='center', va='center', color=c_txt, fontproperties=prop_standard, zorder=7)
    for y, group in notes_par_temps.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]; 
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)
    ax.axis('off')
    px_y_t0 = ax.transData.transform((0, 0))[1]
    px_y_t1 = ax.transData.transform((0, -1))[1]
    total_h_px = FIG_HEIGHT * DPI
    pixels_par_temps = px_y_t0 - px_y_t1
    offset_premiere_note_px = total_h_px - px_y_t0
    buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=DPI, facecolor=c_fond, bbox_inches=None)
    buf.seek(0)
    return buf, pixels_par_temps, offset_premiere_note_px

# ==============================================================================
# 🎬 MODIFICATION MAJEURE ICI : UTILISATION DE TEMPFILE
# ==============================================================================
def creer_video_avec_son_calibree(image_buffer, audio_buffer, duration_sec, metrics, bpm, fps=15): # FPS mis à 15 (anciennement 10)
    pixels_par_temps, offset_premiere_note_px = metrics
    
    # Création de fichiers temporaires sécurisés
    # On utilise delete=False car MoviePy a besoin d'accéder au chemin du fichier
    # On s'assure de les supprimer dans le bloc 'finally'
    
    temp_img_path = None
    temp_audio_path = None
    output_filename = None
    
    try:
        # 1. Écrire l'image dans un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f_img:
            f_img.write(image_buffer.getbuffer())
            temp_img_path = f_img.name

        # 2. Écrire l'audio dans un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f_audio:
            f_audio.write(audio_buffer.getbuffer())
            temp_audio_path = f_audio.name
            
        # 3. Préparer le fichier de sortie
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f_vid:
            output_filename = f_vid.name

        # 4. Traitement MoviePy
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
        
        # --- MODIF: Ajout de yuv420p pour lecture immédiate ---
        final.write_videofile(output_filename, codec='libx264', audio_codec='aac', preset='ultrafast', ffmpeg_params=['-pix_fmt', 'yuv420p'], logger=None)
        
        # Fermeture des clips
        audio_clip.close(); video_visual.close(); clip_img.close(); final.close()
        return output_filename

    except Exception as e:
        st.error(f"Erreur vidéo : {e}")
        return None
    finally:
        # Nettoyage sécurisé : on supprime les fichiers sources, mais PAS le fichier de sortie 
        # (car Streamlit en a besoin pour l'afficher juste après)
        if temp_img_path and os.path.exists(temp_img_path): os.remove(temp_img_path)
        if temp_audio_path and os.path.exists(temp_audio_path): os.remove(temp_audio_path)
        # Note: Le fichier vidéo final sera supprimé au prochain rechargement via la fonction charger_morceau() qui clean glob("ngoni_video_*.mp4")
        # Ou par le nettoyage OS automatique du dossier temp

def generer_pdf_livret(buffers, titre):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    for item in buffers:
        pdf.add_page()
        temp_img = f"temp_pdf_{item['type']}_{item.get('idx', 0)}_{random.randint(0,1000)}.png"
        
        # Note: Les buffers contiennent déjà l'image PNG encodée 
        item['buf'].seek(0) # Assurer que la lecture commence au début
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

def charger_morceau():
    choix = st.session_state.selection_banque
    if choix in BANQUE_TABLATURES:
        nouveau = BANQUE_TABLATURES[choix].strip()
        st.session_state.code_actuel = nouveau
        st.session_state.widget_input = nouveau
        st.session_state.partition_generated = False
        st.session_state.video_path = None
        st.session_state.audio_buffer = None
        st.session_state.pdf_buffer = None
        st.session_state.seq_grid = {}
        
        plt.close('all')
        gc.collect()
        for temp_file in glob.glob("temp_*"):
            try: os.remove(temp_file)
            except: pass
        # Nettoyage fichiers vidéos temporaires systèmes si besoin (optionnel)

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

with st.sidebar:
    st.header("🎚️ Réglages")
    st.markdown("### 📚 Banque de Morceaux")
    st.selectbox("Choisir un morceau :", options=list(BANQUE_TABLATURES.keys()), key='selection_banque', on_change=charger_morceau)
    st.caption("⚠️ Remplacera le texte actuel.")
    st.markdown("---")
    with st.expander("🎨 Apparence", expanded=False):
        bg_color = "#e5c4a3"
        use_bg_img = True
        bg_alpha = 0.2
        st.markdown("---")
        force_white_print = st.checkbox("🖨️ Fond blanc pour impression", value=True)
    st.markdown("---")
    st.markdown("### 🤝 Contribuer")
    st.markdown(f'<a href="mailto:julienflorin59@gmail.com" target="_blank"><button style="width:100%; background-color:#A67C52; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">📧 Envoyer ma partition</button></a>', unsafe_allow_html=True)
    if st.button("🔗 Créer un lien de partage"):
        url_share = f"https://share.streamlit.io/votre_app?code={urllib.parse.quote(st.session_state.code_actuel)}"
        st.code(url_share, language="text")
    
    st.markdown("---")
    with st.expander("📖 Guide & Légende", expanded=False):
        st.markdown("""
        ### 📖 Guide Rapide
        **1. Éditeur :**
        * **Boutons** : Cliquez sur 1G, 2D etc.
        * **Visuel** : Cliquez sur les cordes.
        * **Séquenceur** : Cochez les cases.
        * *Astuce Mobile : Scrollez horizontalement si les onglets dépassent.*

        **2. Syntaxe :**
        * `+` : Nouvelle note (avance d'un temps).
        * `=` : Note simultanée.
        * `S` : Silence (Important pour le rythme).
        """)
    
    st.markdown("---")
    st.markdown(f'<a href="mailto:julienflorin59@gmail.com?subject=Rapport de Bug - Ngonilélé App" target="_blank"><button style="width:100%; background-color:#800020; color:white; padding:8px; border:none; border-radius:5px; cursor:pointer;">🐞 Reporter un bug</button></a>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📝 Éditeur & Partition", "⚙️ Accordage", "🎬 Vidéo (Bêta)", "🎧 Audio & Groove"])

with tab2:
    st.subheader("Configuration des cordes")
    col_g, col_d = st.columns(2)
    acc_config = {}
    with col_g:
        st.write("**Main Gauche**")
        for i in range(1, 7):
            k = f"{i}G"; val = st.selectbox(f"Corde {k}", NOTES_GAMME, index=NOTES_GAMME.index(DEF_ACC[k]), key=k)
            acc_config[k] = {'x': POSITIONS_X[k], 'n': val}
    with col_d:
        st.write("**Main Droite**")
        for i in range(1, 7):
            k = f"{i}D"; val = st.selectbox(f"Corde {k}", NOTES_GAMME, index=NOTES_GAMME.index(DEF_ACC[k]), key=k)
            acc_config[k] = {'x': POSITIONS_X[k], 'n': val}

with tab1:
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
            afficher_header_style("⌨️ Mode Rapide")
            st.radio("Doigté :", ["🖐️ Auto", "👍 Pouce (P)", "👆 Index (I)"], key="btn_mode_doigt", horizontal=True)
            
            def ajouter_note_boutons(corde):
                suffixe, nom_doigt = get_suffixe_doigt(corde, "btn_mode_doigt")
                ajouter_texte(f"+ {corde}{suffixe}")
                st.toast(f"✅ {corde} ajoutée", icon="🎵")
            
            st.markdown("""<style>div[data-testid="column"] .stButton button { width: 100%; margin: 0; }</style>""", unsafe_allow_html=True)
            
            c_notes = st.columns(2)
            with c_notes[0]: 
                st.caption("Gauche")
                for c in ['1G','2G','3G','4G','5G','6G']: st.button(c, key=f"btn_{c}", on_click=ajouter_note_boutons, args=(c,), use_container_width=True)
            with c_notes[1]:
                st.caption("Droite")
                for c in ['1D','2D','3D','4D','5D','6D']: st.button(c, key=f"btn_{c}", on_click=ajouter_note_boutons, args=(c,), use_container_width=True)
            
            st.write("") # Espaceur
            
            c_tools = st.columns(2)
            with c_tools[0]:
                st.caption("Outils")
                st.button("↩️ Effacer", key="btn_undo", on_click=annuler_derniere_ligne, use_container_width=True)
                st.button("🟰 Simultané", key="btn_simul", on_click=ajouter_avec_feedback, args=("=", "Simultané"), use_container_width=True)
                st.button("🔁 Doubler (x2)", key="btn_x2", on_click=ajouter_avec_feedback, args=("x2", "Doublé"), use_container_width=True)
                st.button("🔇 Silence", key="btn_silence", on_click=ajouter_avec_feedback, args=("+ S", "Silence"), use_container_width=True)
            with c_tools[1]:
                st.caption("Structure")
                st.button("📄 Page", key="btn_page", on_click=ajouter_avec_feedback, args=("+ PAGE", "Page"), use_container_width=True)
                st.button("📝 Texte", key="btn_txt", on_click=ajouter_avec_feedback, args=("+ TXT Msg", "Texte"), use_container_width=True)
            
            st.markdown("---")
            with st.expander("📦 Sauvegarder ce motif en Bloc"):
                b_name_btn = st.text_input("Nom", key="name_blk_btn")
                if st.button("Sauvegarder", key="btn_save_btn"):
                    if b_name_btn and st.session_state.code_actuel:
                        st.session_state.stored_blocks[b_name_btn] = st.session_state.code_actuel
                        st.toast(f"Bloc '{b_name_btn}' créé !", icon="📦")

        with subtab_visu:
            # Note: Le CSS en Partie 1 (overflow-x: auto) gère l'affichage mobile ici
            afficher_header_style("🎨 Mode Visuel")
            st.radio("Doigté :", ["🖐️ Auto", "👍 Pouce (P)", "👆 Index (I)"], key="visu_mode_doigt", horizontal=True)
            def ajouter_note_visuelle(corde):
                suffixe, nom_doigt = get_suffixe_doigt(corde, "visu_mode_doigt")
                ajouter_texte(f"+ {corde}{suffixe}")
                st.toast(f"✅ {corde} ajoutée", icon="🎵")
            def outil_visuel_wrapper(action, txt_code, msg_toast):
                if action == "ajouter": ajouter_texte(txt_code)
                elif action == "undo": annuler_derniere_ligne()
                st.toast(msg_toast, icon="🛠️")
            
            st.write("G ________________________________ D")
            cols_visu = st.columns([1,1,1,1,1,1, 0.2, 1,1,1,1,1,1])
            cordes_gauche = ['6G', '5G', '4G', '3G', '2G', '1G']
            for i, corde in enumerate(cordes_gauche):
                with cols_visu[i]:
                    st.button(corde, key=f"visu_{corde}", on_click=ajouter_note_visuelle, args=(corde,), use_container_width=True)
                    c = COLORS_VISU.get(corde, 'gray')
                    st.markdown(f"<div style='margin:0 auto; width:15px; height:15px; border-radius:50%; background-color:{c};'></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='margin:0 auto; width:2px; height:60px; background-color:{c};'></div>", unsafe_allow_html=True)
            with cols_visu[6]:
                st.markdown("<div style='height:100px; width:4px; background-color:black; margin:0 auto; border-radius:2px;'></div>", unsafe_allow_html=True)
            cordes_droite = ['1D', '2D', '3D', '4D', '5D', '6D']
            for i, corde in enumerate(cordes_droite):
                with cols_visu[i+7]:
                    st.button(corde, key=f"visu_{corde}", on_click=ajouter_note_visuelle, args=(corde,), use_container_width=True)
                    c = COLORS_VISU.get(corde, 'gray')
                    st.markdown(f"<div style='margin:0 auto; width:15px; height:15px; border-radius:50%; background-color:{c};'></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='margin:0 auto; width:2px; height:60px; background-color:{c};'></div>", unsafe_allow_html=True)
            st.write("")
            c_tools = st.columns(6)
            # Outils Visuels
            with c_tools[0]: st.button("↩️", key="v_undo", on_click=outil_visuel_wrapper, args=("undo", "", "Annulé !"), use_container_width=True)
            with c_tools[1]: st.button("🟰", key="v_simul", on_click=outil_visuel_wrapper, args=("ajouter", "=", "Simultané"), use_container_width=True)
            with c_tools[2]: st.button("🔁", key="v_x2", on_click=outil_visuel_wrapper, args=("ajouter", "x2", "Doublé"), use_container_width=True)
            with c_tools[3]: st.button("🔇", key="v_sil", on_click=outil_visuel_wrapper, args=("ajouter", "+ S", "Silence"), use_container_width=True)
            with c_tools[4]: st.button("📄", key="v_page", on_click=outil_visuel_wrapper, args=("ajouter", "+ PAGE", "Page"), use_container_width=True)
            with c_tools[5]: st.button("📝", key="v_txt", on_click=outil_visuel_wrapper, args=("ajouter", "+ TXT Message", "Texte"), use_container_width=True)

        with subtab_seq:
            # Note: Le CSS en Partie 1 (overflow-x: auto) gère l'affichage mobile ici
            afficher_header_style("🎹 Séquenceur")
            nb_temps = st.number_input("Nombre de temps", min_value=4, max_value=64, value=8, step=4)
            cols = st.columns([0.8] + [1]*12) 
            cordes_list = ['6G', '5G', '4G', '3G', '2G', '1G', '1D', '2D', '3D', '4D', '5D', '6D']
            with cols[0]: st.write("**T**")
            for i, c in enumerate(cordes_list):
                with cols[i+1]: st.markdown(f"**{c}**")
            with st.container(height=400):
                for t in range(nb_temps):
                    cols = st.columns([0.8] + [1]*12)
                    with cols[0]: 
                        st.write(""); st.caption(f"**{t+1}**")
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
                        if not notes_activees: texte_genere += "+ S\n"
                        else:
                            premier = True
                            for note in notes_activees:
                                prefix = "+ " if premier else "= "
                                doigt = " P" if note in ['1G','2G','3G','1D','2D','3D'] else " I"
                                texte_genere += f"{prefix}{note}{doigt}\n"
                                premier = False
                    ajouter_texte(texte_genere)
                    st.toast("Séquence ajoutée !", icon="🎹")
            with col_seq_reset:
                if st.button("🗑️"):
                    for k in st.session_state.seq_grid: st.session_state.seq_grid[k] = False
                    st.rerun()

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
                    for b_name in st.session_state.stored_blocks:
                        st.info(f"📦 {b_name}")
                else:
                    st.caption("Aucun.")

            st.markdown("---")
            st.markdown("#### 🏗️ Assembler")
            structure_input = st.text_input("Structure (ex: Refrain x2 + Couplet)", placeholder="Refrain x2 + Couplet")
            
            if st.button("🚀 Générer tout", type="primary"):
                if structure_input:
                    full_code = compiler_arrangement(structure_input, st.session_state.stored_blocks)
                    st.session_state.code_actuel = full_code
                    st.session_state.widget_input = full_code
                    st.toast("Partition assemblée !", icon="🚀")
                    st.rerun()

        st.markdown("---")
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

        # --- GESTION FICHIER & PROJET (JSON) ---
        with st.expander("Gérer le fichier (Sauvegarde & Projet)"):
            tab_txt, tab_proj = st.tabs(["📄 Texte", "📦 Projet Complet"])
            
            with tab_txt:
                st.download_button(label="💾 Sauvegarder (.txt)", data=st.session_state.code_actuel, file_name=f"{titre_partition}.txt", mime="text/plain")
                uploaded_txt = st.file_uploader("📂 Charger (.txt)", type="txt", key="load_txt")
                if uploaded_txt:
                    content = io.StringIO(uploaded_txt.getvalue().decode("utf-8")).read()
                    st.session_state.code_actuel = content
                    st.session_state.widget_input = content
                    st.toast("Fichier chargé !", icon="✅")
                    st.rerun()

            with tab_proj:
                # 📦 FONCTIONNALITÉ DEMANDÉE : EXPORT CONFIGURATION (CODE + BLOCS)
                projet_data = {
                    "titre": titre_partition,
                    "code": st.session_state.code_actuel,
                    "blocs": st.session_state.stored_blocks, # Sauvegarde les blocs créés par l'utilisateur
                    "version": "1.0"
                }
                json_str = json.dumps(projet_data, indent=4)
                
                st.download_button(
                    label="💾 Sauvegarder Projet (.ngoni)", 
                    data=json_str, 
                    file_name=f"{titre_partition}.ngoni",
                    mime="application/json"
                )
                
                uploaded_proj = st.file_uploader("📂 Charger Projet (.ngoni)", type=["ngoni", "json"], key="load_proj")
                if uploaded_proj:
                    try:
                        data = json.load(uploaded_proj)
                        st.session_state.code_actuel = data.get("code", "")
                        st.session_state.widget_input = data.get("code", "")
                        st.session_state.stored_blocks = data.get("blocs", {}) # Restaure les blocs
                        st.toast("Projet restauré (Code + Blocs) !", icon="🎉")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
       
    with col_view:
        st.subheader("Aperçu")
        view_container = st.container()
        visuals_rendered_this_run = False 

        def afficher_visuels(container):
            with container:
                for item in st.session_state.partition_buffers:
                    if item['type'] == 'legende':
                        st.markdown("#### Page 1 : Légende")
                        st.pyplot(item['img_ecran'])
                    elif item['type'] == 'page':
                        st.markdown(f"#### Page {item['idx']}")
                        st.pyplot(item['img_ecran'])

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
            
            with st.status("📸 Génération...", expanded=True) as status:
                sequence = parser_texte(st.session_state.code_actuel)
                
                # Légende
                fig_leg_ecran = generer_page_1_legende(titre_partition, styles_ecran, mode_white=False)
                if force_white_print:
                    fig_leg_dl = generer_page_1_legende(titre_partition, styles_print, mode_white=True)
                    buf_leg = io.BytesIO(); fig_leg_dl.savefig(buf_leg, format="png", dpi=DPI_PDF_OPTIMISE, facecolor=styles_print['FOND'], bbox_inches='tight'); buf_leg.seek(0)
                    plt.close(fig_leg_dl)
                else:
                    fig_leg_dl = fig_leg_ecran
                    buf_leg = io.BytesIO(); fig_leg_dl.savefig(buf_leg, format="png", dpi=DPI_PDF_OPTIMISE, facecolor=styles_ecran['FOND'], bbox_inches='tight'); buf_leg.seek(0)

                st.session_state.partition_buffers.append({'type':'legende', 'buf': buf_leg, 'img_ecran': fig_leg_ecran})
                
                # Pages
                pages_data = []; current_page = []
                for n in sequence:
                    if n['corde'] == 'PAGE_BREAK':
                        if current_page: pages_data.append(current_page); current_page = []
                    else: current_page.append(n)
                if current_page: pages_data.append(current_page)
                
                if not pages_data: st.warning("Vide.")
                else:
                    for idx, page in enumerate(pages_data):
                        fig_ecran = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_ecran, options_visuelles, mode_white=False)
                        if force_white_print:
                            fig_dl = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_print, options_visuelles, mode_white=True)
                            buf = io.BytesIO(); fig_dl.savefig(buf, format="png", dpi=DPI_PDF_OPTIMISE, facecolor=styles_print['FOND'], bbox_inches='tight'); buf.seek(0)
                            plt.close(fig_dl)
                        else:
                            buf = io.BytesIO(); fig_ecran.savefig(buf, format="png", dpi=DPI_PDF_OPTIMISE, facecolor=styles_ecran['FOND'], bbox_inches='tight'); buf.seek(0)
                        st.session_state.partition_buffers.append({'type':'page', 'idx': idx+2, 'buf': buf, 'img_ecran': fig_ecran})
                        plt.close(fig_ecran)
                
                st.session_state.partition_generated = True
                status.write("✅ Visuels !")
                afficher_visuels(view_container)
                visuals_rendered_this_run = True
                
                status.write("📄 PDF...")
                st.session_state.pdf_buffer = generer_pdf_livret(st.session_state.partition_buffers, titre_partition)
                afficher_bouton_pdf(view_container)
                status.update(label="Terminé !", state="complete", expanded=False)

        if st.session_state.partition_generated and not visuals_rendered_this_run:
            afficher_visuels(view_container)
            afficher_bouton_pdf(view_container)

with tab3:
    st.subheader("Vidéo 🎥")
    st.warning("⚠️ Version Bêta.")
    if not HAS_MOVIEPY or not HAS_PYDUB: st.error("Modules manquants.")
    else:
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            bpm = st.slider("BPM", 30, 200, 60, key="bpm_video")
            seq = parser_texte(st.session_state.code_actuel)
            duree_estimee = ((seq[-1]['temps'] - seq[0]['temps'] + 4) * (60/bpm)) if seq else 10
            st.write(f"Durée : {int(duree_estimee)}s")
        with col_v2:
            if st.button("🎥 Créer Vidéo", type="primary", use_container_width=True):
                with st.status("🎬 Montage...", expanded=True) as status:
                    sequence = parser_texte(st.session_state.code_actuel)
                    audio_buffer = generer_audio_mix(sequence, bpm, acc_config)
                    if audio_buffer:
                        styles_video = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
                        img_buffer, px, offset = generer_image_longue_calibree(sequence, acc_config, styles_video, dpi=85)
                        if img_buffer:
                            # MODIFICATION ICI : FPS à 15 (anciennement 10)
                            video_path = creer_video_avec_son_calibree(img_buffer, audio_buffer, duree_estimee, (px, offset), bpm, fps=15)
                            if video_path:
                                st.session_state.video_path = video_path 
                                status.update(label="✅ Fini !", state="complete", expanded=False)
                            else: status.update(label="❌ Erreur", state="error")
        if st.session_state.video_path and os.path.exists(st.session_state.video_path):
            st.video(st.session_state.video_path)
            with open(st.session_state.video_path, "rb") as file:
                st.download_button("⬇️ Télécharger MP4", data=file, file_name="ngoni_video.mp4", mime="video/mp4", type="primary")

with tab4:
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