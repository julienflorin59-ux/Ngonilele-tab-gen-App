import streamlit as st
import sys
import io
import os
import shutil
import numpy as np
import urllib.parse # <--- L'IMPORT QUI MANQUAIT !

# ==============================================================================
# 🚑 PATCH PYTHON 3.13 (POUR L'AUDIO)
# ==============================================================================
try:
    import pyaudioop
    sys.modules["audioop"] = pyaudioop
except ImportError: pass

# ==============================================================================
# 📦 IMPORTS
# ==============================================================================
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# Gestion sécurisée des modules multimédia
HAS_MOVIEPY = False
try:
    from moviepy.editor import ImageClip, CompositeVideoClip, AudioFileClip, ColorClip
    HAS_MOVIEPY = True
except: pass

HAS_PYDUB = False
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except: pass

# ==============================================================================
# ⚙️ CONFIGURATION
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
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# 🚨 MESSAGE D'AIDE
# ==============================================================================
if st.session_state.get('first_run', True):
    st.info("👈 **CLIQUEZ SUR LA FLÈCHE GRISE (>) EN HAUT À GAUCHE** pour ouvrir le menu !")

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
# 📖 MODE D'EMPLOI
# ==============================================================================
with st.expander("📖 **COMMENT ÇA MARCHE ?**", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 1. Écrire")
        st.write("Utilisez l'onglet **Éditeur**. Tapez votre code et cliquez sur **Générer**.")
    with c2:
        st.markdown("### 2. Vidéo & Audio")
        st.write("Créez une animation karaoké ou exportez le son.")
    with c3:
        st.markdown("### 3. Réglages")
        st.write("Menu de gauche : Banque de sons, Accordage, Apparence.")

# ==============================================================================
# 🧠 LOGIQUE METIER
# ==============================================================================
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
# 🎹 MOTEUR AUDIO (CALAGE PRECIS)
# ==============================================================================
def generer_audio_mix(sequence, bpm):
    if not HAS_PYDUB: st.error("❌ Pydub manquant."); return None, 0
    if not sequence: return None, 0
    if not os.path.exists(DOSSIER_SAMPLES): st.error(f"❌ Dossier '{DOSSIER_SAMPLES}' introuvable."); return None, 0
    
    samples_loaded = {}
    cordes_utilisees = set([n['corde'] for n in sequence if n['corde'] in POSITIONS_X])
    for corde in cordes_utilisees:
        nom_fichier = f"{corde}.mp3"
        chemin = os.path.join(DOSSIER_SAMPLES, nom_fichier)
        if os.path.exists(chemin): samples_loaded[corde] = AudioSegment.from_mp3(chemin)
        else:
            chemin_min = os.path.join(DOSSIER_SAMPLES, f"{corde.lower()}.mp3")
            if os.path.exists(chemin_min): samples_loaded[corde] = AudioSegment.from_mp3(chemin_min)
            
    if not samples_loaded: st.error("Aucun MP3 valide."); return None, 0

    ms_par_temps = 60000 / bpm
    t_min = sequence[0]['temps']
    dernier_t = sequence[-1]['temps']
    
    duree_totale_ms = int((dernier_t - t_min + 4) * ms_par_temps)
    mix = AudioSegment.silent(duration=duree_totale_ms)
    
    for n in sequence:
        corde = n['corde']
        if corde in samples_loaded:
            t = n['temps']
            pos_ms = int((t - t_min) * ms_par_temps)
            if pos_ms < 0: pos_ms = 0
            mix = mix.overlay(samples_loaded[corde], position=pos_ms)
            
    buffer = io.BytesIO(); mix.export(buffer, format="mp3"); buffer.seek(0)
    return buffer, duree_totale_ms / 1000.0

# ==============================================================================
# 🎨 MOTEUR AFFICHAGE (PAGES)
# ==============================================================================
def generer_page_1_legende(titre, styles, mode_white=False):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; prop_titre = get_font(32, 'bold')
    fig, ax = plt.subplots(figsize=(16, 8), facecolor=c_fond)
    ax.set_facecolor(c_fond)
    ax.text(0, 0.5, titre, ha='center', va='center', fontproperties=prop_titre, color=c_txt)
    ax.text(0, -0.5, "Légende simplifiée (Voir App)", ha='center', color=c_txt)
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(-2, 2); ax.axis('off')
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
    ax.vlines(0, y_bot, y_top_cordes + 1.8, color=c_txt, lw=5, zorder=2)
    
    for code, props in config_acc.items():
        x = props['x']; note = props['n']; c = COULEURS_CORDES_REF.get(note, '#000000')
        ax.text(x, y_top_cordes + 0.7, note, ha='center', color=c, fontproperties=prop_note_us)
        ax.vlines(x, y_bot, y_top_cordes, colors=c, lw=3, zorder=1)
    
    # GRILLE
    for t in range(t_min, t_max + 1):
        y = -(t - t_min)
        ax.axhline(y=y, color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)

    notes_par_temps_relatif = {}; rayon = 0.30
    for n in notes_page:
        t_absolu = n['temps']; y = -(t_absolu - t_min)
        if y not in notes_par_temps_relatif: notes_par_temps_relatif[y] = []
        notes_par_temps_relatif[y].append(n); code = n['corde']
        if code == 'TEXTE': 
            bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt, lw=2)
            ax.text(0, y, n.get('message',''), ha='center', va='center', color='black', fontproperties=prop_annotation, bbox=bbox, zorder=10)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']; c = COULEURS_CORDES_REF.get(props['n'], '#000000')
            ax.add_patch(plt.Circle((x, y), rayon, color=c_perle, zorder=3))
            ax.add_patch(plt.Circle((x, y), rayon, fill=False, edgecolor=c, lw=3, zorder=4))
            if 'doigt' in n:
                doigt = n['doigt']; img_path = path_index if doigt == 'I' else path_pouce
                if os.path.exists(img_path):
                    try: ab = AnnotationBbox(OffsetImage(mpimg.imread(img_path), zoom=0.045), (x - 0.70, y + 0.1), frameon=False, zorder=8); ax.add_artist(ab)
                    except: pass
                else: ax.text(x - 0.70, y, doigt, ha='center', va='center', color=c_txt, fontproperties=prop_standard, zorder=7)
    
    for y, group in notes_par_temps_relatif.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)
        
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(y_bot, y_top + 5); ax.axis('off')
    return fig

# ==============================================================================
# 🎥 MOTEUR VIDEO (IMAGE GÉANTE AVEC GÉOMÉTRIE FIXE)
# ==============================================================================
def generer_image_longue_synchro(sequence, config_acc, styles):
    """Génère l'image et retourne les infos géométriques précises (pixels par temps)"""
    if not sequence: return None, 0, 0
    
    t_min = sequence[0]['temps']
    t_max = sequence[-1]['temps']
    
    UNITE_TEMPS = 1.0 
    MARGE_HAUT_UNIT = 3.0 
    MARGE_BAS_UNIT = 2.0 
    
    nb_temps = t_max - t_min
    hauteur_totale_units = MARGE_HAUT_UNIT + nb_temps + MARGE_BAS_UNIT
    
    PIXELS_PER_UNIT = 100 
    hauteur_px = int(hauteur_totale_units * PIXELS_PER_UNIT)
    largeur_px = 1600
    
    MY_DPI = 100
    figsize_w = largeur_px / MY_DPI
    figsize_h = hauteur_px / MY_DPI
    
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    path_pouce = CHEMIN_ICON_POUCE_BLANC if c_fond == 'white' else CHEMIN_ICON_POUCE
    path_index = CHEMIN_ICON_INDEX_BLANC if c_fond == 'white' else CHEMIN_ICON_INDEX

    fig = plt.figure(figsize=(figsize_w, figsize_h), facecolor=c_fond)
    ax = fig.add_axes([0, 0, 1, 1]) 
    ax.set_facecolor(c_fond)
    
    ax.set_xlim(-8, 8)
    ax.set_ylim(-hauteur_totale_units, 0)
    ax.axis('off')
    
    y_start_notes = -MARGE_HAUT_UNIT
    
    prop_note = get_font(24, 'bold'); prop_num = get_font(14, 'bold')
    
    ax.vlines(0, -hauteur_totale_units + 1, -1, color=c_txt, lw=5, zorder=2)
    
    for code, props in config_acc.items():
        x = props['x']; note = props['n']; c = COULEURS_CORDES_REF.get(note, '#000000')
        y_head = 0.5 
        ax.text(x, y_head + 0.8, code, ha='center', color='gray', fontproperties=prop_num)
        ax.text(x, y_head + 0.2, note, ha='center', color=c, fontproperties=prop_note)
        ax.vlines(x, -hauteur_totale_units, y_head, colors=c, lw=3, zorder=1)

    notes_par_temps = {}
    
    for t_offset in range(nb_temps + 1):
        y_pos = y_start_notes - t_offset
        ax.axhline(y=y_pos, color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)

    for n in sequence:
        if n['corde'] == 'PAGE_BREAK': continue
        t = n['temps']
        delta_t = t - t_min
        y_pos = y_start_notes - delta_t
        
        if y_pos not in notes_par_temps: notes_par_temps[y_pos] = []
        notes_par_temps[y_pos].append(n)
        
        code = n['corde']
        if code == 'TEXTE':
            bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt, lw=2)
            ax.text(0, y_pos, n.get('message',''), ha='center', va='center', color='black', bbox=bbox, zorder=10)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']; c = COULEURS_CORDES_REF.get(props['n'], '#000000')
            ax.add_patch(plt.Circle((x, y_pos), 0.3, color=c_perle, zorder=3))
            ax.add_patch(plt.Circle((x, y_pos), 0.3, fill=False, edgecolor=c, lw=3, zorder=4))
            if 'doigt' in n:
                doigt = n['doigt']; img_path = path_index if doigt == 'I' else path_pouce
                if os.path.exists(img_path):
                    try: ab = AnnotationBbox(OffsetImage(mpimg.imread(img_path), zoom=0.045), (x - 0.70, y_pos + 0.1), frameon=False, zorder=8); ax.add_artist(ab)
                    except: pass
                else: ax.text(x - 0.70, y_pos, doigt, ha='center', va='center', color=c_txt, zorder=7)

    for y, group in notes_par_temps.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=MY_DPI, facecolor=c_fond)
    plt.close(fig)
    buf.seek(0)
    
    offset_pixels = MARGE_HAUT_UNIT * PIXELS_PER_UNIT
    px_per_beat = PIXELS_PER_UNIT
    
    return buf, offset_pixels, px_per_beat

def creer_video_avec_son(image_buffer, audio_buffer, duration_sec, offset_px, px_per_beat, bpm, fps=24):
    if not HAS_MOVIEPY: return None
    
    with open("temp_score.png", "wb") as f: f.write(image_buffer.getbuffer())
    with open("temp_audio.mp3", "wb") as f: f.write(audio_buffer.getbuffer())

    clip_img = ImageClip("temp_score.png")
    w, h = clip_img.size
    
    video_h = 600
    window_size = (w, video_h)
    
    bar_y = 150 
    speed_px_sec = px_per_beat * (bpm / 60.0)
    start_y = bar_y - offset_px
    
    moving_clip = clip_img.set_position(lambda t: ('center', start_y - (speed_px_sec * t)))
    
    try:
        from moviepy.video.tools.drawing import color_gradient
        highlight_bar = ColorClip(size=(w, int(px_per_beat)), color=[255, 215, 0]) 
        highlight_bar = highlight_bar.set_opacity(0.3).set_position(('center', bar_y - int(px_per_beat/2))) 
        video_visual = CompositeVideoClip([moving_clip, highlight_bar], size=window_size)
    except:
        video_visual = CompositeVideoClip([moving_clip], size=window_size)
        
    video_visual = video_visual.set_duration(duration_sec)

    audio_clip = AudioFileClip("temp_audio.mp3")
    if audio_clip.duration > duration_sec:
        audio_clip = audio_clip.subclip(0, duration_sec)
    
    final = video_visual.set_audio(audio_clip)
    final.fps = fps
    
    output_filename = "ngoni_video_synchro.mp4"
    final.write_videofile(output_filename, codec='libx264', audio_codec='aac', preset='ultrafast')
    
    audio_clip.close(); final.close()
    return output_filename

# ==============================================================================
# 🎛️ INTERFACE
# ==============================================================================
col_logo, col_titre = st.columns([1, 5])
with col_logo:
    if os.path.exists(CHEMIN_LOGO_APP): st.image(CHEMIN_LOGO_APP, width=100)
    else: st.header("🪕")
with col_titre:
    st.title("Générateur de Tablature Ngonilélé")
    st.markdown("Créez vos partitions, réglez l'accordage et téléchargez le résultat.")

if st.session_state.get('first_run', True):
    st.info("👈 **CLIQUEZ SUR LA FLÈCHE GRISE (>) EN HAUT À GAUCHE** pour ouvrir le menu !")

if len(BANQUE_TABLATURES) > 0: PREMIER_TITRE = list(BANQUE_TABLATURES.keys())[0]
else: PREMIER_TITRE = "Défaut"; BANQUE_TABLATURES[PREMIER_TITRE] = ""

if 'code_actuel' not in st.session_state: st.session_state.code_actuel = BANQUE_TABLATURES[PREMIER_TITRE].strip()
if 'gen_active' not in st.session_state: st.session_state.gen_active = False

def charger_morceau():
    choix = st.session_state.selection_banque
    if choix in BANQUE_TABLATURES:
        nouveau = BANQUE_TABLATURES[choix].strip()
        st.session_state.code_actuel = nouveau
        st.session_state.widget_input = nouveau

def mise_a_jour_texte(): st.session_state.code_actuel = st.session_state.widget_input

with st.sidebar:
    st.header("🎚️ Réglages")
    st.markdown("### 📚 Banque de Morceaux")
    st.selectbox("Choisir un morceau :", options=list(BANQUE_TABLATURES.keys()), key='selection_banque', on_change=charger_morceau)
    st.caption("⚠️ Remplacera le texte actuel.")
    st.markdown("---")
    titre_partition = st.text_input("Titre de la partition", "Tablature Ngonilélé")
    with st.expander("🎨 Apparence", expanded=False):
        bg_color = st.color_picker("Couleur de fond", "#e5c4a1")
        use_bg_img = st.checkbox("Texture Ngonilélé (si image présente)", True)
        bg_alpha = st.slider("Transparence Texture", 0.0, 1.0, 0.2)
        st.markdown("---")
        force_white_print = st.checkbox("🖨️ Fond blanc pour impression", value=True)
    
    st.markdown("---")
    st.markdown("### 🤝 Contribuer")
    mon_email = "julienflorin59@gmail.com" 
    sujet_mail = f"Nouvelle Tablature Ngonilélé : {titre_partition}"
    corps_mail = f"Bonjour,\n\nVoici une proposition :\n\n{st.session_state.code_actuel}"
    mailto_link = f"mailto:{mon_email}?subject={urllib.parse.quote(sujet_mail)}&body={urllib.parse.quote(corps_mail)}"
    st.markdown(f'<a href="{mailto_link}" target="_blank"><button style="width:100%; background-color:#FF4B4B; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">📧 Envoyer ma partition</button></a>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📝 Éditeur & Partition", "⚙️ Accordage", "🎬 Vidéo (Bêta)", "🎧 Audio"])

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
    col_input, col_view = st.columns([1, 2])
    with col_input:
        st.subheader("Code")
        # --- LEGENDE ---
        st.markdown("""
        <div style="background-color: #262730; padding: 10px; border-radius: 5px; border: 1px solid #444; color: #FAFAFA;">
        💡 <b>Légende rapide :</b><br>
        <code>1</code> : Temps 1 &nbsp;|&nbsp; <code>4D</code> : Corde &nbsp;|&nbsp; <code>+</code> : Temps suivant<br>
        <code>=</code> : Notes simultanées &nbsp;|&nbsp; <code>S</code> : Silence &nbsp;|&nbsp; <code>x2</code> : Répéter
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        with st.expander("❓ Sauvegarder / Recharger"):
            st.write("Pour ne pas perdre votre travail, téléchargez le fichier .txt")
        uploaded_file = st.file_uploader("📂 Charger un fichier (.txt)", type="txt")
        if uploaded_file is not None:
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            content = stringio.read()
            if content != st.session_state.code_actuel:
                st.session_state.code_actuel = content
                st.session_state.widget_input = content
                st.rerun()
        st.text_area("Saisissez votre tablature ici :", height=500, key="widget_input", on_change=mise_a_jour_texte)
        st.download_button(label="💾 Sauvegarder le code (.txt)", data=st.session_state.code_actuel, file_name=f"{titre_partition.replace(' ', '_')}.txt", mime="text/plain")
        
    with col_view:
        st.subheader("Aperçu")
        if st.button("🔄 Générer la partition", type="primary"):
            st.session_state.gen_active = True

        if st.session_state.gen_active:
            styles_ecran = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
            styles_print = {'FOND': 'white', 'TEXTE': 'black', 'PERLE_FOND': 'white', 'LEGENDE_FOND': 'white'}
            options_visuelles = {'use_bg': use_bg_img, 'alpha': bg_alpha}
            sequence = parser_texte(st.session_state.code_actuel)
            
            st.markdown("### Page 1 : Légende")
            fig_leg_ecran = generer_page_1_legende(titre_partition, styles_ecran, mode_white=False)
            st.pyplot(fig_leg_ecran)
            if force_white_print: fig_leg_dl = generer_page_1_legende(titre_partition, styles_print, mode_white=True)
            else: fig_leg_dl = fig_leg_ecran
            buf_leg = io.BytesIO(); fig_leg_dl.savefig(buf_leg, format="png", dpi=200, facecolor=styles_print['FOND'] if force_white_print else bg_color, bbox_inches='tight'); buf_leg.seek(0)
            st.download_button(label="⬇️ Télécharger Légende", data=buf_leg, file_name=f"{titre_partition}_Legende.png", mime="image/png")
            plt.close(fig_leg_ecran); 
            if force_white_print: plt.close(fig_leg_dl)
            
            pages_data = []; current_page = []
            for n in sequence:
                if n['corde'] == 'PAGE_BREAK':
                    if current_page: pages_data.append(current_page); current_page = []
                else: current_page.append(n)
            if current_page: pages_data.append(current_page)
            
            if not pages_data: st.warning("Aucune note détectée.")
            else:
                for idx, page in enumerate(pages_data):
                    st.markdown(f"### Page {idx+2}")
                    fig_ecran = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_ecran, options_visuelles, mode_white=False)
                    st.pyplot(fig_ecran)
                    if force_white_print: fig_dl = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_print, options_visuelles, mode_white=True)
                    else: fig_dl = fig_ecran
                    buf = io.BytesIO(); fig_dl.savefig(buf, format="png", dpi=200, facecolor=styles_print['FOND'] if force_white_print else bg_color, bbox_inches='tight'); buf.seek(0)
                    st.download_button(label=f"⬇️ Télécharger Page {idx+2}", data=buf, file_name=f"{titre_partition}_Page_{idx+2}.png", mime="image/png")
                    plt.close(fig_ecran); 
                    if force_white_print: plt.close(fig_dl)

# --- TAB VIDEO ---
with tab3:
    st.subheader("Générateur de Vidéo Défilante 🎥")
    
    if not HAS_MOVIEPY: st.error("❌ Le module 'moviepy' n'est pas installé.")
    elif not HAS_PYDUB: st.error("❌ Le module 'pydub' n'est pas installé.")
    else:
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            bpm = st.slider("Vitesse (BPM)", 30, 200, 60, key="bpm_video")
            seq = parser_texte(st.session_state.code_actuel)
            if seq:
                # Calcul durée exacte
                ms_par_temps = 60000 / bpm
                t_min = seq[0]['temps']
                dernier_t = seq[-1]['temps']
                duree_ms = int((dernier_t - t_min + 4) * ms_par_temps)
                st.write(f"Durée : {duree_ms/1000:.1f}s")
            else: duree_estimee = 10
        with col_v2:
            btn_video = st.button("🎥 Générer Vidéo + Audio")

        if btn_video:
            with st.spinner("Génération de la piste Audio..."):
                sequence = parser_texte(st.session_state.code_actuel)
                audio_buffer, duration_sec = generer_audio_mix(sequence, bpm)
                
            if audio_buffer:
                with st.spinner("Génération de l'image géante..."):
                    styles_video = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
                    img_buffer, offset_px, px_per_beat = generer_image_longue_synchro(sequence, acc_config, styles_video)
                
                if img_buffer:
                    with st.spinner("Montage Final (Synchronisation)..."):
                        try:
                            video_path = creer_video_avec_son(img_buffer, audio_buffer, duration_sec, offset_px, px_per_beat, bpm)
                            st.success("Vidéo terminée ! 🥳")
                            st.video(video_path)
                            with open(video_path, "rb") as file:
                                st.download_button(label="⬇️ Télécharger la Vidéo", data=file, file_name="ngoni_video.mp4", mime="video/mp4")
                        except Exception as e:
                            st.error(f"Erreur lors du montage : {e}")

# --- TAB AUDIO ---
with tab4:
    st.subheader("Générateur Audio Seul 🎧")
    if not HAS_PYDUB:
         st.error("❌ Le module 'pydub' n'est pas installé.")
    else:
        col_a1, col_a2 = st.columns(2)
        with col_a1: bpm_audio = st.slider("Vitesse (BPM)", 30, 200, 100, key="bpm_audio")
        with col_a2: btn_audio = st.button("🎵 Générer MP3")
        if btn_audio:
            with st.spinner("Mixage..."):
                sequence = parser_texte(st.session_state.code_actuel)
                mp3_buffer, _ = generer_audio_mix(sequence, bpm_audio)
                if mp3_buffer:
                    st.success("Terminé !")
                    st.audio(mp3_buffer, format="audio/mp3")
                    st.download_button(label="⬇️ Télécharger le MP3", data=mp3_buffer, file_name=f"{titre_partition.replace(' ', '_')}.mp3", mime="audio/mpeg")