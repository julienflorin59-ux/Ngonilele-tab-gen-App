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
from fpdf import FPDF
import random
import pandas as pd 

# ==============================================================================
# ⚙️ CONFIGURATION & CHEMINS
# ==============================================================================
st.set_page_config(
    page_title="Générateur Tablature Ngonilélé", 
    layout="wide", 
    page_icon="ico_ngonilele.png", 
    initial_sidebar_state="expanded"
)

CHEMIN_POLICE = 'ML.ttf' 
CHEMIN_IMAGE_FOND = 'texture_ngonilele.png'
CHEMIN_ICON_POUCE = 'icon_pouce.png'
CHEMIN_ICON_INDEX = 'icon_index.png'
CHEMIN_ICON_POUCE_BLANC = 'icon_pouce_blanc.png'
CHEMIN_ICON_INDEX_BLANC = 'icon_index_blanc.png'
CHEMIN_LOGO_APP = 'ico_ngonilele.png'
DOSSIER_SAMPLES = 'samples'

# ==============================================================================
# 🚀 OPTIMISATION (CACHING)
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

# --- INITIALISATION SÉQUENCEUR (Dictionnaire) ---
if 'seq_grid' not in st.session_state:
    st.session_state.seq_grid = {} 

# ==============================================================================
# 🎵 BANQUE DE DONNÉES
# ==============================================================================
BANQUE_TABLATURES = {
    "--- Nouveau / Vide ---": "",
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
st.markdown("""
<div style="background-color: #d4b08c; color: black; padding: 10px; border-radius: 5px; border-left: 5px solid #A67C52; margin-bottom: 10px;">
    <strong>👈 Cliquez sur la flèche > en haut à gauche</strong> pour ouvrir le menu et charger un morceau dans la banque, imprimer sur fond blanc, m'envoyer vos tablatures pour les ajouter à la banque !!
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

POSITIONS_X = {'1G': -1, '2G': -2, '3G': -3, '4G': -4, '5G': -5, '6G': -6, '1D': 1, '2D': 2, '3D': 3, '4D': 4, '5D': 5, '6D': 6}
COULEURS_CORDES_REF = {'C': '#FF0000', 'D': '#FF8C00', 'E': '#FFD700', 'F': '#32CD32', 'G': '#00BFFF', 'A': '#00008B', 'B': '#9400D3'}
TRADUCTION_NOTES = {'C':'do', 'D':'ré', 'E':'mi', 'F':'fa', 'G':'sol', 'A':'la', 'B':'si'}
AUTOMATIC_FINGERING = {'1G':'P','2G':'P','3G':'P','1D':'P','2D':'P','3D':'P','4G':'I','5G':'I','6G':'I','4D':'I','5D':'I','6D':'I'}
NOTES_GAMME = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
DEF_ACC = {'1G':'G','2G':'C','3G':'E','4G':'A','5G':'C','6G':'G','1D':'F','2D':'A','3D':'D','4D':'G','5D':'B','6D':'E'}

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

# ==============================================================================
# 🎹 MOTEUR AUDIO
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
    buffer = io.BytesIO(); mix.export(buffer, format="mp3"); buffer.seek(0)
    return buffer

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
    buffer = io.BytesIO(); metronome_track.export(buffer, format="mp3"); buffer.seek(0)
    return buffer

# ==============================================================================
# 🎨 MOTEUR AFFICHAGE OPTIMISÉ
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
    fig, ax = plt.subplots(figsize=(16, 8), facecolor=c_fond)
    ax.set_facecolor(c_fond)
    ax.text(0, 2.5, titre, ha='center', va='bottom', fontproperties=prop_titre, color=c_txt)
    dessiner_contenu_legende(ax, 0.5, styles, mode_white)
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(-6, 4); ax.axis('off')
    return fig

def generer_page_notes(notes_page, idx, titre, config_acc, styles, options_visuelles, mode_white=False):
    plt.close('all') # Cleanup
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    
    img_pouce = load_image_asset(CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE)
    img_index = load_image_asset(CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX)
    
    t_min = notes_page[0]['temps']; t_max = notes_page[-1]['temps']
    lignes_sur_page = t_max - t_min + 1
    hauteur_fig = max(6, (lignes_sur_page * 0.75) + 6)
    
    fig, ax = plt.subplots(figsize=(16, hauteur_fig), facecolor=c_fond)
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

def generer_image_longue_calibree(sequence, config_acc, styles):
    if not sequence: return None, 0, 0
    t_min = sequence[0]['temps']; t_max = sequence[-1]['temps']
    y_max_header = 3.0; y_min_footer = -(t_max - t_min) - 2.0; hauteur_unites = y_max_header - y_min_footer
    FIG_WIDTH = 16; FIG_HEIGHT = hauteur_unites * 0.8; DPI = 100
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    
    plt.close('all') # Cleanup
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT), dpi=DPI, facecolor=c_fond); ax.set_facecolor(c_fond)
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
    plt.close(fig) # IMPORTANT
    buf.seek(0)
    return buf, pixels_par_temps, offset_premiere_note_px

# ✅ NOUVELLE FONCTION : Générer uniquement l'en-tête pour la vidéo (CORRIGÉE)
def generer_entete_seul(config_acc, styles):
    FIG_WIDTH = 16
    FIG_HEIGHT = 2.0 # Légèrement augmenté pour tout voir
    DPI = 100
    c_fond = styles['FOND']; c_txt = styles['TEXTE']
    
    plt.close('all')
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT), dpi=DPI, facecolor=c_fond); ax.set_facecolor(c_fond)
    # Zoom sur la zone utile
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(0.0, 4.0); ax.axis('off')

    prop_note_us = get_font_cached(24, 'bold')
    prop_note_eu = get_font_cached(18, 'normal', 'italic')
    prop_numero = get_font_cached(14, 'bold')

    y_base = 1.5
    ax.vlines(0, 0, y_base + 1.8, color=c_txt, lw=5, zorder=2)

    for code, props in config_acc.items():
        x = props['x']; note = props['n']; c = COULEURS_CORDES_REF.get(note, '#000000')
        # Positionnement plus espacé
        ax.text(x, y_base + 1.3, code, ha='center', color='gray', fontproperties=prop_numero)
        ax.text(x, y_base + 0.8, note, ha='center', color=c, fontproperties=prop_note_us) # US Note (Remonté)
        ax.text(x, y_base + 0.0, TRADUCTION_NOTES.get(note, '?'), ha='center', color=c, fontproperties=prop_note_eu) # EU Note
        ax.vlines(x, 0, y_base, colors=c, lw=3, zorder=1)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=DPI, facecolor=c_fond, bbox_inches=None)
    plt.close(fig)
    buf.seek(0)
    return buf

# ==============================================================================
# 🔧 FONCTION VIDÉO MODIFIÉE (HEADER FIXE + SYNC CALIBRÉE)
# ==============================================================================
def creer_video_avec_son_calibree(image_buffer, audio_buffer, duration_sec, metrics, bpm, config_acc, styles, fps=24):
    pixels_par_temps, offset_premiere_note_px = metrics
    
    # Fichiers temporaires
    with open("temp_score.png", "wb") as f: f.write(image_buffer.getbuffer())
    with open("temp_audio.mp3", "wb") as f: f.write(audio_buffer.getbuffer())
    
    # ✅ GÉNÉRATION HEADER FIXE
    header_buf = generer_entete_seul(config_acc, styles)
    with open("temp_header.png", "wb") as f: f.write(header_buf.getbuffer())

    clip_img = ImageClip("temp_score.png")
    w, h = clip_img.size
    
    video_h = 600
    # ✅ AJUSTEMENT POSITION BARRE ET SYNC
    bar_y = 160 # Position visuelle de la barre
    start_y = bar_y - offset_premiere_note_px # Sync
    speed_px_sec = pixels_par_temps * (bpm / 60.0)
    
    def scroll_func(t):
        current_y = start_y - (speed_px_sec * t)
        return ('center', current_y)
    
    # Clip défilant (Partition complète)
    moving_clip = clip_img.set_position(scroll_func).set_duration(duration_sec)
    
    # ✅ CLIP HEADER FIXE (Positionné tout en haut)
    header_clip = ImageClip("temp_header.png").set_position(('center', 0)).set_duration(duration_sec)

    # Barre de lecture (Jaune)
    try:
        bar_height = int(pixels_par_temps)
        highlight_bar = ColorClip(size=(w, bar_height), color=(255, 215, 0)).set_opacity(0.3).set_position(('center', bar_y - bar_height/2)).set_duration(duration_sec)
        # Fond
        bg_clip = ColorClip(size=(w, video_h), color=(229, 196, 163)).set_duration(duration_sec) 
        
        # ✅ COMPOSITION : Fond + Partition + Header (FIXE) + Barre (PAR DESSUS TOUT)
        # L'ordre est crucial : la barre est en dernier pour être toujours visible, même sur le header.
        video_visual = CompositeVideoClip([bg_clip, moving_clip, header_clip, highlight_bar], size=(w, video_h))
    except:
        video_visual = CompositeVideoClip([moving_clip], size=(w, video_h))
        
    audio_clip = AudioFileClip("temp_audio.mp3").subclip(0, duration_sec)
    final = video_visual.set_audio(audio_clip)
    final.fps = fps
    
    output_filename = "ngoni_video_sound.mp4"
    final.write_videofile(output_filename, codec='libx264', audio_codec='aac', preset='ultrafast')
    
    # Cleanup
    try: 
        audio_clip.close(); final.close(); video_visual.close(); clip_img.close(); header_clip.close()
        if os.path.exists("temp_score.png"): os.remove("temp_score.png")
        if os.path.exists("temp_header.png"): os.remove("temp_header.png")
        if os.path.exists("temp_audio.mp3"): os.remove("temp_audio.mp3")
    except: pass
    
    return output_filename

def generer_pdf_livret(buffers, titre):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    for item in buffers:
        pdf.add_page()
        temp_img = f"temp_pdf_{item['type']}_{item.get('idx', 0)}.png"
        with open(temp_img, "wb") as f:
            f.write(item['buf'].getbuffer())
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

def charger_morceau():
    choix = st.session_state.selection_banque
    if choix in BANQUE_TABLATURES:
        nouveau = BANQUE_TABLATURES[choix].strip()
        st.session_state.code_actuel = nouveau
        st.session_state.widget_input = nouveau
        st.session_state.partition_generated = False
        st.session_state.video_path = None
        st.session_state.audio_buffer = None
        st.session_state.pdf_buffer = None # Reset PDF

def mise_a_jour_texte(): 
    st.session_state.code_actuel = st.session_state.widget_input
    st.session_state.partition_generated = False
    st.session_state.video_path = None
    st.session_state.audio_buffer = None
    st.session_state.pdf_buffer = None # Reset PDF

def ajouter_texte(txt):
    if 'code_actuel' in st.session_state:
        st.session_state.code_actuel += "\n" + txt
    else:
        st.session_state.code_actuel = txt
    st.session_state.widget_input = st.session_state.code_actuel

# ✅ NOUVELLE FONCTION POUR CONFIRMATION (TOAST)
def ajouter_avec_feedback(txt, label_toast):
    ajouter_texte(txt)
    st.toast(f"Ajouté : {label_toast}", icon="✅")

def annuler_derniere_ligne():
    lines = st.session_state.code_actuel.strip().split('\n')
    if len(lines) > 0:
        st.session_state.code_actuel = "\n".join(lines[:-1])
        st.session_state.widget_input = st.session_state.code_actuel
        st.toast("Dernière note effacée", icon="🗑️") # ✅ TOAST POUR EFFACER

with st.sidebar:
    st.header("🎚️ Réglages")
    st.markdown("### 📚 Banque de Morceaux")
    st.selectbox("Choisir un morceau :", options=list(BANQUE_TABLATURES.keys()), key='selection_banque', on_change=charger_morceau)
    st.caption("⚠️ Remplacera le texte actuel.")
    st.markdown("---")
    with st.expander("🎨 Apparence", expanded=False):
        # ✅ COULEUR PAR DÉFAUT MODIFIÉE pour matcher le thème
        bg_color = "#e5c4a3"
        use_bg_img = True
        bg_alpha = 0.2
        st.markdown("---")
        force_white_print = st.checkbox("🖨️ Fond blanc pour impression", value=True)
    st.markdown("---")
    st.markdown("### 🤝 Contribuer")
    # ✅ COULEUR DU BOUTON MODIFIÉE pour matcher le thème
    st.markdown(f'<a href="mailto:julienflorin59@gmail.com" target="_blank"><button style="width:100%; background-color:#A67C52; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">📧 Envoyer ma partition</button></a>', unsafe_allow_html=True)

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
        subtab_btn, subtab_visu, subtab_seq = st.tabs(["🔘 Boutons (Défaut)", "🎨 Visuel (Nouveau)", "🎹 Séquenceur (Grille Compacte)"])

        # --- LOGIQUE UNIFIÉE ---
        def get_suffixe_doigt(corde, mode_key):
            mode = st.session_state[mode_key]
            if mode == "👍 Force Pouce (P)": return " P", " (Pouce)"
            if mode == "👆 Force Index (I)": return " I", " (Index)"
            if corde in ['1G','2G','3G','1D','2D','3D']: return " P", " (Pouce)"
            return " I", " (Index)"

        # --- ONGLET BOUTONS ---
        with subtab_btn:
            # ✅ REMPLACEMENT DE ST.INFO PAR UN BLOC HTML STYLISÉ
            st.markdown("""
            <div style="background-color: #d4b08c; padding: 10px; border-radius: 5px; border-left: 5px solid #A67C52; color: black; margin-bottom: 10px;">
                <strong>⌨️ Mode Rapide (Grille Compacte)</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.radio("Mode de jeu :", ["🖐️ Auto (Défaut)", "👍 Force Pouce (P)", "👆 Force Index (I)"], key="btn_mode_doigt", horizontal=True)
            
            def ajouter_note_boutons(corde):
                suffixe, nom_doigt = get_suffixe_doigt(corde, "btn_mode_doigt")
                ajouter_texte(f"+ {corde}{suffixe}")
                st.toast(f"✅ Note {corde} ajoutée{nom_doigt}", icon="🎵")

            st.markdown("""<style>
            div[data-testid="column"] .stButton button { width: 100%; height: auto !important; min-height: 0px !important; padding: 4px 8px !important; line-height: 1 !important; }
            div[data-testid="column"] .stButton button p { font-size: 13px !important; }
            </style>""", unsafe_allow_html=True)
            
            bc1, bc2, bc3, bc4 = st.columns(4)
            with bc1: 
                st.caption("Gauche")
                for c in ['1G','2G','3G','4G','5G','6G']: st.button(c, key=f"btn_{c}", on_click=ajouter_note_boutons, args=(c,), use_container_width=True)
            with bc2:
                st.caption("Droite")
                for c in ['1D','2D','3D','4D','5D','6D']: st.button(c, key=f"btn_{c}", on_click=ajouter_note_boutons, args=(c,), use_container_width=True)
            with bc3:
                st.caption("Outils")
                # ✅ BOUTONS MODIFIÉS (NOMS + FEEDBACK TOAST)
                st.button("↩️ Effacer une note", key="btn_undo", on_click=annuler_derniere_ligne, use_container_width=True)
                st.button("🟰 Notes Simultanées", key="btn_simul", on_click=ajouter_avec_feedback, args=("=", "Notes Simultanées"), use_container_width=True)
                st.button("🔁 Notes Doublées", key="btn_x2", on_click=ajouter_avec_feedback, args=("x2", "Notes Doublées"), use_container_width=True)
                st.button("🔇 Insérer Silence", key="btn_silence", on_click=ajouter_avec_feedback, args=("+ S", "Silence"), use_container_width=True)
            with bc4:
                st.caption("Structure")
                # ✅ BOUTONS MODIFIÉS (NOMS + FEEDBACK TOAST)
                st.button("📄 Insérer Page", key="btn_page", on_click=ajouter_avec_feedback, args=("+ PAGE", "Saut de Page"), use_container_width=True)
                st.button("📝 Insérer Texte", key="btn_txt", on_click=ajouter_avec_feedback, args=("+ TXT Message", "Texte"), use_container_width=True)

        # --- ONGLET VISUEL ---
        with subtab_visu:
            # ✅ REMPLACEMENT DE ST.INFO PAR UN BLOC HTML STYLISÉ
            st.markdown("""
            <div style="background-color: #d4b08c; padding: 10px; border-radius: 5px; border-left: 5px solid #A67C52; color: black; margin-bottom: 10px;">
                <strong>🎨 Mode Visuel (Schéma du Manche)</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.radio("Mode de jeu :", ["🖐️ Auto (Défaut)", "👍 Force Pouce (P)", "👆 Force Index (I)"], key="visu_mode_doigt", horizontal=True)
            
            def ajouter_note_visuelle(corde):
                suffixe, nom_doigt = get_suffixe_doigt(corde, "visu_mode_doigt")
                ajouter_texte(f"+ {corde}{suffixe}")
                st.toast(f"✅ Note {corde} ajoutée{nom_doigt}", icon="🎵")

            def outil_visuel_wrapper(action, txt_code, msg_toast):
                if action == "ajouter": ajouter_texte(txt_code)
                elif action == "undo": annuler_derniere_ligne()
                st.toast(msg_toast, icon="🛠️")

            COLORS_VISU = {'6G':'#00BFFF','5G':'#FF4B4B','4G':'#00008B','3G':'#FFD700','2G':'#FF4B4B','1G':'#00BFFF','1D':'#32CD32','2D':'#00008B','3D':'#FFA500','4D':'#00BFFF','5D':'#9400D3','6D':'#FFD700'}
            st.write("##### Cordes de Gauche _____________________ Cordes de Droite")
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
            with c_tools[0]: st.button("↩️", key="v_undo", help="Annuler la dernière action", on_click=outil_visuel_wrapper, args=("undo", "", "Annulé !"), use_container_width=True)
            with c_tools[1]: st.button("🟰", key="v_simul", help="Notes Simultanées (Jouer en même temps)", on_click=outil_visuel_wrapper, args=("ajouter", "=", "Mode Simultané"), use_container_width=True)
            with c_tools[2]: st.button("🔁", key="v_x2", help="Doubler la note (x2)", on_click=outil_visuel_wrapper, args=("ajouter", "x2", "Doublé (x2)"), use_container_width=True)
            with c_tools[3]: st.button("🔇", key="v_sil", help="Insérer un silence", on_click=outil_visuel_wrapper, args=("ajouter", "+ S", "Silence"), use_container_width=True)
            with c_tools[4]: st.button("📄", key="v_page", help="Insérer une page (Saut de page)", on_click=outil_visuel_wrapper, args=("ajouter", "+ PAGE", "Nouvelle Page"), use_container_width=True)
            with c_tools[5]: st.button("📝", key="v_txt", help="Insérer texte (Annotation)", on_click=outil_visuel_wrapper, args=("ajouter", "+ TXT Msg", "Texte"), use_container_width=True)

        # --- ONGLET SÉQUENCEUR (CORRIGÉ ET COMPLET) ---
        with subtab_seq:
            # ✅ REMPLACEMENT DE ST.INFO PAR UN BLOC HTML STYLISÉ
            st.markdown("""
            <div style="background-color: #d4b08c; padding: 10px; border-radius: 5px; border-left: 5px solid #A67C52; color: black; margin-bottom: 10px;">
                <strong>🎹 Séquenceur (Grille Compacte)</strong>
            </div>
            """, unsafe_allow_html=True)
            
            # Nombre de temps variable
            nb_temps = st.number_input("Nombre de temps (Lignes)", min_value=4, max_value=64, value=8, step=4)
            st.write("Cochez les cases (Lignes = Temps, Colonnes = Cordes).")
            
            # Entête des cordes (Horizontal)
            cols = st.columns([0.8] + [1]*12) 
            cordes_list = ['1G', '2G', '3G', '4G', '5G', '6G', '1D', '2D', '3D', '4D', '5D', '6D']
            
            with cols[0]: st.write("**T**")
            for i, c in enumerate(cordes_list):
                with cols[i+1]: st.markdown(f"**{c}**")

            # Conteneur AVEC SCROLL (height fixe)
            with st.container(height=400):
                # Grille de temps
                for t in range(nb_temps):
                    cols = st.columns([0.8] + [1]*12)
                    with cols[0]: 
                        st.write("") 
                        st.caption(f"**{t+1}**")
                    
                    for i, c in enumerate(cordes_list):
                        key = f"T{t}_{c}"
                        if key not in st.session_state.seq_grid:
                            st.session_state.seq_grid[key] = False
                            
                        with cols[i+1]:
                            st.session_state.seq_grid[key] = st.checkbox(" ", key=key, value=st.session_state.seq_grid[key], label_visibility="collapsed")

            st.write("")
            col_seq_btn, col_seq_reset = st.columns([3, 1])
            with col_seq_btn:
                if st.button("📥 Insérer la séquence", type="primary", use_container_width=True):
                    texte_genere = ""
                    # Lecture de la grille
                    for t in range(nb_temps):
                        notes_activees = []
                        for c in cordes_list:
                            if st.session_state.seq_grid[f"T{t}_{c}"]:
                                notes_activees.append(c)
                        
                        if not notes_activees:
                            texte_genere += "+ S\n"
                        else:
                            premier = True
                            for note in notes_activees:
                                prefix = "+ " if premier else "= "
                                doigt = " P" if note in ['1G','2G','3G','1D','2D','3D'] else " I"
                                texte_genere += f"{prefix}{note}{doigt}\n" # FORCE L'AFFICHAGE DU DOIGT
                                premier = False
                    
                    ajouter_texte(texte_genere)
                    st.toast("Séquence ajoutée !", icon="🎹")
            
            with col_seq_reset:
                if st.button("🗑️ Vider"):
                    for k in st.session_state.seq_grid:
                        st.session_state.seq_grid[k] = False
                    st.rerun()
            
            # ✅ RE-AJOUT DES BOUTONS DE STRUCTURE
            st.markdown("---")
            st.caption("Structure & Annotations")
            c_struct_1, c_struct_2 = st.columns(2)
            with c_struct_1:
                st.button("📄 Insérer Page", key="seq_page", on_click=ajouter_avec_feedback, args=("+ PAGE", "Saut de Page"), use_container_width=True)
            with c_struct_2:
                st.button("📝 Insérer Texte", key="seq_txt", on_click=ajouter_avec_feedback, args=("+ TXT Message", "Texte"), use_container_width=True)

        st.markdown("---")
        st.caption("📝 **Éditeur Texte (Résultat en temps réel)**")
        st.text_area("Zone de Code (Modifiable manuellement) :", height=200, key="widget_input", on_change=mise_a_jour_texte, label_visibility="collapsed")
        st.caption("💡 Astuce : Vous pouvez agrandir la zone de texte en tirant le coin inférieur droit.")
        
        st.markdown("---")
        col_play_btn, col_play_bpm = st.columns([1, 1])
        with col_play_bpm: bpm_preview = st.number_input("BPM", 40, 200, 100)
        with col_play_btn:
            st.write(""); st.write("")
            if st.button("🎧 Écouter l'extrait"):
                with st.status("🎵 Génération...", expanded=True) as status:
                    seq_prev = parser_texte(st.session_state.code_actuel)
                    audio_prev = generer_audio_mix(seq_prev, bpm_preview, acc_config)
                    status.update(label="✅ Prêt !", state="complete", expanded=False)
                if audio_prev: st.audio(audio_prev, format="audio/mp3")

        with st.expander("Gérer le fichier"):
            st.download_button(label="💾 Sauvegarder", data=st.session_state.code_actuel, file_name=f"{titre_partition}.txt", mime="text/plain")
            uploaded_file = st.file_uploader("📂 Charger", type="txt")
            if uploaded_file:
                st.session_state.code_actuel = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
                st.rerun()
        
    with col_view:
        st.subheader("Aperçu Partition")
        view_container = st.container()
        
        if st.button("🔄 Générer la partition", type="primary", use_container_width=True):
            st.session_state.partition_buffers = [] 
            st.session_state.partition_generated = False
            
            styles_ecran = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
            styles_print = {'FOND': 'white', 'TEXTE': 'black', 'PERLE_FOND': 'white', 'LEGENDE_FOND': 'white'}
            options_visuelles = {'use_bg': use_bg_img, 'alpha': bg_alpha}
            
            with view_container:
                with st.status("📸 Traitement en cours...", expanded=True) as status:
                    sequence = parser_texte(st.session_state.code_actuel)
                    
                    st.write("📖 Légende...")
                    fig_leg_ecran = generer_page_1_legende(titre_partition, styles_ecran, mode_white=False)
                    st.markdown("#### Page 1 : Légende")
                    st.pyplot(fig_leg_ecran)
                    
                    if force_white_print: fig_leg_dl = generer_page_1_legende(titre_partition, styles_print, mode_white=True)
                    else: fig_leg_dl = fig_leg_ecran
                    buf_leg = io.BytesIO(); fig_leg_dl.savefig(buf_leg, format="png", dpi=200, facecolor=styles_print['FOND'] if force_white_print else bg_color, bbox_inches='tight'); buf_leg.seek(0)
                    st.session_state.partition_buffers.append({'type':'legende', 'buf': buf_leg, 'img_ecran': fig_leg_ecran})
                    if force_white_print: plt.close(fig_leg_dl)
                    
                    pages_data = []; current_page = []
                    for n in sequence:
                        if n['corde'] == 'PAGE_BREAK':
                            if current_page: pages_data.append(current_page); current_page = []
                        else: current_page.append(n)
                    if current_page: pages_data.append(current_page)
                    
                    if not pages_data: st.warning("Aucune note.")
                    else:
                        st.write("📕 Assemblage du PDF...") # Notification génération PDF
                        for idx, page in enumerate(pages_data):
                            st.write(f"📄 Page {idx+2}...")
                            fig_ecran = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_ecran, options_visuelles, mode_white=False)
                            st.markdown(f"#### Page {idx+2}")
                            st.pyplot(fig_ecran)
                            
                            if force_white_print: fig_dl = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_print, options_visuelles, mode_white=True)
                            else: fig_dl = fig_ecran
                            buf = io.BytesIO(); fig_dl.savefig(buf, format="png", dpi=200, facecolor=styles_print['FOND'] if force_white_print else bg_color, bbox_inches='tight'); buf.seek(0)
                            st.session_state.partition_buffers.append({'type':'page', 'idx': idx+2, 'buf': buf, 'img_ecran': fig_ecran})
                            if force_white_print: plt.close(fig_dl)
                        
                        # Génération PDF immédiate
                        st.session_state.pdf_buffer = generer_pdf_livret(st.session_state.partition_buffers, titre_partition)
                    
                    st.session_state.partition_generated = True
                    status.update(label="✅ Terminé !", state="complete", expanded=False)

        elif st.session_state.partition_generated and st.session_state.partition_buffers:
             with view_container:
                for item in st.session_state.partition_buffers:
                    if item['type'] == 'legende':
                        st.markdown("#### Page 1 : Légende")
                        st.pyplot(item['img_ecran'])
                    elif item['type'] == 'page':
                        st.markdown(f"#### Page {item['idx']}")
                        st.pyplot(item['img_ecran'])

        if st.session_state.partition_generated and st.session_state.pdf_buffer:
            st.markdown("---")
            st.download_button(label="📕 Télécharger le Livret PDF", data=st.session_state.pdf_buffer, file_name=f"{titre_partition}.pdf", mime="application/pdf", type="primary", use_container_width=True)

# --- TAB VIDÉO (RÉINTÉGRÉ) ---
with tab3:
    st.subheader("Générateur de Vidéo Défilante 🎥")
    st.warning("⚠️ Sur la version gratuite, évitez les morceaux trop longs.")
    
    if not HAS_MOVIEPY: st.error("❌ Le module 'moviepy' n'est pas installé.")
    elif not HAS_PYDUB: st.error("❌ Le module 'pydub' n'est pas installé.")
    else:
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            bpm = st.slider("Vitesse (BPM)", 30, 200, 60, key="bpm_video")
            seq = parser_texte(st.session_state.code_actuel)
            if seq:
                nb_temps = seq[-1]['temps'] - seq[0]['temps']
                duree_estimee = (nb_temps + 4) * (60/bpm)
                st.write(f"Durée : {int(duree_estimee)}s")
            else: duree_estimee = 10
        with col_v2:
            btn_video = st.button("🎥 Générer Vidéo + Audio", type="primary", use_container_width=True)

        if btn_video:
            with st.status("🎬 Création de la vidéo en cours...", expanded=True) as status:
                st.write("🎹 Mixage Audio...")
                sequence = parser_texte(st.session_state.code_actuel)
                audio_buffer = generer_audio_mix(sequence, bpm, acc_config)
                
                if audio_buffer:
                    st.write("🎨 Création des visuels...")
                    styles_video = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
                    img_buffer, px_par_temps, offset_px = generer_image_longue_calibree(sequence, acc_config, styles_video)
                    
                    if img_buffer:
                        st.write("🎞️ Montage vidéo (Patientez, c'est lourd !)...")
                        progress_bar = st.progress(0)
                        try:
                            progress_bar.progress(30)
                            # ✅ APPEL DE LA FONCTION MODIFIÉE AVEC HEADER FIXE
                            video_path = creer_video_avec_son_calibree(img_buffer, audio_buffer, duree_estimee, (px_par_temps, offset_px), bpm, acc_config, styles_video)
                            progress_bar.progress(100)
                            st.session_state.video_path = video_path 
                            status.update(label="✅ Vidéo terminée !", state="complete", expanded=False)
                            st.success("Vidéo terminée et synchronisée ! 🥳")
                        except Exception as e:
                            st.error(f"Erreur lors du montage : {e}")
                            status.update(label="❌ Erreur !", state="error")

        if st.session_state.video_path and os.path.exists(st.session_state.video_path):
            st.video(st.session_state.video_path)
            with open(st.session_state.video_path, "rb") as file:
                st.download_button(label="⬇️ Télécharger la Vidéo", data=file, file_name="ngoni_video_synchro.mp4", mime="video/mp4", type="primary")

# --- TAB AUDIO (RÉINTÉGRÉ) ---
with tab4:
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        st.subheader("🎧 Générateur Audio")
        if not HAS_PYDUB: st.error("❌ Le module 'pydub' n'est pas installé.")
        else:
            bpm_audio = st.slider("Vitesse Morceau (BPM)", 30, 200, 100, key="bpm_audio")
            if st.button("🎵 Générer MP3 du Morceau", type="primary", use_container_width=True):
                with st.status("🎵 Mixage en cours...", expanded=True) as status:
                    sequence = parser_texte(st.session_state.code_actuel)
                    mp3_buffer = generer_audio_mix(sequence, bpm_audio, acc_config)
                    if mp3_buffer:
                        st.session_state.audio_buffer = mp3_buffer
                        status.update(label="✅ Mixage terminé !", state="complete", expanded=False)
                        st.success("Terminé !")

            if st.session_state.audio_buffer:
                st.audio(st.session_state.audio_buffer, format="audio/mp3")
                st.download_button(label="⬇️ Télécharger le MP3", data=st.session_state.audio_buffer, file_name=f"{titre_partition.replace(' ', '_')}.mp3", mime="audio/mpeg", type="primary")

    with col_droite:
        st.subheader("🥁 Groove Box (Métronome)")
        # ✅ REMPLACEMENT ICI : BLOC HTML STYLISÉ POUR LE MÉTRONOME
        st.markdown("""
        <div style="background-color: #d4b08c; padding: 10px; border-radius: 5px; border-left: 5px solid #A67C52; color: black; margin-bottom: 10px;">
            Un outil simple pour s'entraîner en rythme.
        </div>
        """, unsafe_allow_html=True)
        
        col_sig, col_bpm_metro = st.columns([1, 2])
        with col_sig: signature_metro = st.radio("Signature", ["4/4", "3/4"], horizontal=True)
        with col_bpm_metro: bpm_metro = st.slider("Vitesse (BPM)", 30, 200, 80, key="bpm_metro")
        duree_metro = st.slider("Durée (secondes)", 10, 300, 60, step=10)
        if st.button("▶️ Lancer le Métronome", type="primary", use_container_width=True):
            with st.status("🥁 Création du beat...", expanded=True) as status:
                metro_buffer = generer_metronome(bpm_metro, duree_metro, signature_metro)
                if metro_buffer:
                    st.session_state.metronome_buffer = metro_buffer
                    status.update(label="✅ Prêt !", state="complete", expanded=False)
        
        if st.session_state.metronome_buffer:
            st.audio(st.session_state.metronome_buffer, format="audio/mp3")