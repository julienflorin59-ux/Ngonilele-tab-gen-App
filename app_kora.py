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

# --- OPTIMISATION VITESSE : BACKEND NON-INTERACTIF ---
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
    page_title="Générateur Tablature Ngonilélé (Pro)",
    layout="wide",
    page_icon="ico_ngonilele.png",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 📱 OPTIMISATION CSS & STYLE GLOBAL
# ==============================================================================
@st.cache_resource
def load_css_styles():
    return """
<style>
    @media (max-width: 640px) {
        .stButton button { padding: 0px 2px !important; font-size: 0.8rem !important; min-height: 40px !important; white-space: nowrap !important; }
        div[data-testid="column"] { width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; min-width: calc(50% - 0.5rem) !important; }
    }
    button[data-testid="stTab"] { border: 1px solid #A67C52; border-radius: 5px; margin-right: 5px; background-color: #e5c4a3; color: black; padding: 10px 15px; opacity: 0.9; }
    button[data-testid="stTab"][aria-selected="true"] { background-color: #d4b08c; border: 2px solid #A67C52; font-weight: bold; opacity: 1; }
    
    /* Boutons de téléchargement et Upload stylisés */
    .stDownloadButton button, [data-testid='stFileDropzone'] { background-color: #e5c4a3 !important; color: black !important; border: none !important; transition: 0.2s; }
    .stDownloadButton button:hover, [data-testid='stFileDropzone']:hover { background-color: #d4b08c !important; }
    [data-testid='stFileUploader'] label[data-testid='stWidgetLabel'] { display: none; }
    [data-testid='stFileDropzone']::after { content: "📂 Charger projet"; color: black; font-weight: bold; display: block; text-align: center; }
    [data-testid='stFileDropzone'] > div > div { display: none !important; }
</style>
"""
st.markdown(load_css_styles(), unsafe_allow_html=True)

# --- CONSTANTES ---
CHEMIN_POLICE = 'ML.ttf'
CHEMIN_IMAGE_FOND = 'texture_ngonilele.png'
CHEMIN_ICON_POUCE = 'icon_pouce.png'
CHEMIN_ICON_INDEX = 'icon_index.png'
CHEMIN_ICON_POUCE_BLANC = 'icon_pouce_blanc.png'
CHEMIN_ICON_INDEX_BLANC = 'icon_index_blanc.png'
DOSSIER_SAMPLES = 'samples'

# --- CONSTANTES RYTHMIQUES (BASE 12) ---
TICKS_NOIRE = 12       # 1 temps
TICKS_CROCHE = 6       # 1/2 temps
TICKS_TRIOLET = 4      # 1/3 temps
TICKS_DOUBLE = 3       # 1/4 temps

# NOUVEAUX SYMBOLES (EMOJIS)
SYMBOLES_DUREE = {
    '+': TICKS_NOIRE,
    '♪': TICKS_CROCHE,   # Croche (1 note)
    '🎶': TICKS_TRIOLET, # Triolet (3 notes)
    '♬': TICKS_DOUBLE    # Double (2 notes)
}

# --- DONNÉES MUSICALES ---
POSITIONS_X = {'1G': -1, '2G': -2, '3G': -3, '4G': -4, '5G': -5, '6G': -6, '1D': 1, '2D': 2, '3D': 3, '4D': 4, '5D': 5, '6D': 6}
COULEURS_CORDES_REF = {'C': '#FF0000', 'D': '#FF8C00', 'E': '#FFD700', 'F': '#32CD32', 'G': '#00BFFF', 'A': '#00008B', 'B': '#9400D3'}
COLORS_VISU = {'6G':'#00BFFF','5G':'#FF4B4B','4G':'#00008B','3G':'#FFD700','2G':'#FF4B4B','1G':'#00BFFF','1D':'#32CD32','2D':'#00008B','3D':'#FFA500','4D':'#00BFFF','5D':'#9400D3','6D':'#FFD700'}
TRADUCTION_NOTES = {'C':'do', 'D':'ré', 'E':'mi', 'F':'fa', 'G':'sol', 'A':'la', 'B':'si'}
AUTOMATIC_FINGERING = {'1G':'P','2G':'P','3G':'P','1D':'P','2D':'P','3D':'P','4G':'I','5G':'I','6G':'I','4D':'I','5D':'I','6D':'I'}

NOTES_GAMME = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FULL_NOTES = []
for oct in [3,4,5]:
    for n in NOTES_GAMME: FULL_NOTES.append(f"{n}{oct}")

BASE_TUNING_HARDWARE = {'1D':'E3','1G':'G3','2D':'A3','2G':'C4','3D':'D4','3G':'E4','4D':'G4','4G':'A4','5D':'C5','5G':'D5','6D':'E5','6G':'G5'}
DEF_ACC = BASE_TUNING_HARDWARE.copy()

GAMMES_PRESETS = {
    "1. Pentatonique Fondamentale": "E3G3A3C4D4E4G4A4C5D5E5G5",
    "2. Pentatonique (Descente Basse)": "F3G3A3C4D4E4G4A4C5D5E5G5",
    "3. Manitoumani (Standard)": "F3G3A3C4D4E4G4A4B4C5E5G5",
    "4. Orientale Sahara": "F3A3B3D4E4F4G#4A4B4C5E5F5",
    "5. Fa Blues Augmenté Nyama": "F3G#3A#3C4D#4F4G4G#4A#4C5D#5F5"
}
ORDRE_MAPPING = ['1D', '1G', '2D', '2G', '3D', '3G', '4D', '4G', '5D', '5G', '6D', '6G']

BANQUE_TABLATURES = {
    "--- Nouveau / Vide ---": "",
    "Exercice 1 : Gamme Simple": "1   1D\n+   1G\n+   2D\n+   2G\n+   3D\n+   3G\n+   4D\n+   4G\n+   5D\n+   5G\n+   6D\n+   6G",
    "Exercice 3 : Coordination (Ping-Pong)": "1   6G\n+   6D\n+   5G\n+   5D\n+   4G\n+   4D\n+   3G\n+   3D\n+   2G\n+   2D\n+   1G\n+   1D\n+   S\n+   TXT  REMONTEE\n+   1D\n+   1G\n+   2D\n+   2G\n+   3D\n+   3G\n+   4D\n+   4G\n+   5D\n+   5G\n+   6D\n+   6G",
    "Exercice 4 : Les Tierces": "1   1G\n+   3G\n+   2G\n+   4G\n+   3G\n+   5G\n+   4G\n+   6G\n+   S\n+   TXT  COTE DROIT\n+   1D\n+   3D\n+   2D\n+   4D\n+   3D\n+   5D\n+   4D\n+   6D\n+   S\n+   TXT  FINAL\n+   6G\n=   6D",
    "Exercice 5 : Accords et Silences": "1   6G\n=   6D\n+   S\n+   5G\n=   5D\n+   S\n+   4G\n=   4D\n+   S\n+   3G\n=   3D\n+   S\n+   2G\n=   2D\n+   S\n+   1G\n=   1D\n+   S\n+   TXT  ARPEGE RAPIDE\n+   6G\n+   6D\n+   5G\n+   5D\n+   4G\n=   4D",
    "Démonstration Rythmes": "1   6G\n+   TXT  NOIRES (+)\n+   6D\n+   5G\n+   5D\n+   S\n+   TXT  CROCHES (♪)\n♪   4G\n♪   4D\n♪   3G\n♪   3D\n+   S\n+   TXT  TRIOLETS (🎶)\n🎶   2G\n🎶   2D\n🎶   1G\n🎶   1D\n🎶   2G\n🎶   2D\n+   S\n+   TXT  DOUBLES (♬)\n♬ 6G\n♬ 6D\n♬ 5G\n♬ 5D\n♬ 4G\n♬ 4D\n♬ 3G\n♬ 3D"
}

# ==============================================================================
# 🚀 FONCTIONS UTILES
# ==============================================================================
@st.cache_resource
def load_font_properties():
    if os.path.exists(CHEMIN_POLICE): return fm.FontProperties(fname=CHEMIN_POLICE)
    return fm.FontProperties(family='sans-serif')

@st.cache_resource
def load_image_asset(path):
    if os.path.exists(path): return mpimg.imread(path)
    return None

def get_font_cached(size, weight='normal', style='normal'):
    prop = load_font_properties().copy()
    prop.set_size(size); prop.set_weight(weight); prop.set_style(style)
    return prop

def parse_gamme_string(gamme_str): return re.findall(r"[A-G][#b]?[0-9]*", gamme_str)
def get_color_for_note(note): return COULEURS_CORDES_REF.get(note[0].upper(), '#000000')

def get_valid_notes_for_string(string_key):
    # Logique simplifiée pour l'exemple
    return FULL_NOTES

# --- LE CŒUR RYTHMIQUE (NOUVEAU PARSER BASE 12) ---
def parser_texte(texte):
    data = []
    current_tick = 0
    last_note_tick = 0
    last_note_duration = TICKS_NOIRE # Par défaut
    
    if not texte: return []
    
    for ligne in texte.strip().split('\n'):
        parts = ligne.strip().split(maxsplit=2)
        if not parts: continue
        try:
            symbole = parts[0]
            corde_valide = parts[1].upper()
            
            # 1. Gestion du TEMPS
            if symbole == '=':
                # Accord : même temps que la note précédente
                this_start = last_note_tick
                this_duration = last_note_duration # Hérite de la durée
            elif symbole.isdigit():
                # Cas spécial "1" au début
                this_start = 0
                this_duration = TICKS_NOIRE
                current_tick = 0
            elif symbole in SYMBOLES_DUREE:
                # +, ♪, 🎶, ♬
                duration = SYMBOLES_DUREE[symbole]
                this_start = current_tick
                this_duration = duration
                current_tick += duration # On avance le curseur
            else:
                continue

            last_note_tick = this_start
            last_note_duration = this_duration

            # 2. Gestion du CONTENU
            if corde_valide == 'TXT':
                msg = parts[2] if len(parts) > 2 else ""
                data.append({'tick': this_start, 'duration': this_duration, 'corde': 'TEXTE', 'message': msg})
                continue
            elif corde_valide == 'PAGE':
                data.append({'tick': this_start, 'duration': 0, 'corde': 'PAGE_BREAK'})
                continue
            
            corde_valide = 'SILENCE' if corde_valide=='S' else corde_valide
            
            # Gestion répétition et doigté (inchangée)
            doigt = None; repetition = 1
            if len(parts) > 2:
                for p in parts[2].split():
                    p_upper = p.upper()
                    if p_upper.startswith('X') and p_upper[1:].isdigit(): repetition = int(p_upper[1:])
                    elif p_upper in ['I', 'P']: doigt = p_upper
            
            if not doigt and corde_valide in AUTOMATIC_FINGERING: doigt = AUTOMATIC_FINGERING[corde_valide]
            
            # Ajout des notes (avec répétition)
            temp_cursor = this_start
            for i in range(repetition):
                note = {'tick': temp_cursor, 'duration': this_duration, 'corde': corde_valide}
                if doigt: note['doigt'] = doigt
                data.append(note)
                
                if i < repetition - 1:
                    temp_cursor += this_duration
                    current_tick = temp_cursor + this_duration # Mise à jour globale si répétition

        except: pass
        
    data.sort(key=lambda x: x['tick'])
    return data

# ==============================================================================
# 🎹 MOTEUR AUDIO (AVEC DÉCOUPE RYTHMIQUE)
# ==============================================================================
HAS_PYDUB = False
try:
    from pydub import AudioSegment
    from pydub.generators import Sine
    HAS_PYDUB = True
except: pass

@st.cache_data(show_spinner=False)
def generer_audio_mix(sequence, bpm, acc_config):
    if not HAS_PYDUB or not sequence: return None
    
    # 1. Chargement des samples (Optimisé)
    samples_loaded = {}
    cordes_utilisees = set([n['corde'] for n in sequence if n['corde'] in POSITIONS_X])
    
    for corde in cordes_utilisees:
        note_name = acc_config.get(corde, {'n':'C4'})['n']
        chemin = os.path.join(DOSSIER_SAMPLES, f"{note_name}.mp3")
        loaded = False
        
        if os.path.exists(chemin):
            sound = AudioSegment.from_mp3(chemin)
            samples_loaded[corde] = sound
            loaded = True
        else:
            # Fallback mp3 corde ou sinus
            chemin_def = os.path.join(DOSSIER_SAMPLES, f"{corde}.mp3")
            if os.path.exists(chemin_def):
                samples_loaded[corde] = AudioSegment.from_mp3(chemin_def)
                loaded = True
        
        if not loaded:
            # Génération sinus si pas de sample
            tone = Sine(440).to_audio_segment(duration=1000).apply_gain(-5)
            samples_loaded[corde] = tone

    # 2. Calculs temporels (Base 12)
    # 1 Temps (Noire = 12 ticks) = 60000 / BPM ms
    ms_par_tick = (60000 / bpm) / TICKS_NOIRE
    
    dernier_tick = sequence[-1]['tick'] + sequence[-1]['duration']
    duree_totale_ms = int(dernier_tick * ms_par_tick) + 1000 # Marge de fin
    mix = AudioSegment.silent(duration=duree_totale_ms)

    # 3. Assemblage avec découpe (Slicing) et Fade Out
    for n in sequence:
        corde = n['corde']
        if corde in samples_loaded:
            start_ms = int(n['tick'] * ms_par_tick)
            duration_ticks = n['duration']
            
            # Durée théorique de la note
            note_ms = int(duration_ticks * ms_par_tick)
            
            # On prend le sample
            original_sample = samples_loaded[corde]
            
            # SI la note est courte (Croche/Double/Triolet), on la coupe !
            # On garde une petite marge (+50ms) pour que ça respire, sauf si très rapide
            len_to_keep = note_ms
            
            # Pour éviter de couper si le sample est déjà plus court
            if len(original_sample) > len_to_keep:
                # Slicing + Fade Out pour éviter le "CLIC"
                played_sample = original_sample[:len_to_keep].fade_out(15)
            else:
                played_sample = original_sample

            mix = mix.overlay(played_sample, position=start_ms)
            
    buffer = io.BytesIO()
    mix.export(buffer, format="mp3", bitrate="128k")
    buffer.seek(0)
    return buffer

# ==============================================================================
# 🎨 MOTEUR AFFICHAGE (ADAPTÉ BASE 12 & LIGATURES)
# ==============================================================================
def dessiner_contenu_legende(ax, styles):
    c_txt = styles['TEXTE']
    ax.text(0, 0, "LÉGENDE", ha='center', fontsize=20, color=c_txt)
    # Mise à jour avec les Emojis
    ax.text(0, -1, "+ = Noire | ♪ = Croche | 🎶 = Triolet | ♬ = Double", ha='center', color=c_txt)
    ax.axis('off')

def generer_page_notes(notes_page, idx, titre, config_acc, styles, options_visuelles):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    
    # Calcul des limites en Ticks
    tick_min = notes_page[0]['tick']
    tick_max = notes_page[-1]['tick'] + 12
    
    # Conversion Ticks -> Unités visuelles (1 Noire = 1.0 unité Y)
    hauteur_unites = (tick_max - tick_min) / 12.0
    hauteur_fig = max(6, hauteur_unites * 1.5 + 4) # Ajustement hauteur dynamique
    
    fig = Figure(figsize=(16, hauteur_fig), facecolor=c_fond)
    ax = fig.subplots()
    ax.set_facecolor(c_fond)
    
    y_top = 2.0
    y_start_notes = 0
    
    # Titre et Cordes
    prop_titre = get_font_cached(32, 'bold')
    ax.text(0, y_top + 1.5, f"{titre} (Page {idx})", ha='center', fontproperties=prop_titre, color=c_txt)
    
    # Lignes verticales Cordes
    y_bot_visuel = - ((tick_max - tick_min) / 12.0) - 1
    ax.vlines(0, y_bot_visuel, y_top, color=c_txt, lw=5, zorder=2) # Centre
    
    for code, props in config_acc.items():
        x = props['x']; note = props['n']
        c = get_color_for_note(note)
        ax.text(x, y_top + 0.5, note, ha='center', color=c, fontweight='bold')
        ax.vlines(x, y_bot_visuel, y_top, colors=c, lw=2, zorder=1)

    # Lignes horizontales (Temps / Noires)
    # On dessine une ligne tous les 12 ticks (toutes les noires)
    start_beat_tick = (tick_min // 12) * 12
    for t in range(start_beat_tick, tick_max + 12, 12):
        y = - ((t - tick_min) / 12.0)
        ax.axhline(y=y, color='#666666', lw=1, alpha=0.5, zorder=0.5)

    # DESSIN DES NOTES
    rayon = 0.30
    img_pouce = load_image_asset(CHEMIN_ICON_POUCE)
    img_index = load_image_asset(CHEMIN_ICON_INDEX)

    for n in notes_page:
        tick_relatif = n['tick'] - tick_min
        y = - (tick_relatif / 12.0)
        code = n['corde']
        
        if code == 'TEXTE':
            bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt)
            ax.text(0, y, n.get('message',''), ha='center', va='center', bbox=bbox, zorder=10)
        elif code == 'SILENCE':
            ax.text(0, y, "S", ha='center', va='center', fontweight='bold', color='red', zorder=10)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']
            c = get_color_for_note(props['n'])
            
            # Cercle
            ax.add_patch(patches.Circle((x, y), rayon, color=c_perle, zorder=3))
            ax.add_patch(patches.Circle((x, y), rayon, fill=False, edgecolor=c, lw=3, zorder=4))
            
            # Doigté
            if 'doigt' in n:
                d = n['doigt']
                img = img_index if d == 'I' else img_pouce
                if img is not None:
                    ab = AnnotationBbox(OffsetImage(img, zoom=0.04), (x-0.7, y), frameon=False, zorder=5)
                    ax.add_artist(ab)
            
    # LIGATURES VISUELLES (LINKS)
    # On relie les notes d'un même sous-groupe
    sorted_notes = sorted([n for n in notes_page if n['corde'] in config_acc], key=lambda x: x['tick'])
    for i in range(len(sorted_notes) - 1):
        n1 = sorted_notes[i]
        n2 = sorted_notes[i+1]
        
        # Si elles sont dans le même "Temps" (Beat) et sont des sous-divisions
        if n1['duration'] < 12 and n2['duration'] < 12:
            beat1 = n1['tick'] // 12
            beat2 = n2['tick'] // 12
            if beat1 == beat2:
                # Calcul Y
                y1 = - ((n1['tick'] - tick_min) / 12.0)
                y2 = - ((n2['tick'] - tick_min) / 12.0)
                
                # Barre de liaison (Ligature verticale)
                lw_link = 3 if n1['duration'] <= 4 else 1.5
                color_link = '#A67C52'
                
                # Double barre pour les doubles croches (durée 3 ticks)
                if n1['duration'] == 3:
                     ax.plot([-0.2, -0.2], [y1, y2], color=color_link, lw=lw_link, zorder=2, alpha=0.7)
                     ax.plot([-0.3, -0.3], [y1, y2], color=color_link, lw=lw_link, zorder=2, alpha=0.7)
                else:
                     ax.plot([-0.2, -0.2], [y1, y2], color=color_link, lw=lw_link, zorder=2, alpha=0.7)

    ax.set_xlim(-7.5, 7.5); ax.set_ylim(y_bot_visuel, y_top + 2); ax.axis('off')
    return fig

# --- GÉNÉRATION IMAGE LONGUE (Pour Vidéo) ---
def generer_image_longue_hd(sequence, config_acc, styles):
    tick_max = sequence[-1]['tick'] + 24
    height_units = tick_max / 12.0
    fig = Figure(figsize=(16, height_units * 0.8), dpi=100, facecolor=styles['FOND'])
    ax = fig.subplots(); ax.set_facecolor(styles['FOND'])
    
    y_top = 2.0; y_bot = - (height_units) - 2
    ax.vlines(0, y_bot, y_top, color='black', lw=5)
    
    # Cordes
    for code, props in config_acc.items():
        x = props['x']; c = get_color_for_note(props['n'])
        ax.text(x, y_top, code, ha='center', color=c, fontsize=14, fontweight='bold')
        ax.vlines(x, y_bot, y_top, colors=c, lw=2)
        
    # Notes
    for n in sequence:
        y = - (n['tick'] / 12.0)
        code = n['corde']
        if code in config_acc:
            props = config_acc[code]; x = props['x']; c = get_color_for_note(props['n'])
            ax.add_patch(patches.Circle((x, y), 0.3, color=styles['PERLE_FOND'], zorder=3))
            ax.add_patch(patches.Circle((x, y), 0.3, fill=False, edgecolor=c, lw=3, zorder=4))
        elif code == 'TEXTE':
            ax.text(0, y, n.get('message',''), ha='center', bbox=dict(fc='white'), zorder=10)
            
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(y_bot, y_top + 2); ax.axis('off')
    
    # Métriques pour vidéo
    px_y0 = ax.transData.transform((0,0))[1]
    px_y1 = ax.transData.transform((0,-1))[1] # 1 temps (Noire) plus bas
    px_per_beat = px_y0 - px_y1
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches=None)
    buf.seek(0)
    plt.close(fig)
    return buf, px_per_beat, (fig.get_figheight()*100 - px_y0)

# ==============================================================================
# 🎬 VIDÉO (Adaptée Base 12)
# ==============================================================================
HAS_MOVIEPY = False
try:
    from moviepy.editor import ImageClip, CompositeVideoClip, AudioFileClip, ColorClip
    HAS_MOVIEPY = True
except: pass

def creer_video_hd(image_buf, audio_buf, duration, metrics, bpm):
    if not HAS_MOVIEPY: return None
    px_per_beat, offset_px = metrics
    
    # Vitesse : Pixels par temps * (BPM / 60) = Pixels par seconde
    speed_px_sec = px_per_beat * (bpm / 60.0)
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_img: f_img.write(image_buf.getbuffer()); img_path = f_img.name
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f_aud: f_aud.write(audio_buf.getbuffer()); aud_path = f_aud.name
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f_vid: vid_path = f_vid.name
    
    try:
        clip_img = ImageClip(img_path)
        w, h = clip_img.size
        video_h = 720
        bar_y = 150
        
        start_pos_y = bar_y - offset_px
        
        def scroll(t): return ('center', start_pos_y - (speed_px_sec * t))
        
        moving = clip_img.set_position(scroll).set_duration(duration)
        bg = ColorClip(size=(w, video_h), color=(229, 196, 163)).set_duration(duration)
        bar = ColorClip(size=(w, 4), color=(255,0,0)).set_opacity(0.5).set_position(('center', bar_y)).set_duration(duration)
        
        final_video = CompositeVideoClip([bg, moving, bar], size=(w, video_h))
        audio = AudioFileClip(aud_path).subclip(0, duration)
        final_video = final_video.set_audio(audio)
        
        final_video.write_videofile(vid_path, fps=15, codec='libx264', audio_codec='aac', preset='ultrafast', logger=None)
        
        clip_img.close(); final_video.close(); audio.close()
        return vid_path
    except Exception as e:
        print(e); return None

# ==============================================================================
# 🧩 INTERFACE
# ==============================================================================
# Init Session
if 'init_done' not in st.session_state:
    st.session_state.update({
        'partition_buffers': [], 'generated': False, 'code_actuel': BANQUE_TABLATURES[list(BANQUE_TABLATURES.keys())[0]],
        'audio_buf': None, 'vid_path': None, 'stored_blocks': {}, 'init_done': True
    })
    for k, v in DEF_ACC.items(): st.session_state[f"acc_{k}"] = v

# Sidebar
with st.sidebar:
    st.header("🎚️ Menu")
    choix = st.selectbox("Bibliothèque", list(BANQUE_TABLATURES.keys()))
    if st.button("Charger"):
        st.session_state.code_actuel = BANQUE_TABLATURES[choix]
        st.session_state.generated = False
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 🎼 Nouveau Rythme")
    st.info("""
    **+** = Noire (1 temps)
    **♪** = Croche (1/2 temps)
    **🎶** = Triolet (1/3 temps)
    **♬** = Double (1/4 temps)
    """)

# Tabs
tab_acc, tab_edit, tab_media = st.tabs(["⚙️ Accordage", "📝 Éditeur", "🎬 Média"])

with tab_acc:
    st.caption("Configuration rapide")
    preset = st.selectbox("Gammes", list(GAMMES_PRESETS.keys()))
    if st.button("Appliquer Gamme"):
        parsed = parse_gamme_string(GAMMES_PRESETS[preset])
        for i, k in enumerate(ORDRE_MAPPING): st.session_state[f"acc_{k}"] = parsed[i]
        st.success("OK")

with tab_edit:
    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.subheader("Code")
        
        # Toolbar rapide (Mise à jour avec EMOJIS)
        c1, c2, c3, c4 = st.columns(4)
        def add_symbol(s): st.session_state.code_actuel += f"\n{s} "
        with c1: st.button("Noire (+)", on_click=add_symbol, args=("+",), use_container_width=True)
        with c2: st.button("Croche (♪)", on_click=add_symbol, args=("♪",), use_container_width=True)
        with c3: st.button("Triolet (🎶)", on_click=add_symbol, args=("🎶",), use_container_width=True)
        with c4: st.button("Double (♬)", on_click=add_symbol, args=("♬",), use_container_width=True)

        txt = st.text_area("Éditeur", value=st.session_state.code_actuel, height=400, key="widget_code")
        st.session_state.code_actuel = txt
        
        if st.button("🔄 Générer Partition", type="primary"):
            # Parsing
            seq = parser_texte(txt)
            
            # Config actuelle
            acc = {k: {'x': POSITIONS_X[k], 'n': st.session_state[f"acc_{k}"]} for k in POSITIONS_X}
            styles = {'FOND': '#e5c4a3', 'TEXTE': 'black', 'PERLE_FOND': '#e5c4a3'}
            
            # Génération images pages
            bufs = []
            chunk_size = 144
            if not seq: seq = []
            current_chunk = []
            last_tick = 0
            
            pages = []
            current_page = []
            page_tick_start = 0
            
            for n in seq:
                if n['corde'] == 'PAGE_BREAK' or (n['tick'] - page_tick_start > 144):
                    if current_page: pages.append(current_page)
                    current_page = []
                    page_tick_start = n['tick']
                if n['corde'] != 'PAGE_BREAK':
                    current_page.append(n)
            if current_page: pages.append(current_page)
            
            st.session_state.partition_buffers = []
            for i, p in enumerate(pages):
                fig = generer_page_notes(p, i+1, "Tablature", acc, styles, {})
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', facecolor='#e5c4a3')
                buf.seek(0)
                st.session_state.partition_buffers.append({'img': buf})
                plt.close(fig)
            
            st.session_state.generated = True
            
    with col2:
        st.subheader("Aperçu")
        if st.session_state.generated:
            for b in st.session_state.partition_buffers:
                st.image(b['img'])

with tab_media:
    col_a, col_v = st.columns(2)
    acc = {k: {'x': POSITIONS_X[k], 'n': st.session_state[f"acc_{k}"]} for k in POSITIONS_X}
    
    with col_a:
        st.subheader("Audio")
        bpm = st.number_input("BPM", 60, 200, 90)
        if st.button("🎵 Générer MP3"):
            seq = parser_texte(st.session_state.code_actuel)
            mp3 = generer_audio_mix(seq, bpm, acc)
            if mp3:
                st.audio(mp3, format="audio/mp3")
                st.session_state.audio_buf = mp3
    
    with col_v:
        st.subheader("Vidéo")
        if st.button("🎥 Générer MP4"):
            if st.session_state.audio_buf:
                status = st.status("Génération vidéo...")
                seq = parser_texte(st.session_state.code_actuel)
                styles = {'FOND': '#e5c4a3', 'TEXTE': 'black', 'PERLE_FOND': '#e5c4a3'}
                img_long, px_beat, offset = generer_image_longue_hd(seq, acc, styles)
                
                ms_per_tick = (60000 / bpm) / 12
                total_ms = seq[-1]['tick'] * ms_per_tick + 2000
                
                vid = creer_video_hd(img_long, st.session_state.audio_buf, total_ms/1000, (px_beat, offset), bpm)
                if vid:
                    st.video(vid)
                    status.update(label="Terminé", state="complete")
            else:
                st.error("Générez l'audio d'abord !")