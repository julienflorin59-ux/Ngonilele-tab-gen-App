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
import shutil
from fpdf import FPDF
import random
import pandas as pd 
import re 
import gc 
import glob 
import json

# ==============================================================================
# ⚙️ CONFIGURATION & CSS ULTRA-COMPACT (MOBILE)
# ==============================================================================
st.set_page_config(
    page_title="Générateur Tablature Ngonilélé", 
    layout="wide", 
    page_icon="ico_ngonilele.png", 
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* OPTIMISATION MOBILE AGRESSIVE */
    @media (max-width: 640px) {
        /* 1. Réduire les marges de la page entière */
        .block-container {
            padding-top: 1rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }

        /* 2. Boutons : Plus petits, moins de hauteur, texte plus petit */
        .stButton button {
            padding: 0px 4px !important;
            font-size: 0.85rem !important;
            line-height: 1.2 !important;
            min-height: 38px !important; /* Hauteur réduite */
            height: auto !important;
            margin-bottom: 4px !important;
        }
        
        /* 3. Colonnes : Forcer 50% de largeur stricte et réduire l'espacement entre elles */
        div[data-testid="column"] {
            width: 50% !important;
            flex: 1 1 50% !important;
            min-width: 50% !important;
            padding: 0 3px !important; /* Espace entre colonnes réduit */
        }

        /* 4. Séquenceur & Visuel : Scroll horizontal fluide */
        div[data-testid="stHorizontalBlock"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            padding-bottom: 5px !important;
        }
        
        /* 5. Réduire la taille des titres */
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }
        
        /* 6. Checkbox du séquenceur plus compacte */
        div[data-testid="stCheckbox"] {
            min-height: 0px !important;
            margin-bottom: 0px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

CHEMIN_POLICE = 'ML.ttf' 
CHEMIN_IMAGE_FOND = 'texture_ngonilele.png'
CHEMIN_ICON_POUCE = 'icon_pouce.png'
CHEMIN_ICON_INDEX = 'icon_index.png'
CHEMIN_ICON_POUCE_BLANC = 'icon_pouce_blanc.png'
CHEMIN_ICON_INDEX_BLANC = 'icon_index_blanc.png'
CHEMIN_LOGO_APP = 'ico_ngonilele.png'
DOSSIER_SAMPLES = 'samples'

# ==============================================================================
# 🚀 FONCTIONS LOGIQUES
# ==============================================================================
@st.cache_resource
def load_font_properties():
    if os.path.exists(CHEMIN_POLICE): return fm.FontProperties(fname=CHEMIN_POLICE)
    return fm.FontProperties(family='sans-serif')

@st.cache_resource
def load_image_asset(path):
    if os.path.exists(path): return mpimg.imread(path)
    return None

BANQUE_TABLATURES = {
    "--- Nouveau / Vide ---": "",
    "Exercice Débutant": "1 1D\n+ S\n+ 1G\n+ S\n+ 2D\n+ S\n+ 2G\n+ S\n+ 3D\n+ S\n+ 3G\n+ S\n+ 4D\n+ S\n+ 4G\n+ S\n+ 5D\n+ S\n+ 5G\n+ S\n+ 6D\n+ S\n+ 6G\n+ S",
    "Manitoumani": "1 4D\n+ 4G\n+ 5D\n+ 5G\n+ 4G\n= 2D\n+ 3G\n+ 6D x2\n+ 2G\n= 5G\n+ 3G\n+ 6D x2\n+ 2G\n= 5G\n+ 3G\n+ 6D x2\n+ 2G\n= 5G"
}

# En-tête simplifié
col_logo, col_titre = st.columns([1, 5])
with col_logo:
    if os.path.exists(CHEMIN_LOGO_APP): st.image(CHEMIN_LOGO_APP, width=80)
    else: st.header("🪕")
with col_titre:
    st.title("Générateur Ngonilélé")

HAS_MOVIEPY = False
try:
    from moviepy.editor import ImageClip, CompositeVideoClip, AudioFileClip, ColorClip
    HAS_MOVIEPY = True
except: pass
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
    prop.set_size(size); prop.set_weight(weight); prop.set_style(style)
    return prop

def parser_texte(texte):
    data = []; dernier_temps = 0
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
            if corde_valide == 'TXT': data.append({'temps': t, 'corde': 'TEXTE', 'message': parts[2] if len(parts)>2 else ""}); continue
            elif corde_valide == 'PAGE': data.append({'temps': t, 'corde': 'PAGE_BREAK'}); continue
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
            block_name = match.group(1).strip(); repeat_count = int(match.group(2))
        else:
            block_name = part; repeat_count = 1
        if block_name in blocks_dict:
            for _ in range(repeat_count): full_text += blocks_dict[block_name].strip() + "\n"
        else: full_text += f"+ TXT [Bloc '{block_name}' introuvable]\n"
    return full_text

def get_note_freq(note_name):
    return {'C': 261.63, 'D': 293.66, 'E': 329.63, 'F': 349.23, 'G': 392.00, 'A': 440.00, 'B': 493.88}.get(note_name, 440.0)

@st.cache_data(show_spinner=False)
def generer_audio_mix(sequence, bpm, acc_config):
    if not HAS_PYDUB or not sequence: return None
    samples_loaded = {}
    cordes_utilisees = set([n['corde'] for n in sequence if n['corde'] in POSITIONS_X])
    for corde in cordes_utilisees:
        loaded = False
        if os.path.exists(DOSSIER_SAMPLES):
            chemin = os.path.join(DOSSIER_SAMPLES, f"{corde}.mp3")
            if os.path.exists(chemin): samples_loaded[corde] = AudioSegment.from_mp3(chemin); loaded = True
        if not loaded:
            freq = get_note_freq(acc_config.get(corde, {'n':'C'})['n'])
            samples_loaded[corde] = Sine(freq).to_audio_segment(duration=600).fade_out(400) - 5
    if not samples_loaded: return None
    ms_par_temps = 60000 / bpm
    mix = AudioSegment.silent(duration=int((sequence[-1]['temps'] + 4) * ms_par_temps))
    for n in sequence:
        if n['corde'] in samples_loaded:
            pos_ms = int((n['temps'] - 1) * ms_par_temps)
            mix = mix.overlay(samples_loaded[n['corde']], position=max(0, pos_ms))
    buffer = io.BytesIO(); mix.export(buffer, format="mp3", bitrate="64k"); buffer.seek(0)
    return buffer

@st.cache_data(show_spinner=False)
def generer_metronome(bpm, duration_sec=30, signature="4/4"):
    if not HAS_PYDUB: return None
    ms_per_beat = 60000 / bpm
    accent = (WhiteNoise().to_audio_segment(duration=60).fade_out(50).overlay(Sine(1500).to_audio_segment(duration=20).fade_out(20).apply_gain(-10))).apply_gain(-2)
    normal = WhiteNoise().to_audio_segment(duration=40).fade_out(35).apply_gain(-8)
    measure = accent + AudioSegment.silent(max(0, ms_per_beat - len(accent))) + (normal + AudioSegment.silent(max(0, ms_per_beat - len(normal)))) * (2 if signature == "3/4" else 3)
    track = (measure * (int((duration_sec * 1000) / len(measure)) + 1))[:int(duration_sec*1000)]
    buffer = io.BytesIO(); track.export(buffer, format="mp3", bitrate="32k", parameters=["-preset", "ultrafast"]); buffer.seek(0)
    return buffer

def generer_page_1_legende(titre, styles, mode_white=False):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; fig = Figure(figsize=(16, 8), facecolor=c_fond); ax = fig.subplots(); ax.set_facecolor(c_fond)
    ax.text(0, 2.5, titre, ha='center', va='bottom', fontproperties=get_font_cached(32, 'bold'), color=c_txt)
    img_pouce = load_image_asset(CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE)
    img_index = load_image_asset(CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX)
    y_pos=0.5
    rect = patches.FancyBboxPatch((-7.5, y_pos - 3.6), 15, 3.3, boxstyle="round,pad=0.1", linewidth=1.5, edgecolor=c_txt, facecolor=styles['LEGENDE_FOND'], zorder=0); ax.add_patch(rect)
    ax.text(0, y_pos - 0.6, "LÉGENDE", ha='center', fontsize=14, color=c_txt, fontproperties=get_font_cached(16, 'bold'))
    if img_pouce is not None: ax.add_artist(AnnotationBbox(OffsetImage(img_pouce, zoom=0.045), (-5.5, y_pos-1.2), frameon=False))
    ax.text(-4.5, y_pos-1.2, "= Pouce", ha='left', va='center', color=c_txt, fontproperties=get_font_cached(12, 'bold'))
    if img_index is not None: ax.add_artist(AnnotationBbox(OffsetImage(img_index, zoom=0.045), (-5.5, y_pos-1.8), frameon=False))
    ax.text(-4.5, y_pos-1.8, "= Index", ha='left', va='center', color=c_txt, fontproperties=get_font_cached(12, 'bold'))
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(-6, 4); ax.axis('off')
    return fig

def generer_page_notes(notes_page, idx, titre, config_acc, styles, options_visuelles, mode_white=False):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']
    t_min = notes_page[0]['temps']; t_max = notes_page[-1]['temps']
    fig = Figure(figsize=(16, max(6, (t_max - t_min + 1) * 0.75 + 6)), facecolor=c_fond); ax = fig.subplots(); ax.set_facecolor(c_fond)
    y_top = 2.5; y_bot = - (t_max - t_min) - 1.5
    if not mode_white and options_visuelles['use_bg']:
        img = load_image_asset(CHEMIN_IMAGE_FOND)
        if img is not None: 
            ratio = img.shape[1]/img.shape[0]; h_final = (10.5/ratio)*1.4
            ax.imshow(img, extent=[-5.25, 5.25, (y_top+y_bot)/2 - h_final/2, (y_top+y_bot)/2 + h_final/2], aspect='auto', zorder=-1, alpha=options_visuelles['alpha'])
    ax.text(0, y_top + 3.0, f"{titre} (Page {idx})", ha='center', va='bottom', fontproperties=get_font_cached(32, 'bold'), color=c_txt)
    ax.text(-3.5, y_top + 2.0, "Cordes de Gauche", ha='center', color=c_txt, fontproperties=get_font_cached(20, 'bold'))
    ax.text(3.5, y_top + 2.0, "Cordes de Droite", ha='center', color=c_txt, fontproperties=get_font_cached(20, 'bold'))
    ax.vlines(0, y_bot, y_top + 1.8, color=c_txt, lw=5, zorder=2)
    for code, props in config_acc.items():
        x = props['x']; note = props['n']; c = COULEURS_CORDES_REF.get(note, '#000000')
        ax.text(x, y_top + 1.3, code, ha='center', color='gray', fontproperties=get_font_cached(14, 'bold'))
        ax.text(x, y_top + 0.7, note, ha='center', color=c, fontproperties=get_font_cached(24, 'bold'))
        ax.vlines(x, y_bot, y_top, colors=c, lw=3, zorder=1)
    for t in range(t_min, t_max + 1): ax.axhline(y=-(t - t_min), color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)
    img_P = load_image_asset(CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE)
    img_I = load_image_asset(CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX)
    notes_by_y = {}
    for n in notes_page:
        y = -(n['temps'] - t_min); notes_by_y.setdefault(y, []).append(n)
        if n['corde'] == 'TEXTE':
            ax.text(0, y, n.get('message',''), ha='center', va='center', color='black', fontproperties=get_font_cached(16, 'bold'), bbox=dict(boxstyle="round,pad=0.5", fc=styles['PERLE_FOND'], ec=c_txt, lw=2), zorder=10)
        elif n['corde'] == 'SEPARATOR': ax.axhline(y, color=c_txt, lw=3, zorder=4)
        elif n['corde'] in config_acc:
            props = config_acc[n['corde']]; x = props['x']; c = COULEURS_CORDES_REF.get(props['n'], '#000000')
            ax.add_patch(plt.Circle((x, y), 0.30, color=styles['PERLE_FOND'], zorder=3))
            ax.add_patch(plt.Circle((x, y), 0.30, fill=False, edgecolor=c, lw=3, zorder=4))
            if 'doigt' in n:
                cur_img = img_I if n['doigt'] == 'I' else img_P
                if cur_img is not None: ax.add_artist(AnnotationBbox(OffsetImage(cur_img, zoom=0.045), (x-0.7, y+0.1), frameon=False, zorder=8))
    for y, group in notes_by_y.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(y_bot, y_top + 5); ax.axis('off')
    return fig

def generer_image_longue_calibree(sequence, config_acc, styles, dpi=72):
    if not sequence: return None, 0, 0
    t_min = sequence[0]['temps']; t_max = sequence[-1]['temps']
    y_max = 3.0; y_min = -(t_max - t_min) - 2.0
    fig = Figure(figsize=(16, (y_max - y_min) * 0.8), dpi=dpi, facecolor=styles['FOND']); ax = fig.subplots(); ax.set_facecolor(styles['FOND'])
    ax.set_ylim(y_min, y_max); ax.set_xlim(-7.5, 7.5)
    ax.vlines(0, y_min+1, y_max-1.2, color=styles['TEXTE'], lw=5, zorder=2)
    for code, props in config_acc.items():
        x = props['x']; c = COULEURS_CORDES_REF.get(props['n'], '#000000')
        ax.vlines(x, y_min+1, 2.0, colors=c, lw=3, zorder=1)
    notes_by_y = {}
    for n in sequence:
        if n['corde'] == 'PAGE_BREAK': continue
        y = -(n['temps'] - t_min); notes_by_y.setdefault(y, []).append(n)
        if n['corde'] in config_acc:
            props = config_acc[n['corde']]; x = props['x']; c = COULEURS_CORDES_REF.get(props['n'], '#000000')
            ax.add_patch(plt.Circle((x, y), 0.30, color=styles['PERLE_FOND'], zorder=3))
            ax.add_patch(plt.Circle((x, y), 0.30, fill=False, edgecolor=c, lw=3, zorder=4))
    for y, group in notes_by_y.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=styles['TEXTE'], lw=2, zorder=2)
    ax.axis('off')
    px_y0 = ax.transData.transform((0, 0))[1]; px_y1 = ax.transData.transform((0, -1))[1]
    buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=dpi, facecolor=styles['FOND'], bbox_inches=None); buf.seek(0)
    return buf, px_y0 - px_y1, (fig.get_figheight() * dpi) - px_y0
# ==============================================================================
# 🔧 SUITE LOGIQUE (VIDÉO & ÉTATS)
# ==============================================================================
def creer_video(img_buf, aud_buf, dur, metrics, bpm, fps=10):
    px_par_temps, offset = metrics; tmp_img = f"t_i_{random.randint(0,99)}.png"; tmp_aud = f"t_a_{random.randint(0,99)}.mp3"; out = f"vid_{random.randint(0,99)}.mp4"
    try:
        with open(tmp_img, "wb") as f: f.write(img_buf.getbuffer())
        with open(tmp_aud, "wb") as f: f.write(aud_buf.getbuffer())
        clip = ImageClip(tmp_img); w, h = clip.size
        speed = px_par_temps * (bpm / 60.0)
        mov = clip.set_position(lambda t: ('center', 100 - offset - (speed * t))).set_duration(dur)
        comp = CompositeVideoClip([ColorClip((w, 480), color=(229, 196, 163)).set_duration(dur), mov], size=(w, 480))
        aud = AudioFileClip(tmp_aud).subclip(0, dur)
        final = comp.set_audio(aud); final.fps = fps
        final.write_videofile(out, codec='libx264', audio_codec='aac', preset='ultrafast', logger=None)
        aud.close(); comp.close(); clip.close(); final.close()
        return out
    except Exception as e: st.error(str(e)); return None
    finally:
        if os.path.exists(tmp_img): os.remove(tmp_img)
        if os.path.exists(tmp_aud): os.remove(tmp_aud)

# ==============================================================================
# 🎛️ ÉTATS & INTERFACE
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

if len(BANQUE_TABLATURES) > 0: PREMIER_TITRE = list(BANQUE_TABLATURES.keys())[0]
else: PREMIER_TITRE = "Défaut"; BANQUE_TABLATURES[PREMIER_TITRE] = ""
if st.session_state.code_actuel == "": st.session_state.code_actuel = BANQUE_TABLATURES[PREMIER_TITRE].strip()
if "code" in st.query_params: st.session_state.code_actuel = st.query_params["code"]

def maj(): st.session_state.code_actuel = st.session_state.widget_input; st.session_state.partition_generated = False
def ajout(txt): st.session_state.code_actuel += "\n" + txt; st.session_state.widget_input = st.session_state.code_actuel
def charger_morceau(): 
    st.session_state.code_actuel = BANQUE_TABLATURES[st.session_state.selection_banque].strip()
    st.session_state.widget_input = st.session_state.code_actuel
    st.session_state.partition_generated = False
    plt.close('all'); gc.collect()

with st.sidebar:
    st.selectbox("📚 Morceau :", options=list(BANQUE_TABLATURES.keys()), key='selection_banque', on_change=charger_morceau)
    with st.expander("🎨 Options"):
        bg_color = "#e5c4a3"; use_bg_img = True; bg_alpha = 0.2
        force_white_print = st.checkbox("🖨️ Impression blanche", value=True)
    
    st.markdown("---")
    with st.expander("Gérer le fichier (JSON)"):
        st.download_button("💾 Sauver (.txt)", st.session_state.code_actuel, "tab.txt")
        up = st.file_uploader("📂 Charger", type=["txt","json","ngoni"])
        if up: 
            try:
                if up.name.endswith("txt"): s = io.StringIO(up.getvalue().decode("utf-8")).read(); st.session_state.code_actuel = s; st.session_state.widget_input = s
                else: d = json.load(up); st.session_state.code_actuel = d.get("code",""); st.session_state.stored_blocks = d.get("blocs",{})
                st.rerun()
            except: st.error("Erreur fichier")

        proj = {"code": st.session_state.code_actuel, "blocs": st.session_state.stored_blocks}
        st.download_button("💾 Sauver Projet (.ngoni)", json.dumps(proj), "projet.ngoni")

tab1, tab2, tab3 = st.tabs(["📝 Éditeur", "⚙️ Accordage", "🎬 Vidéo"])

with tab2:
    cg, cd = st.columns(2); acc_config = {}
    with cg:
        for i in range(1, 7): k=f"{i}G"; acc_config[k]={'x':POSITIONS_X[k],'n':st.selectbox(k, NOTES_GAMME, index=NOTES_GAMME.index(DEF_ACC[k]), key=k)}
    with cd:
        for i in range(1, 7): k=f"{i}D"; acc_config[k]={'x':POSITIONS_X[k],'n':st.selectbox(k, NOTES_GAMME, index=NOTES_GAMME.index(DEF_ACC[k]), key=k)}

with tab1:
    titre_partition = st.text_input("Titre", "Ma Tablature")
    c_in, c_view = st.columns([1, 1.5])
    
    with c_in:
        t_btn, t_vis, t_seq, t_blk = st.tabs(["🔘", "🎨", "🎹", "📦"])
        
        with t_btn: # BOUTONS COMPACTS
            mode = st.radio("Doigté", ["Auto", "Pouce", "Index"], horizontal=True)
            def add_btn(c): 
                s = " P" if mode=="Pouce" else " I" if mode=="Index" else " P" if c in ['1G','2G','3G','1D','2D','3D'] else " I"
                ajout(f"+ {c}{s}"); st.toast(f"{c} ajouté")
            
            # Ici on garde 2 colonnes même sur mobile pour que les boutons soient assez larges
            c_notes = st.columns(2) 
            with c_notes[0]: 
                st.caption("Gauche")
                for c in ['1G','2G','3G','4G','5G','6G']: st.button(c, key=f"b{c}", on_click=add_btn, args=(c,), use_container_width=True)
            with c_notes[1]:
                st.caption("Droite")
                for c in ['1D','2D','3D','4D','5D','6D']: st.button(c, key=f"b{c}", on_click=add_btn, args=(c,), use_container_width=True)
            
            c_tls = st.columns(2)
            with c_tls[0]: 
                st.button("↩️", on_click=lambda: (st.session_state.update(code_actuel="\n".join(st.session_state.code_actuel.split('\n')[:-1])), st.session_state.update(widget_input=st.session_state.code_actuel)), use_container_width=True)
                st.button("🟰", on_click=ajout, args=("=",), use_container_width=True)
            with c_tls[1]:
                st.button("🔇", on_click=ajout, args=("+ S",), use_container_width=True)
                st.button("📄", on_click=ajout, args=("+ PAGE",), use_container_width=True)

        with t_vis: # VISUEL (SCROLL HORIZONTAL ACTIVÉ)
            cols = st.columns([1]*6 + [0.2] + [1]*6)
            for i, c in enumerate(['6G','5G','4G','3G','2G','1G']): 
                with cols[i]: st.button(c, key=f"v{c}", on_click=add_btn, args=(c,))
            with cols[6]: st.write("|")
            for i, c in enumerate(['1D','2D','3D','4D','5D','6D']): 
                with cols[i+7]: st.button(c, key=f"v{c}", on_click=add_btn, args=(c,))

        with t_seq: # SEQUENCEUR (SCROLL HORIZONTAL ACTIVÉ)
            nb_t = st.number_input("Temps", 4, 32, 8, step=4)
            cols = st.columns([0.8] + [1]*12)
            clist = ['6G','5G','4G','3G','2G','1G','1D','2D','3D','4D','5D','6D']
            with cols[0]: st.write("T")
            for i, c in enumerate(clist): 
                with cols[i+1]: st.markdown(f"**{c}**")
            
            with st.container(height=300):
                for t in range(nb_t):
                    cc = st.columns([0.8] + [1]*12)
                    with cc[0]: st.caption(f"{t+1}")
                    for i, c in enumerate(clist):
                        k = f"sq_{t}_{c}"; st.session_state.seq_grid.setdefault(k, False)
                        with cc[i+1]: st.session_state.seq_grid[k] = st.checkbox("", key=k, value=st.session_state.seq_grid[k])
            
            if st.button("📥 Insérer"):
                res = ""
                for t in range(nb_t):
                    notes = [c for c in clist if st.session_state.seq_grid[f"sq_{t}_{c}"]]
                    if not notes: res += "+ S\n"
                    else:
                        for idx, n in enumerate(notes): res += ("+ " if idx==0 else "= ") + n + (" P" if n in ['1G','2G','3G','1D','2D','3D'] else " I") + "\n"
                ajout(res)

        with t_blk: # BLOCS
            bn = st.text_input("Nom Bloc"); bc = st.text_area("Contenu")
            if st.button("Sauver Bloc") and bn: st.session_state.stored_blocks[bn] = bc; st.success("OK")
            st.write(list(st.session_state.stored_blocks.keys()))
            struc = st.text_input("Structure (ex: A x2 + B)")
            if st.button("🚀 Générer") and struc: 
                full = compiler_arrangement(struc, st.session_state.stored_blocks)
                st.session_state.code_actuel = full; st.session_state.widget_input = full; st.rerun()

        st.text_area("Code", height=150, key="widget_input", on_change=maj)
        
        cb1, cb2 = st.columns(2)
        with cb1: 
             bpm_p = st.number_input("BPM", 40, 200, 100)
             if st.button("🎧 Play"): 
                 aud = generer_audio_mix(parser_texte(st.session_state.code_actuel), bpm_p, acc_config)
                 if aud: st.audio(aud, format="audio/mp3")
        with cb2:
             if st.button("🥁 Métronome"):
                 mb = generer_metronome(bpm_p, 60)
                 if mb: st.audio(mb, format="audio/mp3")

    with c_view:
        if st.button("🔄 RECHARGER VISUEL", type="primary"):
            st.session_state.partition_buffers = []
            seq = parser_texte(st.session_state.code_actuel)
            sty = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
            sty_w = {'FOND': 'white', 'TEXTE': 'black', 'PERLE_FOND': 'white', 'LEGENDE_FOND': 'white'}
            
            # Legende
            fig_l = generer_page_1_legende(titre_partition, sty)
            buf_l = io.BytesIO(); 
            if force_white_print: fig_dl = generer_page_1_legende(titre_partition, sty_w, True); fig_dl.savefig(buf_l, format='png', dpi=150, facecolor='white'); plt.close(fig_dl)
            else: fig_l.savefig(buf_l, format='png', dpi=150, facecolor=bg_color)
            buf_l.seek(0)
            st.session_state.partition_buffers.append({'type':'legende', 'img_ecran': fig_l, 'buf': buf_l})

            # Pages
            pgs = []; cur = []
            for n in seq:
                if n['corde']=='PAGE_BREAK': pgs.append(cur); cur=[]
                else: cur.append(n)
            if cur: pgs.append(cur)
            
            for i, p in enumerate(pgs):
                f_e = generer_page_notes(p, i+2, titre_partition, acc_config, sty, {'use_bg': use_bg_img, 'alpha': bg_alpha})
                b_p = io.BytesIO()
                if force_white_print: f_d = generer_page_notes(p, i+2, titre_partition, acc_config, sty_w, {}, True); f_d.savefig(b_p, format='png', dpi=150, facecolor='white'); plt.close(f_d)
                else: f_e.savefig(b_p, format='png', dpi=150, facecolor=bg_color)
                b_p.seek(0)
                st.session_state.partition_buffers.append({'type':'page', 'img_ecran': f_e, 'buf': b_p, 'idx': i+2})
            
            # PDF
            pdf = FPDF(); 
            for b in st.session_state.partition_buffers:
                pdf.add_page(); tmp=f"t_{random.randint(0,99)}.png"; b['buf'].seek(0)
                with open(tmp, "wb") as f: f.write(b['buf'].read())
                pdf.image(tmp, 10, 10, 190); os.remove(tmp)
            out = io.BytesIO(); out.write(pdf.output(dest='S').encode('latin-1')); out.seek(0)
            st.session_state.pdf_buffer = out

        for b in st.session_state.partition_buffers:
            st.pyplot(b['img_ecran'])
        
        if st.session_state.pdf_buffer:
            st.download_button("📕 PDF", st.session_state.pdf_buffer, "part.pdf", "application/pdf", type="primary")

with tab3:
    if st.button("🎥 Créer Vidéo"):
        if not HAS_MOVIEPY: st.error("Pas de moviepy")
        else:
            s = parser_texte(st.session_state.code_actuel); b = st.slider("BPM", 30, 200, 60); dur = (s[-1]['temps']+4)*(60/b)
            aud = generer_audio_mix(s, b, acc_config)
            img, px, off = generer_image_longue_calibree(s, acc_config, {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color}, 72)
            res = creer_video(img, aud, dur, (px, off), b)
            if res: st.video(res)