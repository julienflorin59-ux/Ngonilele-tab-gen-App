import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import io
import os
import urllib.parse # Indispensable pour le lien email

# ==============================================================================
# 🎵 BANQUE DE DONNÉES
# ==============================================================================
BANQUE_TABLATURES = {
    "--- Nouveau / Vide ---": """
1   4D
+   4G
""",
    "Manitoumani : -M- & Lamomali": """

1  4D   I
+   4G   I
+   5D   I
+   5G   I
+   4G   I
=   2D   P
+   3G   P
+   6D   I x2
+   2G   P
=   5G   I
+  3G   P
+  6D   I x2
+  2G   P
=  5G   I
+ 3G   P
+ 6D   I x2
+ 2G   P
= 5G   I
+   TXT  REPETER 2x (Reprendre au début)
+   PAGE
+   4D   I
+   4G   I
+   5D   I
+   5G   I
+   4G   I
=   1D   P
+   2G   P
+   6D   I  x2
+   2G   P
=   4G   I
+   1D   P
+   2G   P
+   6D   I  x2
+   2G   P
=   4G   I
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
+ 4D   I
+ PAGE
+   4G   I
+   5D   I
+   5G   I
+   4G   I
=   2D   P
+   3G   P
+   6D   I x2
+   2G   P
=   5G   I
+  3G   P
+  6D   I x2
+  2G   P
=  5G   I
+ 3G   P
+ 6D   I x2
+ 2G   P
= 5G   I
"""}

# ==============================================================================
# ⚙️ CONFIGURATION DE LA PAGE
# ==============================================================================
st.set_page_config(page_title="Générateur Tablature Ngonilélé", layout="wide", page_icon="🪕")

st.title("🪕 Générateur de Tablature Ngonilélé")
st.markdown("Créez vos partitions, réglez l'accordage et téléchargez le résultat.")

# ==============================================================================
# 🧠 MOTEUR LOGIQUE
# ==============================================================================

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

# --- Chemins ---
CHEMIN_POLICE = 'ML.ttf' 
CHEMIN_IMAGE_FOND = 'texture_ngonilele.png'
CHEMIN_ICON_POUCE = 'icon_pouce.png'
CHEMIN_ICON_INDEX = 'icon_index.png'
CHEMIN_ICON_POUCE_BLANC = 'icon_pouce_blanc.png'
CHEMIN_ICON_INDEX_BLANC = 'icon_index_blanc.png'

def get_font(size, weight='normal', style='normal'):
    if os.path.exists(CHEMIN_POLICE):
        return fm.FontProperties(fname=CHEMIN_POLICE, size=size, weight=weight, style=style)
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
# 🎨 MOTEUR D'AFFICHAGE
# ==============================================================================

def dessiner_contenu_legende(ax, y_pos, styles, mode_white=False):
    c_txt = styles['TEXTE']; c_fond = styles['LEGENDE_FOND']; c_bulle = styles['PERLE_FOND']
    prop_annotation = get_font(16, 'bold'); prop_legende = get_font(12, 'bold')
    path_pouce = CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE
    path_index = CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX

    rect = patches.FancyBboxPatch((-7.5, y_pos - 3.6), 15, 3.3, boxstyle="round,pad=0.1", linewidth=1.5, edgecolor=c_txt, facecolor=c_fond, zorder=0)
    ax.add_patch(rect)
    ax.text(0, y_pos - 0.6, "LÉGENDE", ha='center', va='center', fontsize=14, fontweight='bold', color=c_txt, fontproperties=prop_annotation)
    
    x_icon_center = -5.5; x_text_align = -4.5; y_row1 = y_pos - 1.2; y_row2 = y_pos - 1.8; y_row3 = y_pos - 2.4; y_row4 = y_pos - 3.0
    
    if os.path.exists(path_pouce):
        ab = AnnotationBbox(OffsetImage(mpimg.imread(path_pouce), zoom=0.045), (x_icon_center, y_row1), frameon=False); ax.add_artist(ab)
    ax.text(x_text_align, y_row1, "= Pouce", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    if os.path.exists(path_index):
        ab = AnnotationBbox(OffsetImage(mpimg.imread(path_index), zoom=0.045), (x_icon_center, y_row2), frameon=False); ax.add_artist(ab)
    ax.text(x_text_align, y_row2, "= Index", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    
    offsets = [-0.7, 0, 0.7]
    for i, off in enumerate(offsets):
        c = plt.Circle((x_icon_center + off, y_row3), 0.25, facecolor=c_bulle, edgecolor=c_txt, lw=2); ax.add_patch(c)
        ax.text(x_icon_center + off, y_row3, str(i+1), ha='center', va='center', fontsize=12, fontweight='bold', color=c_txt)
    ax.text(x_text_align, y_row3, "= Ordre de jeu", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    
    x_simul_end = x_icon_center + 1.4
    ax.plot([x_icon_center - 0.7, x_simul_end - 0.7], [y_row4, y_row4], color=c_txt, lw=3, zorder=1)
    ax.add_patch(plt.Circle((x_icon_center - 0.7, y_row4), 0.25, facecolor=c_bulle, edgecolor=c_txt, lw=2, zorder=2))
    ax.add_patch(plt.Circle((x_simul_end - 0.7, y_row4), 0.25, facecolor=c_bulle, edgecolor=c_txt, lw=2, zorder=2))
    ax.text(x_text_align, y_row4, "= Notes simultanées", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    
    x_droite = 1.5; y_text_top = y_pos - 1.2; line_height = 0.45
    ax.text(x_droite, y_text_top, "1G = 1ère corde à gauche", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    ax.text(x_droite, y_text_top - line_height, "2G = 2ème corde à gauche", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    ax.text(x_droite, y_text_top - line_height*2, "1D = 1ère corde à droite", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    ax.text(x_droite, y_text_top - line_height*3, "2D = 2ème corde à droite", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    ax.text(x_droite, y_text_top - line_height*4, "(Etc...)", ha='left', va='center', fontproperties=prop_legende, color=c_txt)

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
    
    t_min = notes_page[0]['temps']; t_max = notes_page[-1]['temps']
    lignes_sur_page = t_max - t_min + 1
    hauteur_fig = max(6, (lignes_sur_page * 0.75) + 6)

    fig, ax = plt.subplots(figsize=(16, hauteur_fig), facecolor=c_fond)
    ax.set_facecolor(c_fond)
    y_top = 2.5; y_bot = - (t_max - t_min) - 1.5; y_top_cordes = y_top

    # Fonts
    prop_titre = get_font(32, 'bold'); prop_texte = get_font(20, 'bold')
    prop_note_us = get_font(24, 'bold'); prop_note_eu = get_font(18, 'normal', 'italic')
    prop_numero = get_font(14, 'bold'); prop_standard = get_font(14, 'bold')
    prop_annotation = get_font(16, 'bold')

    if not mode_white and options_visuelles['use_bg'] and os.path.exists(CHEMIN_IMAGE_FOND):
        try:
            img_fond = mpimg.imread(CHEMIN_IMAGE_FOND)
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

    map_labels = {}; last_sep = t_min - 1; sorted_notes = sorted(notes_page, key=lambda x: x['temps']); processed_t = set()
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
        elif code == 'SEPARATOR': ax.axhline(y, color=c_txt, lw=3, zorder=4)
        elif code in config_acc:
            props = config_acc[code]; x = props['x']; c = COULEURS_CORDES_REF.get(props['n'], '#000000')
            ax.add_patch(plt.Circle((x, y), rayon, color=c_perle, zorder=3))
            ax.add_patch(plt.Circle((x, y), rayon, fill=False, edgecolor=c, lw=3, zorder=4))
            ax.text(x, y, map_labels.get(t_absolu, ""), ha='center', va='center', color='black', fontproperties=prop_standard, zorder=6)
            if 'doigt' in n:
                doigt = n['doigt']; img_path = path_index if doigt == 'I' else path_pouce
                succes_img = False
                if os.path.exists(img_path):
                    try:
                        ab = AnnotationBbox(OffsetImage(mpimg.imread(img_path), zoom=0.045), (x - 0.70, y + 0.1), frameon=False, zorder=8)
                        ax.add_artist(ab); succes_img = True
                    except: pass
                if not succes_img: ax.text(x - 0.70, y, doigt, ha='center', va='center', color=c_txt, fontproperties=prop_standard, zorder=7)

    for y, group in notes_par_temps_relatif.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]
        if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)

    ax.set_xlim(-7.5, 7.5); ax.set_ylim(y_bot, y_top + 5); ax.axis('off')
    return fig

# ==============================================================================
# 🎛️ INTERFACE STREAMLIT
# ==============================================================================

# Gestion de la mémoire (State)
if 'code_actuel' not in st.session_state:
    st.session_state.code_actuel = BANQUE_TABLATURES["Exemple : Rythme de base"]
if 'gen_active' not in st.session_state:
    st.session_state.gen_active = False

# Fonction pour charger un morceau (Mise à jour via clé)
def charger_morceau():
    choix = st.session_state.selection_banque
    if choix in BANQUE_TABLATURES:
        st.session_state.code_actuel = BANQUE_TABLATURES[choix].strip()

# Fonction de Callback pour le texte
def mise_a_jour_texte():
    st.session_state.code_actuel = st.session_state.widget_input

# 1. BARRE LATÉRALE
with st.sidebar:
    st.header("🎚️ Réglages")
    
    # --- BANQUE DE DONNÉES ---
    st.markdown("### 📚 Banque de Morceaux")
    st.selectbox(
        "Choisir un morceau :", 
        options=list(BANQUE_TABLATURES.keys()), 
        key='selection_banque',
        on_change=charger_morceau
    )
    st.caption("⚠️ Remplacera le texte actuel.")
    st.markdown("---")
    
    titre_partition = st.text_input("Titre de la partition", "Tablature Ngonilélé")
    with st.expander("🎨 Apparence", expanded=True):
        bg_color = st.color_picker("Couleur de fond", "#e5c4a1")
        use_bg_img = st.checkbox("Texture Ngonilélé (si image présente)", True)
        bg_alpha = st.slider("Transparence Texture", 0.0, 1.0, 0.2)
        st.markdown("---")
        force_white_print = st.checkbox("🖨️ Fond blanc pour impression", value=True, help="Si coché, l'image téléchargée sera sur fond blanc avec icônes blanches.")
    
    # --- SECTION CONTRIBUTION ---
    st.markdown("---")
    st.markdown("### 🤝 Contribuer")
    st.write("Vous avez créé un super morceau ? Envoyez-le moi pour l'ajouter à la banque !")
    
    # Prépare le lien mailto
    mon_email = "julienflorin59@gmail.com" # ⚠️ REMPLACE CECI PAR TON EMAIL !
    sujet_mail = f"Nouvelle Tablature Ngonilélé : {titre_partition}"
    corps_mail = f"Bonjour,\n\nVoici une proposition de tablature :\n\nTitre : {titre_partition}\n\nCode :\n{st.session_state.code_actuel}"
    
    # Encodage URL propre
    sujet_encoded = urllib.parse.quote(sujet_mail)
    corps_encoded = urllib.parse.quote(corps_mail)
    mailto_link = f"mailto:{mon_email}?subject={sujet_encoded}&body={corps_encoded}"
    
    st.markdown(f'''
    <a href="{mailto_link}" target="_blank">
        <button style="width:100%; background-color:#FF4B4B; color:white; padding:10px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">
            📧 Envoyer ma partition
        </button>
    </a>
    ''', unsafe_allow_html=True)

# 2. ONGLETS PRINCIPAUX
tab1, tab2 = st.tabs(["📝 Éditeur & Partition", "⚙️ Accordage"])

with tab2:
    st.subheader("Configuration des cordes")
    col_g, col_d = st.columns(2)
    acc_config = {}
    notes_gamme = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
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
        
        # --- UPLOAD FICHIER TXT ---
        with st.expander("❓ Comment sauvegarder et recharger mes morceaux ?"):
            st.markdown("""
            1. **Sauvegarder :** Cliquez sur le bouton **"💾 Sauvegarder le code"** en bas. Un fichier `.txt` sera téléchargé sur votre ordinateur.
            2. **Recharger :** Au prochain lancement, glissez ce fichier `.txt` dans la zone **"📂 Charger un fichier"** ci-dessous pour reprendre votre travail.
            """)
            
        uploaded_file = st.file_uploader("📂 Charger un fichier sauvegardé (.txt)", type="txt")
        if uploaded_file is not None:
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            content = stringio.read()
            if content != st.session_state.code_actuel:
                st.session_state.code_actuel = content
                st.rerun()
        
        # --- AIDE ---
        with st.expander("ℹ️ Aide syntaxe (Code)"):
            st.markdown("""
            - **Chiffre** (ex: `1`) : Début d'une mesure (Temps 1).
            - **+** : Temps suivant.
            - **=** : Même temps (simultané).
            - **4G, 2D...** : La corde (Chiffre + G/D).
            - **S** : Silence (laisse un espace vide).
            - **PAGE** : Force un saut de page ici.
            - **TXT** : Ajouter un texte (ex: `+ TXT Refrain`).
            - **x2** : Répéter (ex: `+ 6D I x2`).
            """)
        
        # ZONE DE TEXTE (LIAISON NATIVE avec session_state)
        st.text_area(
            "Saisissez votre tablature ici :", 
            value=st.session_state.code_actuel, 
            height=500, 
            key="widget_input",
            on_change=mise_a_jour_texte
        )

        # BOUTON SAUVEGARDE TXT
        st.download_button(
            label="💾 Sauvegarder le code (.txt)",
            data=st.session_state.code_actuel,
            file_name=f"{titre_partition.replace(' ', '_')}.txt",
            mime="text/plain"
        )
        
    with col_view:
        st.subheader("Aperçu")
        
        if st.button("🔄 Générer la partition", type="primary"):
            st.session_state.gen_active = True

        if st.session_state.gen_active:
            
            # Styles
            styles_ecran = {'FOND': bg_color, 'TEXTE': 'black', 'PERLE_FOND': bg_color, 'LEGENDE_FOND': bg_color}
            styles_print = {'FOND': 'white', 'TEXTE': 'black', 'PERLE_FOND': 'white', 'LEGENDE_FOND': 'white'}
            options_visuelles = {'use_bg': use_bg_img, 'alpha': bg_alpha}
            sequence = parser_texte(st.session_state.code_actuel)
            
            # 1. LEGENDE
            st.markdown("### Page 1 : Légende")
            fig_leg_ecran = generer_page_1_legende(titre_partition, styles_ecran, mode_white=False)
            st.pyplot(fig_leg_ecran)
            
            if force_white_print:
                fig_leg_dl = generer_page_1_legende(titre_partition, styles_print, mode_white=True)
            else:
                fig_leg_dl = fig_leg_ecran

            buf_leg = io.BytesIO()
            fig_leg_dl.savefig(buf_leg, format="png", dpi=200, facecolor=styles_print['FOND'] if force_white_print else bg_color, bbox_inches='tight')
            buf_leg.seek(0)
            st.download_button(label="⬇️ Télécharger Légende", data=buf_leg, file_name=f"{titre_partition}_Legende.png", mime="image/png")
            plt.close(fig_leg_ecran)
            if force_white_print: plt.close(fig_leg_dl)
            
            # 2. NOTES
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
                    st.markdown(f"### Page {idx+2}")
                    fig_ecran = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_ecran, options_visuelles, mode_white=False)
                    st.pyplot(fig_ecran)
                    
                    if force_white_print:
                         fig_dl = generer_page_notes(page, idx+2, titre_partition, acc_config, styles_print, options_visuelles, mode_white=True)
                    else:
                         fig_dl = fig_ecran

                    buf = io.BytesIO()
                    fig_dl.savefig(buf, format="png", dpi=200, facecolor=styles_print['FOND'] if force_white_print else bg_color, bbox_inches='tight')
                    buf.seek(0)
                    st.download_button(label=f"⬇️ Télécharger Page {idx+2}", data=buf, file_name=f"{titre_partition}_Page_{idx+2}.png", mime="image/png")
                    plt.close(fig_ecran)
                    if force_white_print: plt.close(fig_dl)