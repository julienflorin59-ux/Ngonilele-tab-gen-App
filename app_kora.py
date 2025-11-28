import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from google.colab import files
import os
from google.colab import drive

# ==============================================================================
# 🎛️ ZONE DE CONTRÔLE (MODIFIEZ TOUT CE QUE VOUS VOULEZ ICI)
# ==============================================================================

# 1. INFO DU MORCEAU
TITRE_PARTITION = "Tablature Manitoumani"

# 2. LA PARTITION (Votre texte codé)
PARTITION_TEXTE = """
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
+ PAGE
+   1G
+   3D
+   3G
+   5D
+   1G
+   3D
+   3G
+   5D
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

"""

# 3. LA GAMME ET L'ACCORDAGE (Règles des notes et des doigtés)
COULEURS_CORDES = {
    'C': '#FF0000', 'D': '#FF8C00', 'E': '#FFD700', 'F': '#32CD32',
    'G': '#00BFFF', 'A': '#00008B', 'B': '#9400D3'
}

CONFIG_INSTRUMENT = {
    '1G': {'x': -1, 'n': 'G'}, '2G': {'x': -2, 'n': 'C'}, '3G': {'x': -3, 'n': 'E'},
    '4G': {'x': -4, 'n': 'A'}, '5G': {'x': -5, 'n': 'C'}, '6G': {'x': -6, 'n': 'G'},
    '1D': {'x': 1, 'n': 'F'},  '2D': {'x': 2, 'n': 'A'},  '3D': {'x': 3, 'n': 'D'},
    '4D': {'x': 4, 'n': 'G'},  '5D': {'x': 5, 'n': 'B'},  '6D': {'x': 6, 'n': 'E'},
}

AUTOMATIC_FINGERING = {
    '1G': 'P', '2G': 'P', '3G': 'P', '1D': 'P', '2D': 'P', '3D': 'P',
    '4G': 'I', '5G': 'I', '6G': 'I', '4D': 'I', '5D': 'I', '6D': 'I',
}

TRADUCTION_NOTES = {'C':'do', 'D':'ré', 'E':'mi', 'F':'fa', 'G':'sol', 'A':'la', 'B':'si'}


# 4. FICHIERS ET IMAGES
CHEMIN_POLICE = '/content/drive/MyDrive/ML.ttf'
CHEMIN_ICON_INDEX = '/content/drive/MyDrive/ICO/icon_index.png'
CHEMIN_ICON_POUCE = '/content/drive/MyDrive/ICO/icon_pouce.png'
CHEMIN_IMAGE_FOND = '/content/drive/MyDrive/ICO/texture_kora.png'

# 5. RÉGLAGES VISUELS (IMAGE DE FOND)
ALPHA_IMAGE_FOND = 0.20
DECALAGE_IMAGE_X = 0.0
ECHELLE_IMAGE = 0.7
CORRECTION_HAUTEUR = 1.4

# 6. RÉGLAGES VISUELS (PAGE)
ZOOM_ICON = 0.045
DECALAGE_ICONE_X = 0.70

# 7. COULEURS DU STYLE
STYLE_VISUEL = {
    'FOND': '#e5c4a1', 'TEXTE': 'black', 'LEGENDE_FOND': '#e5c4a1', 'PERLE_FOND': '#e5c4a1'
}

# ==============================================================================
# ⛔ FIN DE LA ZONE DE CONTRÔLE
# ⛔ NE TOUCHEZ PAS AU CODE CI-DESSOUS (C'EST LE MOTEUR)
# ==============================================================================

# --- 0. INIT DRIVE ---
if not os.path.exists('/content/drive'):
    drive.mount('/content/drive')

# --- 1. FONCTIONS UTILITAIRES ---
def get_font(size, weight='normal', style='normal'):
    if os.path.exists(CHEMIN_POLICE):
        return fm.FontProperties(fname=CHEMIN_POLICE, size=size, weight=weight, style=style)
    return fm.FontProperties(family='sans-serif', size=size, weight=weight, style=style)

prop_titre = get_font(32, 'bold'); prop_texte = get_font(20, 'bold'); prop_note_us = get_font(24, 'bold')
prop_note_eu = get_font(18, 'normal', 'italic'); prop_standard = get_font(14, 'bold'); prop_numero = get_font(14, 'bold')
prop_annotation = get_font(16, 'bold'); prop_legende = get_font(12, 'bold')

# --- 2. FONCTION LÉGENDE ---
def dessiner_legende(ax, y_pos):
    c_txt = STYLE_VISUEL['TEXTE']; c_fond = STYLE_VISUEL['LEGENDE_FOND']; c_bulle = STYLE_VISUEL['PERLE_FOND']
    rect = patches.FancyBboxPatch((-7.5, y_pos - 3.6), 15, 3.3, boxstyle="round,pad=0.1", linewidth=1.5, edgecolor=c_txt, facecolor=c_fond, zorder=0)
    ax.add_patch(rect)
    ax.text(0, y_pos - 0.6, "LÉGENDE", ha='center', va='center', fontsize=14, fontweight='bold', color=c_txt, fontproperties=prop_annotation)
    x_icon_center = -5.5; x_text_align = -4.5; y_row1 = y_pos - 1.2; y_row2 = y_pos - 1.8; y_row3 = y_pos - 2.4; y_row4 = y_pos - 3.0
    if os.path.exists(CHEMIN_ICON_POUCE):
        ab = AnnotationBbox(OffsetImage(mpimg.imread(CHEMIN_ICON_POUCE), zoom=ZOOM_ICON), (x_icon_center, y_row1), frameon=False); ax.add_artist(ab)
    ax.text(x_text_align, y_row1, "= Pouce", ha='left', va='center', fontproperties=prop_legende, color=c_txt)
    if os.path.exists(CHEMIN_ICON_INDEX):
        ab = AnnotationBbox(OffsetImage(mpimg.imread(CHEMIN_ICON_INDEX), zoom=ZOOM_ICON), (x_icon_center, y_row2), frameon=False); ax.add_artist(ab)
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

# --- 3. PARSEUR ---
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
            doigt = None
            repetition = 1

            if len(parts) > 2:
                for p in parts[2].split():
                    p_upper = p.upper()
                    if p_upper.startswith('X') and p_upper[1:].isdigit(): repetition = int(p_upper[1:])
                    elif p_upper in ['I', 'P']: doigt = p_upper

            if not doigt and corde_valide in AUTOMATIC_FINGERING:
                doigt = AUTOMATIC_FINGERING[corde_valide]

            for i in range(repetition):
                current_time = t + i
                note = {'temps': current_time, 'corde': corde_valide}
                if doigt: note['doigt'] = doigt
                data.append(note)
                if i > 0: dernier_temps = current_time
        except: pass
    data.sort(key=lambda x: x['temps'])
    return data

# --- 4. MOTEUR D'AFFICHAGE ---
def afficher_kora_pages(sequence):
    if not sequence: return
    c_fond = STYLE_VISUEL['FOND']; c_txt = STYLE_VISUEL['TEXTE']; c_perle = STYLE_VISUEL['PERLE_FOND']
    pages_data = []; current_page = []
    for n in sequence:
        if n['corde'] == 'PAGE_BREAK':
            if current_page: pages_data.append(current_page); current_page = []
        else: current_page.append(n)
    if current_page: pages_data.append(current_page)

    print(f"👀 Affichage et Téléchargement de la Légende + {len(pages_data)} pages de notes...")

    nom_base = f"{TITRE_PARTITION.replace(' ', '_')}"

    # ==========================================================================
    # 🟢 PARTIE 1 : LA PAGE DE LÉGENDE (PAGE 1)
    # ==========================================================================
    fig_leg, ax_leg = plt.subplots(figsize=(16, 8), facecolor=c_fond); ax_leg.set_facecolor(c_fond)
    
    # ⚠️ IMAGE DE FOND SUPPRIMÉE ICI POUR LA LÉGENDE

    ax_leg.text(0, 2.5, TITRE_PARTITION, ha='center', va='bottom', fontproperties=prop_titre, color=c_txt)
    dessiner_legende(ax_leg, 0.5) # Dessine la légende au centre
    
    ax_leg.set_xlim(-7.5, 7.5); ax_leg.set_ylim(-6, 4); ax_leg.axis('off')

    nom_imp = f"{nom_base}_Page_1_Legende.png"
    plt.savefig(nom_imp, dpi=200, facecolor='white', bbox_inches='tight'); files.download(nom_imp)
    
    # Version écran couleur fond
    nom_ecran = f"{nom_base}_Ecran_1_Legende.png"; fig_leg.patch.set_facecolor(c_fond); ax_leg.set_facecolor(c_fond)
    plt.savefig(nom_ecran, dpi=200, facecolor=c_fond, bbox_inches='tight'); files.download(nom_ecran)
    plt.show(); plt.close()


    # ==========================================================================
    # 🟢 PARTIE 2 : LES PAGES DE NOTES (A PARTIR DE LA PAGE 2)
    # ==========================================================================
    for idx, notes_page in enumerate(pages_data):
        if not notes_page: continue
        t_min = notes_page[0]['temps']; t_max = notes_page[-1]['temps'];

        lignes_sur_page = t_max - t_min + 1
        lignes_base = lignes_sur_page 

        # Hauteur calculée sans l'espace légende additionnel
        hauteur_fig = (lignes_base * 0.75) + 6
        hauteur_fig = max(6, hauteur_fig)

        fig, ax = plt.subplots(figsize=(16, hauteur_fig), facecolor=c_fond); ax.set_facecolor(c_fond)

        y_top = 2.5; offset_legende = 0; y_top_cordes = y_top - offset_legende
        y_bot = - (t_max - t_min) - 1.5 - offset_legende

        if os.path.exists(CHEMIN_IMAGE_FOND):
            try:
                img_fond = mpimg.imread(CHEMIN_IMAGE_FOND); LARGEUR_REF = 15.0
                h_px, w_px = img_fond.shape[:2]; ratio = w_px / h_px
                largeur_finale = LARGEUR_REF * ECHELLE_IMAGE
                hauteur_finale = (largeur_finale / ratio) * CORRECTION_HAUTEUR
                x_center, y_center = DECALAGE_IMAGE_X, (y_top + y_bot) / 2
                extent = [x_center - largeur_finale/2, x_center + largeur_finale/2, y_center - hauteur_finale/2, y_center + hauteur_finale/2]
                ax.imshow(img_fond, extent=extent, aspect='auto', zorder=-1, alpha=ALPHA_IMAGE_FOND)
            except: pass

        # Numéro de page ajusté (+2 car page 1 est la légende)
        titre = f"{TITRE_PARTITION} (Page {idx+2})"
        ax.text(0, y_top + 3.0, titre, ha='center', va='bottom', fontproperties=prop_titre, color=c_txt)

        ax.text(-3.5, y_top_cordes + 2.0, "Cordes de Gauche", ha='center', va='bottom', fontproperties=prop_texte, color=c_txt)
        ax.text(3.5, y_top_cordes + 2.0, "Cordes de Droite", ha='center', va='bottom', fontproperties=prop_texte, color=c_txt)
        ax.vlines(0, y_bot, y_top_cordes + 1.8, color=c_txt, lw=5, zorder=2)

        for code, p in CONFIG_INSTRUMENT.items():
            x = p['x']
            c = COULEURS_CORDES[p['n']]
            ax.text(x, y_top_cordes + 1.3, code, ha='center', color='gray', fontproperties=prop_numero)
            ax.text(x, y_top_cordes + 0.7, p['n'], ha='center', color=c, fontproperties=prop_note_us)
            ax.text(x, y_top_cordes + 0.1, TRADUCTION_NOTES[p['n']], ha='center', color=c, fontproperties=prop_note_eu)
            ax.vlines(x, y_bot, y_top_cordes, colors=c, lw=3, zorder=1)

        map_labels = {}; last_sep = t_min - 1; sorted_notes = sorted(notes_page, key=lambda x: x['temps']); processed_t = set()
        for n in sorted_notes:
            t = n['temps']
            if n['corde'] in ['SEPARATOR', 'TEXTE']: last_sep = t; map_labels[t] = ""
            elif t not in processed_t: map_labels[t] = str(t - last_sep); processed_t.add(t)

        notes_par_temps_relatif = {}; rayon = 0.30
        for n in notes_page:
            t_absolu = n['temps']; y = -(t_absolu - t_min) - offset_legende
            if y not in notes_par_temps_relatif: notes_par_temps_relatif[y] = []
            notes_par_temps_relatif[y].append(n); code = n['corde']

            if code == 'TEXTE':
                bbox = dict(boxstyle="round,pad=0.5", fc=c_perle, ec=c_txt, lw=2)
                ax.text(0, y, n.get('message',''), ha='center', va='center', color='black', fontproperties=prop_annotation, bbox=bbox, zorder=10)
            elif code == 'SEPARATOR': ax.axhline(y, color=c_txt, lw=3, zorder=4)
            elif code == 'SILENCE':
                pass 
            elif code in CONFIG_INSTRUMENT:
                props = CONFIG_INSTRUMENT[code]; x = props['x']
                c = COULEURS_CORDES[props['n']]
                ax.add_patch(plt.Circle((x, y), rayon, color=c_perle, zorder=3)); ax.add_patch(plt.Circle((x, y), rayon, fill=False, edgecolor=c, lw=3, zorder=4))
                ax.text(x, y, map_labels.get(t_absolu, ""), ha='center', va='center', color='black', fontproperties=prop_standard, zorder=6)
                if 'doigt' in n:
                    doigt = n['doigt']; img_path = CHEMIN_ICON_INDEX if doigt == 'I' else CHEMIN_ICON_POUCE
                    succes = False
                    if os.path.exists(img_path):
                        try:
                            ab = AnnotationBbox(OffsetImage(mpimg.imread(img_path), zoom=ZOOM_ICON), (x - DECALAGE_ICONE_X, y + 0.1), frameon=False, zorder=8)
                            ax.add_artist(ab); succes = True
                        except: pass
                    if not succes: ax.text(x - 0.70, y, doigt, ha='center', va='center', color=c_txt, fontproperties=prop_standard, zorder=7)

        for y, group in notes_par_temps_relatif.items():
            xs = [CONFIG_INSTRUMENT[n['corde']]['x'] for n in group if n['corde'] in CONFIG_INSTRUMENT]
            if len(xs) > 1: ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)

        ax.set_xlim(-7.5, 7.5); ax.set_ylim(y_bot, y_top + 5); ax.axis('off')

        # Nommage des fichiers notes : Commence à Page_2
        nom_imp = f"{nom_base}_Print_{idx+2}.png"
        plt.savefig(nom_imp, dpi=200, facecolor='white', bbox_inches='tight'); files.download(nom_imp)
        nom_ecran = f"{nom_base}_Ecran_{idx+2}.png"; fig.patch.set_facecolor(c_fond); ax.set_facecolor(c_fond)
        plt.savefig(nom_ecran, dpi=200, facecolor=c_fond, bbox_inches='tight'); files.download(nom_ecran)
        plt.show(); plt.close()

# EXECUTION
ma_melodie = parser_texte(PARTITION_TEXTE)
afficher_kora_pages(ma_melodie)