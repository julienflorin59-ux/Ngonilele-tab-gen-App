def generer_page_notes(notes_page, idx, titre, config_acc, styles, options_visuelles, mode_white=False):
    c_fond = styles['FOND']; c_txt = styles['TEXTE']; c_perle = styles['PERLE_FOND']
    path_pouce = CHEMIN_ICON_POUCE_BLANC if mode_white else CHEMIN_ICON_POUCE
    path_index = CHEMIN_ICON_INDEX_BLANC if mode_white else CHEMIN_ICON_INDEX
    
    t_min = notes_page[0]['temps']
    t_max = notes_page[-1]['temps']
    lignes_sur_page = t_max - t_min + 1
    
    # Calcul dynamique de la hauteur
    hauteur_fig = max(6, (lignes_sur_page * 0.75) + 6)
    
    fig, ax = plt.subplots(figsize=(16, hauteur_fig), facecolor=c_fond)
    ax.set_facecolor(c_fond)
    
    y_top = 2.5
    y_bot = - (t_max - t_min) - 1.5
    y_top_cordes = y_top
    
    prop_titre = get_font(32, 'bold'); prop_texte = get_font(20, 'bold')
    prop_note_us = get_font(24, 'bold'); prop_note_eu = get_font(18, 'normal', 'italic')
    prop_numero = get_font(14, 'bold'); prop_standard = get_font(14, 'bold')
    prop_annotation = get_font(16, 'bold')
    
    # Fond texturé (Optionnel)
    if not mode_white and options_visuelles['use_bg'] and os.path.exists(CHEMIN_IMAGE_FOND):
        try: 
            img_fond = mpimg.imread(CHEMIN_IMAGE_FOND)
            h_px, w_px = img_fond.shape[:2]
            ratio = w_px / h_px
            largeur_finale = 15.0 * 0.7
            hauteur_finale = (largeur_finale / ratio) * 1.4
            y_center = (y_top + y_bot) / 2
            extent = [-largeur_finale/2, largeur_finale/2, y_center - hauteur_finale/2, y_center + hauteur_finale/2]
            ax.imshow(img_fond, extent=extent, aspect='auto', zorder=-1, alpha=options_visuelles['alpha'])
        except: pass
        
    ax.text(0, y_top + 3.0, f"{titre} (Page {idx})", ha='center', va='bottom', fontproperties=prop_titre, color=c_txt)
    ax.text(-3.5, y_top_cordes + 2.0, "Cordes de Gauche", ha='center', va='bottom', fontproperties=prop_texte, color=c_txt)
    ax.text(3.5, y_top_cordes + 2.0, "Cordes de Droite", ha='center', va='bottom', fontproperties=prop_texte, color=c_txt)
    
    # Barre centrale
    ax.vlines(0, y_bot, y_top_cordes + 1.8, color=c_txt, lw=5, zorder=2)
    
    # Cordes
    for code, props in config_acc.items():
        x = props['x']; note = props['n']; c = COULEURS_CORDES_REF.get(note, '#000000')
        ax.text(x, y_top_cordes + 1.3, code, ha='center', color='gray', fontproperties=prop_numero)
        ax.text(x, y_top_cordes + 0.7, note, ha='center', color=c, fontproperties=prop_note_us)
        ax.text(x, y_top_cordes + 0.1, TRADUCTION_NOTES.get(note, '?'), ha='center', color=c, fontproperties=prop_note_eu)
        ax.vlines(x, y_bot, y_top_cordes, colors=c, lw=3, zorder=1)
    
    # Lignes horizontales (temps)
    for t in range(t_min, t_max + 1):
        y = -(t - t_min)
        ax.axhline(y=y, color='#666666', linestyle='-', linewidth=1, alpha=0.7, zorder=0.5)

    # Placement des notes
    map_labels = {}; last_sep = t_min - 1
    sorted_notes = sorted(notes_page, key=lambda x: x['temps'])
    processed_t = set()
    
    for n in sorted_notes:
        t = n['temps']
        if n['corde'] in ['SEPARATOR', 'TEXTE']: last_sep = t
        elif t not in processed_t: 
            map_labels[t] = str(t - last_sep)
            processed_t.add(t)
            
    notes_par_temps_relatif = {}; rayon = 0.30
    
    for n in notes_page:
        t_absolu = n['temps']; y = -(t_absolu - t_min)
        if y not in notes_par_temps_relatif: notes_par_temps_relatif[y] = []
        notes_par_temps_relatif[y].append(n)
        
        code = n['corde']
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
                doigt = n['doigt']; img_path = path_index if doigt == 'I' else path_pouce; succes_img = False
                if os.path.exists(img_path):
                    try: 
                        ab = AnnotationBbox(OffsetImage(mpimg.imread(img_path), zoom=0.045), (x - 0.70, y + 0.1), frameon=False, zorder=8)
                        ax.add_artist(ab); succes_img = True
                    except: pass
                if not succes_img: 
                    ax.text(x - 0.70, y, doigt, ha='center', va='center', color=c_txt, fontproperties=prop_standard, zorder=7)
                    
    # Liaisons (simultanées)
    for y, group in notes_par_temps_relatif.items():
        xs = [config_acc[n['corde']]['x'] for n in group if n['corde'] in config_acc]
        if len(xs) > 1: 
            ax.plot([min(xs), max(xs)], [y, y], color=c_txt, lw=2, zorder=2)
            
    ax.set_xlim(-7.5, 7.5)
    ax.set_ylim(y_bot, y_top + 5)
    ax.axis('off')
    
    return fig