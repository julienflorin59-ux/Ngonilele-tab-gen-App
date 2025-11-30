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

# ==============================================================================
# ⚙️ CONFIGURATION & CHEMINS
# ==============================================================================
CHEMIN_POLICE = 'ML.ttf' 
CHEMIN_IMAGE_FOND = 'texture_ngonilele.png'
CHEMIN_ICON_POUCE = 'icon_pouce.png'
CHEMIN_ICON_INDEX = 'icon_index.png'
CHEMIN_ICON_POUCE_BLANC = 'icon_pouce_blanc.png'
CHEMIN_ICON_INDEX_BLANC = 'icon_index_blanc.png'
CHEMIN_LOGO_APP = 'ico_ngonilele.png' # Image de l'instrument
DOSSIER_SAMPLES = 'samples'

# Définition du Favicon (Image de l'instrument si trouvée)
icon_page = CHEMIN_LOGO_APP if os.path.exists(CHEMIN_LOGO_APP) else "🪕"

# Configuration de la page
st.set_page_config(
    page_title="Générateur Tablature Ngonilélé", 
    layout="wide", 
    page_icon=icon_page, # Utilisation de l'image ici
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
if 'debug_info' not in st.session_state: st.session_state.debug_info = ""

# ==============================================================================
# 🧠 MOTEUR LOGIQUE
# ==============================================================================
HAS_MOVIEPY = False
try:
    from moviepy.editor import ImageClip, CompositeVideoClip, AudioFileClip, ColorClip, TextClip
    HAS_MOVIEPY = True
except ImportError:
    try:
        from moviepy.editor import ImageClip, CompositeVideoClip, AudioFileClip
        from moviepy.video.VideoClip import ColorClip, TextClip
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

DPI = 100
FIG_HEIGHT = 12 

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
    
    buffer = io.BytesIO(); metronome_track.export(buffer, format="mp3"); buffer.seek(0)
    return buffer

# ==============================================================================
# 🎨 MOTEUR AFFICHAGE
# ==============================================================================
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
    for n in sorted_notes:
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
    offset_premiere_note_px = ax.get_window_extent().height - px_y_t0 
    buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=DPI, facecolor=c_fond, bbox_inches=None); plt.close(fig); buf.seek(0)
    return buf, pixels_par_temps, offset_premiere_note_px

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
# 🎬 MOTEUR VIDÉO
# ==============================================================================
def generer_image_longue_calibree(sequence, config_acc, styles):
    return generer_page_notes(sequence, 1, "", config_acc, styles, {'use_bg':True, 'alpha':0.2}, mode_white=False)

def creer_video_avec_son_calibree(img_buffer, audio_buffer, duree_estimee, calib_data, bpm):
    if not HAS_MOVIEPY: return None
    px_par_temps, offset_px = calib_data
    temp_img = "temp_long_score.png"
    temp_audio = "temp_audio_mix.mp3"
    temp_video = "temp_video_final.mp4"
    with open(temp_img, "wb") as f: f.write(img_buffer.getbuffer())
    with open(temp_audio, "wb") as f: f.write(audio_buffer.getbuffer())
    clip_img = ImageClip(temp_img)
    audio_clip = AudioFileClip(temp_audio)
    temps_par_sec = bpm / 60.0
    vitesse_defilement = px_par_temps * temps_par_sec
    w, h = clip_img.size
    H_VIDEO = 720
    W_VIDEO = 1280
    
    def scroll_func(t):
        y_start = (H_VIDEO / 3) - offset_px
        y_current = y_start - (vitesse_defilement * t)
        x_center = (W_VIDEO - w) // 2
        return (x_center, int(y_current))

    bg_clip = ColorClip(size=(W_VIDEO, H_VIDEO), color=(30,30,30), duration=audio_clip.duration + 2)
    moving_score = clip_img.set_pos(scroll_func).set_duration(audio_clip.duration + 2)
    barre = ColorClip(size=(W_VIDEO, 5), color=(255, 0, 0), duration=audio_clip.duration + 2).set_pos((0, H_VIDEO/3))
    
    final = CompositeVideoClip([bg_clip, moving_score, barre])
    final = final.set_audio(audio_clip)
    final.write_videofile(temp_video, fps=24, codec='libx264', audio_codec='aac', logger=None)
    try:
        os.remove(temp_img)
        os.remove(temp_audio)
    except: pass
    return temp_video

# ==============================================================================
# 🎛️ INTERFACE STREAMLIT
# ==============================================================================
BANQUE_TABLATURES = {
    "--- Nouveau / Vide ---": "",
    "Manitoumani": "1 4D\n+ 4G\n+ 5D\n+ 5G\n+ 4G\n= 2D\n+ 3G\n+ 6D x2"
}

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

def ajouter_texte(txt, msg_toast=None):
    if 'code_actuel' in st.session_state:
        st.session_state.code_actuel += "\n" + txt
    else:
        st.session_state.code_actuel = txt
    st.session_state.widget_input = st.session_state.code_actuel
    
    # Feedback visuel (Toast) pour tout ajout
    if msg_toast:
        st.toast(msg_toast, icon="✅")
    else:
        display_txt = txt.replace("+", "").strip()
        if display_txt == "=": display_txt = "Simultané"
        if display_txt == "x2": display_txt = "Note Doublée"
        if display_txt == "S": display_txt = "Silence"
        if display_txt == "PAGE": display_txt = "Saut de Page"
        st.toast(f"Ajouté : {display_txt}", icon="🎵")

def annuler_derniere_ligne():
    lines = st.session_state.code_actuel.strip().split('\n')
    if len(lines) > 0:
        st.session_state.code_actuel = "\n".join(lines[:-1])
        st.session_state.widget_input = st.session_state.code_actuel
        st.toast("Dernière ligne annulée", icon="↩️")

with st.sidebar:
    st.header("🎚️ Réglages")
    st.markdown("### 📚 Banque")
    st.selectbox("Choisir un morceau :", options=list(BANQUE_TABLATURES.keys()), key='selection_banque', on_change=charger_morceau)
    st.markdown("---")
    with st.expander("🎨 Apparence", expanded=False):
        bg_color = st.color_picker("Couleur de fond", "#e5c4a1")
        use_bg_img = st.checkbox("Texture Ngonilélé", True)
        bg_alpha = st.slider("Transparence", 0.0, 1.0, 0.2)
        st.markdown("---")
        force_white_print = st.checkbox("🖨️ Fond blanc (Impression)", value=True)
    st.markdown("---")
    st.markdown("### 🤝 Contribuer")
    st.markdown("Envoyez vos tabs à : julienflorin59@gmail.com")

tab1, tab2, tab3, tab4 = st.tabs(["📝 Éditeur", "⚙️ Accordage", "🎬 Vidéo", "🎧 Audio"])

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
    
    # --- COLONNE DE GAUCHE : ÉDITEUR ---
    with col_input:
        st.subheader("Outils de Saisie")
        
        # ONGLETS DE SAISIE UNIQUEMENT
        subtab_btn, subtab_visu = st.tabs(["🔘 Grille Rapide", "🎨 Manche Visuel"])

        # >>> 1. GRILLE
        with subtab_btn:
            st.caption("Mode Rapide")
            st.markdown("""<style>div[data-testid="column"] .stButton button {width: 100%; padding: 4px 8px !important;}</style>""", unsafe_allow_html=True)
            bc1, bc2, bc3, bc4 = st.columns(4)
            with bc1: 
                st.caption("Gauche")
                for c in ['1G','2G','3G','4G','5G','6G']: st.button(c, key=f"b_{c}", on_click=ajouter_texte, args=(f"+ {c}",), use_container_width=True)
            with bc2:
                st.caption("Droite")
                for c in ['1D','2D','3D','4D','5D','6D']: st.button(c, key=f"b_{c}", on_click=ajouter_texte, args=(f"+ {c}",), use_container_width=True)
            with bc3:
                st.caption("Outils")
                st.button("↩️ Undo", key="btn_undo", on_click=annuler_derniere_ligne, use_container_width=True)
                # MODIFICATION ICI : Libellés changés
                st.button("🟰 Notes Simultanées", key="btn_simul", on_click=ajouter_texte, args=("=",), use_container_width=True)
                st.button("🔁 Note Doublée", key="btn_x2", on_click=ajouter_texte, args=("x2",), use_container_width=True)
                st.button("🔇 Insérer Silence", key="btn_sil", on_click=ajouter_texte, args=("+ S",), use_container_width=True)
            with bc4:
                st.caption("Structure")
                # MODIFICATION ICI : Libellés changés
                st.button("📄 Insérer Page", key="btn_pg", on_click=ajouter_texte, args=("+ PAGE",), use_container_width=True)
                st.button("📝 Insérer Texte", key="btn_tx", on_click=ajouter_texte, args=("+ TXT Msg",), use_container_width=True)

        # >>> 2. VISUEL
        with subtab_visu:
            def ajouter_visu(corde):
                mode = st.session_state.visu_mode; sfx = ""; msg = ""
                if mode == "Force P": sfx=" P"; msg=" (Pouce)"
                elif mode == "Force I": sfx=" I"; msg=" (Index)"
                ajouter_texte(f"+ {corde}{sfx}", f"Note {corde}{msg}")

            st.radio("Doigté", ["Auto", "Force P", "Force I"], key="visu_mode", horizontal=True)
            cols_visu = st.columns([1,1,1,1,1,1, 0.2, 1,1,1,1,1,1])
            COLORS_VISU = {'6G': '#00BFFF', '5G': '#FF4B4B', '4G': '#00008B', '3G': '#FFD700', '2G': '#FF4B4B', '1G': '#00BFFF', '1D': '#32CD32', '2D': '#00008B', '3D': '#FFA500', '4D': '#00BFFF', '5D': '#9400D3', '6D': '#FFD700'}
            
            # Gauche
            for i, c in enumerate(['6G', '5G', '4G', '3G', '2G', '1G']):
                with cols_visu[i]:
                    st.button(c, key=f"v_{c}", on_click=ajouter_visu, args=(c,), use_container_width=True)
                    st.markdown(f"<div style='margin:0 auto; width:4px; height:40px; background-color:{COLORS_VISU.get(c,'gray')};'></div>", unsafe_allow_html=True)
            # Chevalet
            with cols_visu[6]: st.markdown("<div style='height:60px; width:2px; background-color:black; margin:0 auto;'></div>", unsafe_allow_html=True)
            # Droite
            for i, c in enumerate(['1D', '2D', '3D', '4D', '5D', '6D']):
                with cols_visu[i+7]:
                    st.button(c, key=f"v_{c}", on_click=ajouter_visu, args=(c,), use_container_width=True)
                    st.markdown(f"<div style='margin:0 auto; width:4px; height:40px; background-color:{COLORS_VISU.get(c,'gray')};'></div>", unsafe_allow_html=True)

        # ========================================================
        # ZONE DE TEXTE (HORS ONGLETS - TOUJOURS VISIBLE)
        # ========================================================
        st.markdown("---")
        st.caption("📝 **Code de la partition (Modifiable)**")
        st.text_area(
            "Zone de Code", 
            value=st.session_state.widget_input, 
            height=250, 
            key="widget_input", 
            on_change=mise_a_jour_texte, 
            label_visibility="collapsed"
        )

        st.markdown("---")
        # Lecteur Rapide
        if st.button("🎧 Écouter l'extrait (Rapide)"):
            with st.spinner("Génération..."):
                seq = parser_texte(st.session_state.code_actuel)
                aud = generer_audio_mix(seq, 100, acc_config)
                if aud: st.audio(aud, format="audio/mp3")

    # --- COLONNE DE DROITE : APERÇU ---
    with col_view:
        st.subheader("Aperçu Partition")
        if st.button("🔄 Actualiser la vue", type="primary", use_container_width=True):
            st.session_state.partition_buffers = [] 
            styles_ecran = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
            styles_print = {'FOND': 'white', 'TEXTE': 'black', 'PERLE_FOND': 'white', 'LEGENDE_FOND': 'white'}
            opt_visu = {'use_bg': use_bg_img, 'alpha': bg_alpha}
            
            with st.status("Génération...", expanded=True) as status:
                seq = parser_texte(st.session_state.code_actuel)
                
                # Légende
                fig_leg = generer_page_1_legende(titre_partition, styles_ecran, False)
                if force_white_print: fig_leg_dl = generer_page_1_legende(titre_partition, styles_print, True)
                else: fig_leg_dl = fig_leg
                buf_leg = io.BytesIO(); fig_leg_dl.savefig(buf_leg, format="png", dpi=150, facecolor=styles_print['FOND'] if force_white_print else bg_color, bbox_inches='tight'); buf_leg.seek(0)
                st.session_state.partition_buffers.append({'type':'legende', 'buf': buf_leg, 'img_ecran': fig_leg, 'idx': 1})
                if force_white_print: plt.close(fig_leg_dl)

                # Pages
                pgs = []; cur = []
                for n in seq:
                    if n['corde'] == 'PAGE_BREAK': pgs.append(cur); cur = []
                    else: cur.append(n)
                if cur: pgs.append(cur)
                
                for idx, p in enumerate(pgs):
                    fig = generer_page_notes(p, idx+2, titre_partition, acc_config, styles_ecran, opt_visu, False)
                    if force_white_print: fig_dl = generer_page_notes(p, idx+2, titre_partition, acc_config, styles_print, opt_visu, True)
                    else: fig_dl = fig
                    buf = io.BytesIO(); fig_dl.savefig(buf, format="png", dpi=150, facecolor=styles_print['FOND'] if force_white_print else bg_color, bbox_inches='tight'); buf.seek(0)
                    st.session_state.partition_buffers.append({'type':'page', 'idx': idx+2, 'buf': buf, 'img_ecran': fig})
                    if force_white_print: plt.close(fig_dl)
                
                st.session_state.partition_generated = True
                status.update(label="Terminé !", state="complete", expanded=False)

        if st.session_state.partition_generated:
            pdf_buf = generer_pdf_livret(st.session_state.partition_buffers, titre_partition)
            st.download_button("📕 Télécharger PDF", pdf_buf, f"{titre_partition}.pdf", "application/pdf", type="primary", use_container_width=True)
            for item in st.session_state.partition_buffers:
                st.image(item['img_ecran'], use_column_width=True)

# --- TAB VIDEO ---
with tab3:
    st.subheader("Générateur de Vidéo 🎥")
    if not HAS_MOVIEPY: st.error("MoviePy manquant.")
    else:
        c1, c2 = st.columns(2)
        with c1: bpm_v = st.slider("BPM", 30, 200, 60, key="bpm_vid")
        with c2: 
            st.write("")
            btn_gen_v = st.button("🎬 Lancer la vidéo")
        
        if btn_gen_v:
            with st.status("Création vidéo...", expanded=True) as s:
                seq = parser_texte(st.session_state.code_actuel)
                aud = generer_audio_mix(seq, bpm_v, acc_config)
                nb_t = seq[-1]['temps'] - seq[0]['temps'] if seq else 10
                dur = (nb_t + 4) * (60/bpm_v)
                
                styles_v = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
                img_buf, px_par_temps, offset_px = generer_image_longue_calibree(seq, acc_config, styles_v)
                
                vid_path = creer_video_avec_son_calibree(img_buf, aud, dur, (px_par_temps, offset_px), bpm_v)
                
                st.session_state.video_path = vid_path
                s.update(label="Vidéo Prête !", state="complete")
        
        if st.session_state.video_path:
            st.video(st.session_state.video_path)
            with open(st.session_state.video_path, "rb") as f:
                st.download_button("⬇️ MP4", f, "video_ngoni.mp4", "video/mp4")

# --- TAB AUDIO ---
with tab4:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Piste Audio")
        bpm_a = st.slider("BPM", 30, 200, 100, key="bpm_aud")
        if st.button("🎵 Générer MP3"):
            seq = parser_texte(st.session_state.code_actuel)
            st.session_state.audio_buffer = generer_audio_mix(seq, bpm_a, acc_config)
        if st.session_state.audio_buffer:
            st.audio(st.session_state.audio_buffer)
            st.download_button("⬇️ MP3", st.session_state.audio_buffer, "audio.mp3", "audio/mpeg")
    with c2:
        st.subheader("Métronome")
        sig = st.radio("Signature", ["4/4", "3/4"], horizontal=True)
        bpm_m = st.slider("BPM", 30, 200, 80, key="bpm_met")
        if st.button("▶️ Start"):
            st.session_state.metronome_buffer = generer_metronome(bpm_m, 60, sig)
        if st.session_state.metronome_buffer:
            st.audio(st.session_state.metronome_buffer)