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
from PIL import Image 

# ==============================================================================
# 📦 INSTALLATION REQUISE POUR LE VISUEL
# ==============================================================================
try:
    from streamlit_image_coordinates import streamlit_image_coordinates
    HAS_CLICK_COORD = True
except ImportError:
    HAS_CLICK_COORD = False

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

st.set_page_config(
    page_title="Générateur Tablature Ngonilélé", 
    layout="wide", 
    page_icon=icon_page,
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 📦 GESTION DE LA PERSISTANCE
# ==============================================================================
if 'partition_buffers' not in st.session_state: st.session_state.partition_buffers = []
if 'partition_generated' not in st.session_state: st.session_state.partition_generated = False
if 'video_path' not in st.session_state: st.session_state.video_path = None
if 'audio_buffer' not in st.session_state: st.session_state.audio_buffer = None
if 'metronome_buffer' not in st.session_state: st.session_state.metronome_buffer = None
if 'code_actuel' not in st.session_state: st.session_state.code_actuel = ""
if 'last_click_value' not in st.session_state: st.session_state.last_click_value = None

# ==============================================================================
# 🚨 MESSAGE D'AIDE
# ==============================================================================
if st.session_state.get('first_run', True):
    st.info("👈 **CLIQUEZ SUR LA FLÈCHE GRISE 'MENU' EN HAUT À GAUCHE** pour choisir un morceau, changer l'apparence (imprimer en fond blanc) ou m'envoyer ta tablature !")

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

col_logo, col_titre = st.columns([1, 5])
with col_logo:
    if os.path.exists(CHEMIN_LOGO_APP): st.image(CHEMIN_LOGO_APP, width=100)
    else: st.header("🪕")
with col_titre:
    st.title("Générateur de Tablature Ngonilélé")
    st.markdown("Composez, Écoutez et Exportez.")

with st.expander("❓ Comment ça marche ? (Mode d'emploi)"):
    st.markdown("""
    1.  **Menu Gauche** : Réglages et Accordage.
    2.  **Saisie** : Cliquez sur le manche visuel ou utilisez les boutons.
    3.  **Audio** : Générez le MP3 ou lancez le Métronome.
    4.  **Exports** : Téléchargez le PDF (Livret) ou la Vidéo.
    """)

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

def generer_audio_mix(sequence, bpm, acc_config):
    if not HAS_PYDUB: st.error("❌ Pydub manquant."); return None
    if not sequence: return None
    
    samples_loaded = {}
    cordes_utilisees = set([n['corde'] for n in sequence if n['corde'] in POSITIONS_X])
    
    for corde in cordes_utilisees:
        loaded = False
        if os.path.exists(DOSSIER_SAMPLES):
            nom_fichier = f"{corde}.mp3"
            chemin = os.path.join(DOSSIER_SAMPLES, nom_fichier)
            if os.path.exists(chemin): 
                samples_loaded[corde] = AudioSegment.from_mp3(chemin)
                loaded = True
            else:
                chemin_min = os.path.join(DOSSIER_SAMPLES, f"{corde.lower()}.mp3")
                if os.path.exists(chemin_min): 
                    samples_loaded[corde] = AudioSegment.from_mp3(chemin_min)
                    loaded = True
        
        if not loaded:
            note_name = 'C' 
            if corde in acc_config: note_name = acc_config[corde]['n']
            freq = get_note_freq(note_name)
            tone = Sine(freq).to_audio_segment(duration=600).fade_out(400)
            samples_loaded[corde] = tone - 5 

    if not samples_loaded: 
        st.error("Aucun son généré."); return None

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
    silence_acc = ms_per_beat - len(sound_accent)
    silence_norm = ms_per_beat - len(sound_normal)
    if silence_acc < 0: silence_acc = 0
    if silence_norm < 0: silence_norm = 0
    beat_accent = sound_accent + AudioSegment.silent(duration=silence_acc)
    beat_normal = sound_normal + AudioSegment.silent(duration=silence_norm)
    if signature == "3/4": measure_block = beat_accent + beat_normal + beat_normal
    else: measure_block = beat_accent + beat_normal + beat_normal + beat_normal
    nb_mesures = int((duration_sec * 1000) / len(measure_block)) + 1
    metronome_track = measure_block * nb_mesures
    metronome_track = metronome_track[:int(duration_sec*1000)]
    buffer = io.BytesIO()
    metronome_track.export(buffer, format="mp3")
    buffer.seek(0)
    return buffer

# ==============================================================================
# 🎨 MOTEUR AFFICHAGE & VISUEL INTERACTIF (FIABLE)
# ==============================================================================

# Mapping précis des positions X (Unité arbitraire pour Matplotlib)
# On imagine un espace de 0 à 14. Tige au milieu (7).
X_POS_MAP = {
    '6G': 1, '5G': 2, '4G': 3, '3G': 4, '2G': 5, '1G': 6,
    '1D': 8, '2D': 9, '3D': 10, '4D': 11, '5D': 12, '6D': 13
}

def dessiner_interface_ngoni_style_img(config_acc):
    """
    Crée une image du N'goni compacte et propre.
    """
    fig, ax = plt.subplots(figsize=(10, 3), facecolor='#e5c4a1')
    ax.set_facecolor('#e5c4a1')
    
    # Tige centrale
    ax.axvline(x=7, color='black', linewidth=4)
    
    def get_col(corde_key):
        note = config_acc[corde_key]['n']
        return COULEURS_CORDES_REF.get(note, '#333333')

    # Dessin des cordes selon X_POS_MAP
    for code, x in X_POS_MAP.items():
        col = get_col(code)
        
        # Le nom de la corde (1G, 2G...) en haut
        ax.text(x, 2.2, code, ha='center', va='center', color=col, fontweight='bold', fontsize=14)
        
        # Bulle visuelle (déco)
        circle = plt.Circle((x, 1.8), 0.3, color=col, ec='black', zorder=2)
        ax.add_patch(circle)
        
        # La corde
        ax.plot([x, x], [0, 1.6], color=col, linewidth=3, zorder=1)

    ax.set_xlim(0, 14)
    ax.set_ylim(0, 2.5)
    ax.axis('off')
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', facecolor='#e5c4a1', pad_inches=0)
    plt.close(fig)
    buf.seek(0) 
    return buf

def traiter_clic_ngoni_fiable(x_pixel, width_image_pixel):
    """
    Logique du plus proche voisin.
    On projette le clic pixel sur l'échelle 0-14 du dessin.
    """
    if width_image_pixel == 0: return None
    
    # L'image générée a un xlim(0, 14).
    x_projeté = (x_pixel / width_image_pixel) * 14.0
    
    # On cherche quelle corde est la plus proche de x_projeté
    meilleure_corde = None
    dist_min = 1000
    
    for code, x_cible in X_POS_MAP.items():
        dist = abs(x_projeté - x_cible)
        if dist < dist_min:
            dist_min = dist
            meilleure_corde = code
            
    # Seuil de sécurité : si on clique trop loin d'une corde (ex: milieu vide), on ignore ?
    # Ici, avec un seuil de 0.8, ça couvre tout confortablement.
    if dist_min < 0.8:
        return meilleure_corde
    return None

def dessiner_contenu_legende(ax, y_pos, styles, mode_white=False):
    c_txt = styles['TEXTE']; c_fond = styles['LEGENDE_FOND']; c_bulle = styles['PERLE_FOND']
    prop_annotation = get_font(16, 'bold'); prop_legende = get_font(12, 'bold')
    path_pouce = CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE
    path_index = CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX
    rect = patches.FancyBboxPatch((-7.5, y_pos - 3.6), 15, 3.3, boxstyle="round,pad=0.1", linewidth=1.5, edgecolor=c_txt, facecolor=c_fond, zorder=0); ax.add_patch(rect)
    ax.text(0, y_pos - 0.6, "LÉGENDE", ha='center', va='center', fontsize=14, fontweight='bold', color=c_txt, fontproperties=prop_annotation)
    x_icon_center = -5.5; x_text_align = -4.5; y_row1 = y_pos - 1.2; y_row2 = y_pos - 1.8; y_row3 = y_pos - 2.4; y_row4 = y_pos - 3.0
    if os.path.exists(path_pouce): ab = AnnotationBbox(OffsetImage(mpimg.imread(path_pouce), zoom=0.045), (x_icon_center, y_row1), frameon=False); ax.add_artist(ab)
    ax.text(x_text_align, y_row1, "= Pouce", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    if os.path.exists(path_index): ab = AnnotationBbox(OffsetImage(mpimg.imread(path_index), zoom=0.045), (x_icon_center, y_row2), frameon=False); ax.add_artist(ab)
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
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; prop_titre = get_font(32, 'bold')
    fig, ax = plt.subplots(figsize=(16, 8), facecolor=c_fond)
    ax.set_facecolor(c_fond)
    ax.text(0, 2.5, titre, ha='center', va='bottom', fontproperties=prop_titre, color=c_txt)
    dessiner_contenu_legende(ax, 0.5, styles, mode_white)
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(-6, 4); ax.axis('off')
    return fig

def generer_page_notes(notes_page, idx, titre, config_acc, styles, options_visuelles, mode_white=False):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    path_pouce = CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE
    path_index = CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX
    t_min = notes_page[0]['temps']; t_max = notes_page[-1]['temps']; lignes_sur_page = t_max - t_min + 1; hauteur_fig = max(6, (lignes_sur_page * 0.75) + 6)
    fig, ax = plt.subplots(figsize=(16, hauteur_fig), facecolor=c_fond); ax.set_facecolor(c_fond)
    y_top = 2.5; y_bot = - (t_max - t_min) - 1.5; y_top_cordes = y_top
    prop_titre = get_font(32, 'bold'); prop_texte = get_font(20, 'bold'); prop_note_us = get_font(24, 'bold'); prop_note_eu = get_font(18, 'normal', 'italic'); prop_numero = get_font(14, 'bold'); prop_standard = get_font(14, 'bold'); prop_annotation = get_font(16, 'bold')
    if not mode_white and options_visuelles['use_bg'] and os.path.exists(CHEMIN_IMAGE_FOND):
        try: img_fond = mpimg.imread(CHEMIN_IMAGE_FOND); h_px, w_px = img_fond.shape[:2]; ratio = w_px / h_px; largeur_finale = 15.0 * 0.7; hauteur_finale = (largeur_finale / ratio) * 1.4; y_center = (y_top + y_bot) / 2; extent = [-largeur_finale/2, largeur_finale/2, y_center - hauteur_finale/2, y_center + hauteur_finale/2]; ax.imshow(img_fond, extent=extent, aspect='auto', zorder=-1, alpha=options_visuelles['alpha'])
        except: pass
    ax.text(0, y_top + 3.0, f"{titre} (Page {idx})", ha='center', va='bottom', fontproperties=prop_titre, color=c_txt)
    ax.text(-3.5, y_top_cordes + 2.0, "Cordes de Gauche", ha='center', va='bottom', fontproperties=prop_texte, color=c_txt); ax.text(3.5, y_top_cordes + 2.0, "Cordes de Droite", ha='center', va='bottom', fontproperties=prop_texte, color=c_txt)
    ax.vlines(0, y_bot, y_top_cordes + 1.8, color=c_txt, lw=5, zorder=2)
    for code, props in config_acc.items():
        x = props['x']; note = props['n']; c = COULEURS_CORDES_REF.get(note, '#000000')
        ax.text(x, y_top_cordes + 1.3, code, ha='center', color='gray', fontproperties=prop_numero); ax.text(x, y_top_cordes + 0.7, note, ha='center', color=c, fontproperties=prop_note_us); ax.text(x, y_top_cordes + 0.1, TRADUCTION_NOTES.get(note, '?'), ha='center', color=c, fontproperties=prop_note_eu); ax.vlines(x, y_bot, y_top_cordes, colors=c, lw=3, zorder=1)
    
    for t in range(t_min, t_max + 1):
        y = -(t - t_min)
        ax.axhline(y=y, color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)

    map_labels = {}; last_sep = t_min - 1; sorted_notes = sorted(notes_page, key=lambda x: x['temps']); processed_t = set()
    for n in sorted_notes:
        t = n['temps']; 
        if n['corde'] in ['SEPARATOR', 'TEXTE']: last_sep = t
        elif t not in processed_t: map_labels[t] = str(t - last_sep); processed_t.add(t)
    notes_par_temps = {}; rayon = 0.30
    for n in notes_page:
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
                doigt = n['doigt']; img_path = path_index if doigt == 'I' else path_pouce
                if os.path.exists(img_path):
                    try: ab = AnnotationBbox(OffsetImage(mpimg.imread(img_path), zoom=0.045), (x - 0.70, y + 0.1), frameon=False, zorder=8); ax.add_artist(ab)
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
    buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=DPI, facecolor=c_fond, bbox_inches=None); plt.close(fig); buf.seek(0)
    return buf, pixels_par_temps, offset_premiere_note_px

def generer_pdf_livret(buffers, titre):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    for item in buffers:
        pdf.add_page()
        temp_img = f"temp_pdf_{item['type']}_{item.get('idx', 0)}.png"
        with open(temp_img, "wb") as f: f.write(item['buf'].getbuffer())
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

def mise_a_jour_texte(): 
    st.session_state.code_actuel = st.session_state.widget_input
    st.session_state.partition_generated = False
    st.session_state.video_path = None
    st.session_state.audio_buffer = None

def ajouter_texte(txt):
    if 'code_actuel' in st.session_state:
        st.session_state.code_actuel += "\n" + txt
    else:
        st.session_state.code_actuel = txt
    st.session_state.widget_input = st.session_state.code_actuel

def annuler_derniere_ligne():
    lines = st.session_state.code_actuel.strip().split('\n')
    if len(lines) > 0:
        st.session_state.code_actuel = "\n".join(lines[:-1])
        st.session_state.widget_input = st.session_state.code_actuel

with st.sidebar:
    st.header("🎚️ Réglages")
    
    st.markdown("### 📚 Banque de Morceaux")
    st.selectbox("Choisir un morceau :", options=list(BANQUE_TABLATURES.keys()), key='selection_banque', on_change=charger_morceau)
    st.caption("⚠️ Remplacera le texte actuel.")

    st.markdown("---")
    
    with st.expander("🎨 Apparence", expanded=False):
        bg_color = st.color_picker("Couleur de fond", "#e5c4a1")
        use_bg_img = st.checkbox("Texture Ngonilélé (si image présente)", True)
        bg_alpha = st.slider("Transparence Texture", 0.0, 1.0, 0.2)
        st.markdown("---")
        force_white_print = st.checkbox("🖨️ Fond blanc pour impression", value=True)

    st.markdown("---")
    st.markdown("### 🤝 Contribuer")
    mon_email = "julienflorin59@gmail.com" 
    sujet_mail = f"Nouvelle Tablature Ngonilélé"
    corps_mail = f"Bonjour,\n\nVoici une proposition :\n\n{st.session_state.code_actuel}"
    mailto_link = f"mailto:{mon_email}?subject={urllib.parse.quote(sujet_mail)}&body={urllib.parse.quote(corps_mail)}"
    st.markdown(f'<a href="{mailto_link}" target="_blank"><button style="width:100%; background-color:#FF4B4B; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">📧 Envoyer ma partition</button></a>', unsafe_allow_html=True)


tab1, tab2, tab3, tab4 = st.tabs(["📝 Éditeur & Partition", "⚙️ Accordage", "🎬 Vidéo (Bêta)", "🎧 Audio & Groove"])

with tab2:
    st.subheader("Configuration des cordes")
    col_g, col_d = st.columns(2)
    acc_config = {}
    notes_gamme = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
    DEF_ACC = {'1G':'G','2G':'C','3G':'E','4G':'A','5G':'C','6G':'G','1D':'F','2D':'A','3D':'D','4D':'G','5D':'B','6D':'E'}
    with col_g:
        st.write("**Main Gauche**")
        for i in range(1, 7):
            k = f"{i}G"; val = st.selectbox(f"Corde {k}", notes_gamme, index=notes_gamme.index(DEF_ACC[k]), key=k)
            acc_config[k] = {'x': POSITIONS_X[k], 'n': val}
    with col_d:
        st.write("**Main Droite**")
        for i in range(1, 7):
            k = f"{i}D"; val = st.selectbox(f"Corde {k}", notes_gamme, index=notes_gamme.index(DEF_ACC[k]), key=k)
            acc_config[k] = {'x': POSITIONS_X[k], 'n': val}

with tab1:
    titre_partition = st.text_input("Titre de la partition", "Tablature Ngonilélé")
    
    col_input, col_view = st.columns([1, 1.5])
    with col_input:
        st.subheader("🎛️ Studio de Composition")
        
        # --- 1. BOUTONS CLASSIQUES (PRIORITAIRES) ---
        with st.expander("⌨️ Saisie par Boutons (Classique)", expanded=True):
            st.caption("Main Gauche")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.button("1G", on_click=ajouter_texte, args=("+ 1G",), use_container_width=True)
            c2.button("2G", on_click=ajouter_texte, args=("+ 2G",), use_container_width=True)
            c3.button("3G", on_click=ajouter_texte, args=("+ 3G",), use_container_width=True)
            c4.button("4G", on_click=ajouter_texte, args=("+ 4G",), use_container_width=True)
            c5.button("5G", on_click=ajouter_texte, args=("+ 5G",), use_container_width=True)
            c6.button("6G", on_click=ajouter_texte, args=("+ 6G",), use_container_width=True)
            
            st.caption("Main Droite")
            d1, d2, d3, d4, d5, d6 = st.columns(6)
            d1.button("1D", on_click=ajouter_texte, args=("+ 1D",), use_container_width=True)
            d2.button("2D", on_click=ajouter_texte, args=("+ 2D",), use_container_width=True)
            d3.button("3D", on_click=ajouter_texte, args=("+ 3D",), use_container_width=True)
            d4.button("4D", on_click=ajouter_texte, args=("+ 4D",), use_container_width=True)
            d5.button("5D", on_click=ajouter_texte, args=("+ 5D",), use_container_width=True)
            d6.button("6D", on_click=ajouter_texte, args=("+ 6D",), use_container_width=True)
            
            st.caption("Outils")
            o1, o2, o3, o4, o5 = st.columns(5)
            o1.button("Simul (=)", on_click=ajouter_texte, args=("=",), use_container_width=True)
            o2.button("x2", on_click=ajouter_texte, args=("x2",), use_container_width=True)
            o3.button("Silence", on_click=ajouter_texte, args=("+ S",), use_container_width=True)
            o4.button("Annuler", on_click=annuler_derniere_ligne, use_container_width=True)
            o5.button("Page", on_click=ajouter_texte, args=("+ PAGE",), use_container_width=True)

        st.write("")

        # --- 2. MODE VISUEL INTERACTIF (DANS UN EXPANDER) ---
        if HAS_CLICK_COORD:
            with st.expander("🎨 Saisie Visuelle Interactive (Manche)", expanded=False):
                col_opt1, col_opt2, col_opt3 = st.columns(3)
                with col_opt1: mode_ajout = st.radio("Mode", ["Suivant (+)", "Simultané (=)"], horizontal=True, label_visibility="collapsed")
                with col_opt2: is_x2 = st.checkbox("Doubler (x2)")
                with col_opt3: is_silence = st.button("🔇 Silence Visuel")

                if is_silence: ajouter_texte("+ S")

                # Image interactive (buffer PNG)
                img_buf = dessiner_interface_ngoni_style_img(acc_config)
                
                # Conversion PIL
                img_pil = Image.open(img_buf)
                value = streamlit_image_coordinates(img_pil, key="ngoni_click")

                # Logique d'ajout sur clic (Plus robuste)
                if value and value != st.session_state.last_click_value:
                    st.session_state.last_click_value = value
                    x_clic = value['x']
                    # Notre image matplotlib fait 10 inches de large avec dpi par défaut (100) -> 1000px
                    width_img = 1000 
                    
                    corde_detectee = traiter_clic_ngoni_fiable(x_clic, width_img)
                    
                    if corde_detectee:
                        prefix = "+ " if mode_ajout == "Suivant (+)" else "= "
                        suffix = " x2" if is_x2 else ""
                        txt_to_add = f"{prefix}{corde_detectee}{suffix}"
                        ajouter_texte(txt_to_add)
                        st.toast(f"Note ajoutée : {corde_detectee}")
                        st.rerun() 
        else:
            st.warning("⚠️ Installez 'streamlit-image-coordinates' pour activer le manche interactif.")

        # --- ÉDITEUR TEXTE ---
        st.markdown("---")
        st.text_area("Éditeur Texte (Lecture Seule / Copie)", value=st.session_state.code_actuel, height=300, key="widget_input", on_change=mise_a_jour_texte)
        
        col_play_btn, col_play_bpm = st.columns([1, 1])
        with col_play_bpm:
            bpm_preview = st.number_input("BPM Aperçu", 40, 200, 100)
        with col_play_btn:
            st.write("") 
            st.write("") 
            if st.button("🎧 Écouter l'extrait"):
                with st.status("🎵 Génération...", expanded=True) as status:
                    seq_prev = parser_texte(st.session_state.code_actuel)
                    audio_prev = generer_audio_mix(seq_prev, bpm_preview, acc_config)
                    status.update(label="✅ Prêt !", state="complete", expanded=False)
                if audio_prev:
                    st.audio(audio_prev, format="audio/mp3")

        with st.expander("Gérer le fichier"):
            st.download_button(label="💾 Sauvegarder (.txt)", data=st.session_state.code_actuel, file_name=f"{titre_partition.replace(' ', '_')}.txt", mime="text/plain")
            uploaded_file = st.file_uploader("📂 Charger (.txt)", type="txt")
            if uploaded_file:
                stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
                st.session_state.code_actuel = stringio.read()
                st.rerun()
        
    with col_view:
        st.subheader("Aperçu Partition")
        if st.button("🔄 Générer la partition", type="primary", use_container_width=True):
            st.session_state.partition_buffers = [] 
            
            styles_ecran = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
            styles_print = {'FOND': 'white', 'TEXTE': 'black', 'PERLE_FOND': 'white', 'LEGENDE_FOND': 'white'}
            options_visuelles = {'use_bg': use_bg_img, 'alpha': bg_alpha}
            # Pour l'aperçu, on utilise status pour faire joli aussi
            with st.status("📸 Génération des images...", expanded=True) as status:
                sequence = parser_texte(st.session_state.code_actuel)
                
                # 1. Légende
                st.write("📖 Création de la légende...")
                fig_leg_ecran = generer_page_1_legende(titre_partition, styles_ecran, mode_white=False)
                if force_white_print: fig_leg_dl = generer_page_1_legende(titre_partition, styles_print, mode_white=True)
                else: fig_leg_dl = fig_leg_ecran
                buf_leg = io.BytesIO(); fig_leg_dl.savefig(buf_leg, format="png", dpi=200, facecolor=styles_print['FOND'] if force_white_print else bg_color, bbox_inches='tight'); buf_leg.seek(0)
                st.session_state.partition_buffers.append({'type':'legende', 'buf': buf_leg, 'img_ecran': fig_leg_ecran})
                if force_white_print: plt.close(fig_leg_dl)
                
                # 2. Pages
                pages_data = []; current_page = []
                for n in sequence:
                    if n['corde'] == 'PAGE_BREAK':
                        if current_page: pages_data.append(current_page); current_page = []
                    else: current_page.append(n)
                if current_page: pages_data.append(current_page)
                
                if not pages_data: st.warning("Aucune note détectée.")
                else:
                    st.write(f"📄 Traitement de {len(pages_data)} pages...")
                    for idx, page in enumerate(pages_data):
                        fig_ecran = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_ecran, options_visuelles, mode_white=False)
                        if force_white_print: fig_dl = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_print, options_visuelles, mode_white=True)
                        else: fig_dl = fig_ecran
                        buf = io.BytesIO(); fig_dl.savefig(buf, format="png", dpi=200, facecolor=styles_print['FOND'] if force_white_print else bg_color, bbox_inches='tight'); buf.seek(0)
                        st.session_state.partition_buffers.append({'type':'page', 'idx': idx+2, 'buf': buf, 'img_ecran': fig_ecran})
                        if force_white_print: plt.close(fig_dl)
                
                st.session_state.partition_generated = True
                status.update(label="✅ Partition prête !", state="complete", expanded=False)

        # --- AFFICHAGE PERSISTANT ---
        if st.session_state.partition_generated and st.session_state.partition_buffers:
            # --- EXPORT PDF EN FIN DE CHAINE ---
            pdf_buffer = generer_pdf_livret(st.session_state.partition_buffers, titre_partition)
            
            st.download_button(
                label="📕 Télécharger le Livret Complet (PDF Portrait)",
                data=pdf_buffer,
                file_name=f"{titre_partition}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            
            st.markdown("---")

            for item in st.session_state.partition_buffers:
                if item['type'] == 'legende':
                    st.markdown("#### Page 1 : Légende")
                    st.pyplot(item['img_ecran'])
                elif item['type'] == 'page':
                    idx = item['idx']
                    st.markdown(f"#### Page {idx}")
                    st.pyplot(item['img_ecran'])

# --- TAB VIDEO ---
with tab3:
    st.subheader("Générateur de Vidéo Défilante 🎥")
    st.warning("⚠️ Sur la version gratuite, évitez les morceaux trop longs.")
    
    if not HAS_MOVIEPY:
        st.error("❌ Le module 'moviepy' n'est pas installé.")
    elif not HAS_PYDUB:
        st.error("❌ Le module 'pydub' n'est pas installé.")
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
            btn_video = st.button("🎥 Générer Vidéo + Audio")

        if btn_video:
            with st.status("🎬 Création de la vidéo en cours...", expanded=True) as status:
                st.write("🎹 Étape 1/3 : Mixage Audio...")
                sequence = parser_texte(st.session_state.code_actuel)
                audio_buffer = generer_audio_mix(sequence, bpm, acc_config)
                
                if audio_buffer:
                    st.write("🎨 Étape 2/3 : Création des visuels...")
                    styles_video = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
                    img_buffer, px_par_temps, offset_px = generer_image_longue_calibree(sequence, acc_config, styles_video)
                    
                    if img_buffer:
                        st.write("🎞️ Étape 3/3 : Montage vidéo (Patientez, c'est lourd !)...")
                        progress_bar = st.progress(0)
                        try:
                            progress_bar.progress(30)
                            video_path = creer_video_avec_son_calibree(img_buffer, audio_buffer, duree_estimee, (px_par_temps, offset_px), bpm)
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
                st.download_button(label="⬇️ Télécharger la Vidéo", data=file, file_name="ngoni_video_synchro.mp4", mime="video/mp4")

# --- TAB AUDIO (ET GROOVE BOX) ---
with tab4:
    col_gauche, col_droite = st.columns(2)
    
    with col_gauche:
        st.subheader("🎧 Générateur Audio")
        if not HAS_PYDUB:
             st.error("❌ Le module 'pydub' n'est pas installé.")
        else:
            bpm_audio = st.slider("Vitesse Morceau (BPM)", 30, 200, 100, key="bpm_audio")
            btn_audio = st.button("🎵 Générer MP3 du Morceau")
            
            if btn_audio:
                with st.status("🎵 Mixage en cours...", expanded=True) as status:
                    sequence = parser_texte(st.session_state.code_actuel)
                    mp3_buffer = generer_audio_mix(sequence, bpm_audio, acc_config)
                    if mp3_buffer:
                        st.session_state.audio_buffer = mp3_buffer
                        status.update(label="✅ Mixage terminé !", state="complete", expanded=False)
                        st.success("Terminé !")

            if st.session_state.audio_buffer:
                st.audio(st.session_state.audio_buffer, format="audio/mp3")
                st.download_button(label="⬇️ Télécharger le MP3", data=st.session_state.audio_buffer, file_name=f"{titre_partition.replace(' ', '_')}.mp3", mime="audio/mpeg")

    with col_droite:
        st.subheader("🥁 Groove Box (Métronome)")
        st.info("Un outil simple pour s'entraîner en rythme.")
        
        col_sig, col_bpm_metro = st.columns([1, 2])
        with col_sig:
             signature_metro = st.radio("Signature", ["4/4", "3/4"], horizontal=True)
        with col_bpm_metro:
             bpm_metro = st.slider("Vitesse (BPM)", 30, 200, 80, key="bpm_metro")

        duree_metro = st.slider("Durée (secondes)", 10, 300, 60, step=10)
        
        if st.button("▶️ Lancer le Métronome"):
            with st.status("🥁 Création du beat...", expanded=True) as status:
                metro_buffer = generer_metronome(bpm_metro, duree_metro, signature_metro)
                if metro_buffer:
                    st.session_state.metronome_buffer = metro_buffer
                    status.update(label="✅ Prêt !", state="complete", expanded=False)
        
        if st.session_state.metronome_buffer:
            st.audio(st.session_state.metronome_buffer, format="audio/mp3")