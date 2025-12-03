with subtab_visu:
            afficher_header_style("🎨 Mode Visuel")
            
            # --- AJOUT SELECTEUR RYTHME ---
            c_doigt, c_rythme = st.columns(2)
            with c_doigt:
                st.radio("Doigté :", ["🖐️ Auto", "👍 Pouce (P)", "👆 Index (I)"], key="visu_mode_doigt", horizontal=True)
            with c_rythme:
                st.radio("Rythme par défaut :", ["+", "♪", "🎶", "♬"], key="visu_mode_rythme", horizontal=True, index=0)
            
            def ajouter_note_visuelle(corde):
                suffixe, nom_doigt = get_suffixe_doigt(corde, "visu_mode_doigt")
                symbol = st.session_state.visu_mode_rythme
                ajouter_texte(f"{symbol} {corde}{suffixe}")
                st.toast(f"✅ {corde} ajoutée ({symbol})", icon="🎵")
                
            def outil_visuel_wrapper(action, txt_code, msg_toast):
                if action == "ajouter": ajouter_texte(txt_code)
                elif action == "undo": annuler_derniere_ligne()
                st.toast(msg_toast, icon="🛠️")
                
            st.write("") # Petit espacement
            
            # --- MODIFICATION ICI : En-têtes explicites ---
            col_head_g, col_head_sep, col_head_d = st.columns([6, 0.2, 6])
            with col_head_g:
                st.markdown("<div style='text-align:center; font-weight:bold; color:#A67C52; margin-bottom:5px;'>Cordes de gauche</div>", unsafe_allow_html=True)
            with col_head_d:
                st.markdown("<div style='text-align:center; font-weight:bold; color:#A67C52; margin-bottom:5px;'>Cordes de droite</div>", unsafe_allow_html=True)
            # ----------------------------------------------

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
            with c_tools[0]: st.button("↩️", key="v_undo", on_click=outil_visuel_wrapper, args=("undo", "", "Annulé !"), use_container_width=True)
            with c_tools[1]: st.button("🟰", key="v_simul", on_click=outil_visuel_wrapper, args=("ajouter", "=", "Simultané"), use_container_width=True)
            with c_tools[2]: st.button("🔁", key="v_x2", on_click=outil_visuel_wrapper, args=("ajouter", "x2", "Doublé"), use_container_width=True)
            with c_tools[3]: st.button("🔇", key="v_sil", on_click=outil_visuel_wrapper, args=("ajouter", "+ S", "Silence"), use_container_width=True)
            with c_tools[4]: st.button("📄", key="v_page", on_click=outil_visuel_wrapper, args=("ajouter", "+ PAGE", "Page"), use_container_width=True)
            with c_tools[5]: st.button("📝", key="v_txt", on_click=outil_visuel_wrapper, args=("ajouter", "+ TXT Message", "Texte"), use_container_width=True)
            afficher_section_sauvegarde_bloc("visu")