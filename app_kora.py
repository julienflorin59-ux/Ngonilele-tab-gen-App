import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import io
import os

# ==============================================================================
# ⚙️ CONFIGURATION DE LA PAGE
# ==============================================================================
st.set_page_config(page_title="Générateur Tablature Ngonilélé", layout="wide", page_icon="🪕")

st.title("🪕 Générateur de Tablature Ngonilélé")
st.markdown("Créez vos partitions, réglez l'accordage et téléchargez le résultat.")

# ==============================================================================
# 🧠 MOTEUR LOGIQUE
# ==============================================================================

# --- Données par défaut ---
TEXTE_DEFAUT = """
1   4D   I
+   4G   I
+   5D   I
+   5G   I
+   4G   I
=   2D   P
+   3G   P
+   6D   I x2
+   2G   P
=   5G   I
"""

POSITIONS_X = {
    '1G': -1, '2G': -2, '3G': -3, '4G': -4, '5G': -5, '6G': -6,
    '1D': 1,  '2D': 2,  '3D': 3,  '4D': 4,  '5D': 5,  '6D': 6
}
COULEURS_CORDES_REF = {
    'C': '#FF0000', 'D': '#FF8C00', 'E': '#FFD700', 'F': '#32CD32',
    'G': '#00BFFF', 'A': '#00008B', 'B': '#9400D3'
}
TRADUCTION_NOTES = {'C':'do', 'D':'ré', 'E':'mi', 'F':'fa', 'G':'sol', 'A':'la', 'B':'si'}
AUTOMATIC_FINGERING = {'1G':'P','2G':'P','3G':'P','1D':'P','2D':'P','3D':'P','4G':'I','5G':'I','6G':'I','4D':'I','5D':'I','6D':'I'}

# --- Gestion des fichiers locaux (Optionnel) ---
# Si vous avez les fichiers sur votre PC, mettez les chemins ici. Sinon, le code utilisera des défauts.
CHEMIN_POLICE = 'ML.ttf' 
CHEMIN_ICON_POUCE = 'icon_pouce.png'
CHEMIN_ICON_INDEX = 'icon_index.png'
# J'ai renommé le fichier attendu ici :
CHEMIN_IMAGE_FOND = 'texture_ngonilele.png'

def get_font(size, weight='normal', style='normal'):
    if os.path.exists(CHEMIN_POLICE):
        return fm.FontProperties(fname=CHEMIN_POLICE, size=size, weight=weight, style=style)
    return fm.FontProperties(family='sans-serif', size=size, weight=weight, style=style)

def parser_texte(texte):
    data = []
    dernier_temps = 0
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
# 🎨 MOTEUR D'AFFICHAGE (Adapté pour Streamlit)
# ==============================================================================

def generer_page_matplotlib(notes_page, idx, titre, config_acc, styles, options_visuelles):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    
    t_min = notes_page[0]['temps']
    t_max = notes_page[-1]['temps']
    lignes_sur_page = t_max - t_min + 1
    hauteur_fig = max(6, (lignes_sur_page * 0.75) + 6)

    fig, ax = plt.subplots(figsize=(16, hauteur_fig), facecolor=c_fond)
    ax.set_facecolor(c_fond)

    y_top = 2.5; y_bot = - (t_max - t_min) - 1.5; y_top_cordes = y_top

    # Fonts
    prop_titre = get_font(32, 'bold')
    prop_texte = get_font(20, 'bold')
    prop_note_us = get_font(24, 'bold')
    prop_note_eu = get_font(18, 'normal', 'italic')
    prop_numero = get_font(14, 'bold')
    prop_standard = get_font(14, 'bold')
    prop_annotation = get_font(16, 'bold')

    # Image de fond
    if options_visuelles['use_bg'] and os.path.exists(CHEMIN_IMAGE_FOND):
        try:
            img_fond = mpimg.imread(CHEMIN_IMAGE_FOND)
            h_px, w_px = img_fond.shape[:2]; ratio = w_px / h_px
            largeur_finale = 15.0 * 0.7
            hauteur_finale = (largeur_finale / ratio) * 1.4
            y_center = (y_top + y_bot) / 2
            extent = [-largeur_finale/2, largeur_finale/2, y_center - hauteur_finale/2, y_center + hauteur_finale/2]
            ax.imshow(img_fond, extent=extent, aspect='auto', zorder=-1, alpha=options_visuelles['alpha'])
        except: pass

    # Titres et Structure
    ax.text(0, y_top + 3.0, f"{titre} (Page {idx})", ha='center', va='bottom', fontproperties=prop_titre, color=c_txt)
    ax.text(-3.5, y_top_cordes + 2.0, "Cordes de Gauche", ha='center', va='bottom', fontproperties=prop_texte, color=c_txt)
    ax.text(3.5, y_top_cordes + 2.0, "Cordes de Droite", ha='center', va='bottom', fontproperties=prop_texte, color=c_txt)
    ax.vlines(0, y_bot, y_top_cordes + 1.8, color=c_txt, lw=5, zorder=2)

    # Cordes
    for code, props in config_acc.items():
        x = props['x']; note = props['n']
        c = COULEURS_CORDES_REF.get(note, '#000000')
        ax.text(x, y_top_cordes + 1.3, code, ha='center', color='gray', fontproperties=prop_numero)
        ax.text(x, y_top_cordes + 0.7, note, ha='center', color=c, fontproperties=prop_note_us)
        ax.text(x, y_top_cordes + 0.1, TRADUCTION_NOTES.get(note, '?'), ha='center', color=c, fontproperties=prop_note_eu)
        ax.vlines(x, y_bot, y_top_cordes, colors=c, lw=3, zorder=1)

    # Notes
    map_labels = {}; last_sep = t_min - 1; sorted_notes = sorted(notes_page, key=lambda x: x['temps']); processed_t = set()
    for n in sorted_notes:
        t = n['temps']
        if n['corde'] in ['SEPARATOR', 'TEXTE']: last_sep = t
        elif t not in processed_t: map_labels[t] = str(t - last_sep); processed_t.add(t)

    notes_par_temps_relatif = {}
    rayon = 0.30
    
    for n in notes_page:
        t_absolu = n['temps']; y = -(t_absolu - t_min)
        if y not in notes_par_temps_relatif: notes_par_temps_relatif[y] = []
        notes_par_temps_relatif[y].append(n); code = n['corde']

        if code == 'TEXTE':
            bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt, lw=2)
            ax.text(0, y, n.get('message',''), ha='center', va='center', color='black', fontproperties=prop_annotation, bbox=bbox, zorder=10)
        elif code == 'SEPARATOR': ax.axhline(y, color=c_txt, lw=3, zorder=4)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']; c = COULEURS_CORDES_REF.get(props['n'], '#000000')
            ax.add_patch(plt.Circle((x, y), rayon, color=c_perle, zorder=3))
            ax.add_patch(plt.Circle((x, y), rayon, fill=False, edgecolor=c, lw=3, zorder=4))
            ax.text(x, y, map_labels.get(t_absolu, ""), ha='center', va='center', color='black', fontproperties=prop_standard, zorder=6)
            
            # Doigts (Images ou Texte)
            if 'doigt' in n:
                doigt = n['doigt']
                img_path = CHEMIN_ICON_INDEX if doigt == 'I' else CHEMIN_ICON_POUCE
                succes_img = False
                if os.path.exists(img_path):
                    try:
                        ab = AnnotationBbox(OffsetImage(mpimg.imread(img_path), zoom=0.045), (x - 0.70, y + 0.1), frameon=False, zorder=8)
                        ax.add_artist(ab); succes_img = True
                    except: pass
                if not succes_img:
                    ax.text(x - 0.70, y, doigt, ha='center', va='center', color=c_txt, fontproperties=prop_standard, zorder=7)

    # Liaisons simultanées
    for y, group in notes_par_temps_relatif.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)

    ax.set_xlim(-7.5, 7.5); ax.set_ylim(y_bot, y_top + 5); ax.axis('off')
    return fig

# ==============================================================================
# 🎛️ INTERFACE STREAMLIT
# ==============================================================================

# 1. BARRE LATÉRALE (Contrôles Globaux)
with st.sidebar:
    st.header("🎚️ Réglages")
    titre_partition = st.text_input("Titre de la partition", "Tablature Ngonilélé")
    
    with st.expander("🎨 Apparence"):
        bg_color = st.color_picker("Couleur de fond", "#e5c4a1")
        use_bg_img = st.checkbox("Texture Ngonilélé (si image présente)", True)
        bg_alpha = st.slider("Transparence Texture", 0.0, 1.0, 0.2)

# 2. ONGLETS PRINCIPAUX
tab1, tab2 = st.tabs(["📝 Éditeur & Partition", "⚙️ Accordage"])

with tab2:
    st.subheader("Configuration des cordes")
    col_g, col_d = st.columns(2)
    acc_config = {}
    notes_gamme = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
    
    # Valeurs par défaut
    DEF_ACC = {'1G':'G','2G':'C','3G':'E','4G':'A','5G':'C','6G':'G','1D':'F','2D':'A','3D':'D','4D':'G','5D':'B','6D':'E'}

    with col_g:
        st.write("**Main Gauche**")
        for i in range(1, 7):
            k = f"{i}G"
            val = st.selectbox(f"Corde {k}", notes_gamme, index=notes_gamme.index(DEF_ACC[k]), key=k)
            acc_config[k] = {'x': POSITIONS_X[k], 'n': val}
    
    with col_d:
        st.write("**Main Droite**")
        for i in range(1, 7):
            k = f"{i}D"
            val = st.selectbox(f"Corde {k}", notes_gamme, index=notes_gamme.index(DEF_ACC[k]), key=k)
            acc_config[k] = {'x': POSITIONS_X[k], 'n': val}

with tab1:
    col_input, col_view = st.columns([1, 2])
    
    with col_input:
        st.subheader("Code")
        texte_input = st.text_area("Saisissez votre tablature ici :", TEXTE_DEFAUT, height=600)
        
    with col_view:
        st.subheader("Aperçu")
        if st.button("🔄 Générer la partition", type="primary"):
            
            styles = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
            opts = {'use_bg': use_bg_img, 'alpha': bg_alpha}
            
            sequence = parser_texte(texte_input)
            
            # Découpage en pages
            pages_data = []; current_page = []
            for n in sequence:
                if n['corde'] == 'PAGE_BREAK':
                    if current_page: pages_data.append(current_page); current_page = []
                else: current_page.append(n)
            if current_page: pages_data.append(current_page)
            
            if not pages_data:
                st.warning("Aucune note détectée.")
            else:
                for idx, page in enumerate(pages_data):
                    fig = generer_page_matplotlib(page, idx+1, titre_partition, acc_config, styles, opts)
                    st.pyplot(fig)
                    
                    # Bouton de téléchargement pour chaque page
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", dpi=200, facecolor=bg_color, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(
                        label=f"⬇️ Télécharger Page {idx+1}",
                        data=buf,
                        file_name=f"{titre_partition}_Page_{idx+1}.png",
                        mime="image/png"
                    )
                    plt.close(fig)