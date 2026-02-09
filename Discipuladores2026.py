with col_graf:
                # 1. VISUALIZAÇÃO DE IMPACTO SEMANAL (Barras Empilhadas)
                st.write("#### 🎯 Impacto por Célula (Membros + Visitantes)")
                df_l_p = df_sem.groupby('Líder')[['Célula']].sum().reset_index()
                df_l_v = df_v_sem.groupby('Líder')[['Vis_Celula']].sum().reset_index()
                df_impacto = pd.merge(df_l_p, df_l_v, on='Líder', how='left').fillna(0)
                
                fig_impacto = go.Figure()
                fig_impacto.add_trace(go.Bar(
                    x=df_impacto['Líder'], y=df_impacto['Célula'], 
                    name="Membros/FA", marker_color='#0284C7',
                    text=df_impacto['Célula'], textposition='auto'
                ))
                fig_impacto.add_trace(go.Bar(
                    x=df_impacto['Líder'], y=df_impacto['Vis_Celula'], 
                    name="Visitantes", marker_color='#FACC15',
                    text=df_impacto['Vis_Celula'], textposition='auto'
                ))
                fig_impacto.update_layout(
                    template="plotly_dark", barmode='stack', height=350,
                    margin=dict(l=10, r=10, t=30, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_impacto, use_container_width=True)
                
                # 2. LINHA DE TENDÊNCIA E CRESCIMENTO (Com Rótulos no Topo)
                st.write("#### 📈 Tendência de Frequência Total")
                # Agrupando por data para ver o crescimento do distrito ou células filtradas
                df_ev_p = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)].groupby('Data')['Célula'].sum().reset_index()
                df_ev_v = st.session_state.db_visitantes[st.session_state.db_visitantes['Líder'].isin(lids_f)].groupby('Data')['Vis_Celula'].sum().reset_index()
                df_tendencia = pd.merge(df_ev_p, df_ev_v, on='Data', how='outer').fillna(0).sort_values('Data')

                fig_tendencia = go.Figure()
                # Linha de Membros
                fig_tendencia.add_trace(go.Scatter(
                    x=df_tendencia['Data'], y=df_tendencia['Célula'],
                    name="Público Interno", mode='lines+markers+text',
                    text=df_tendencia['Célula'], textposition="top center",
                    line=dict(color='#38BDF8', width=4),
                    fill='tozeroy', fillcolor='rgba(56, 189, 248, 0.1)' # Efeito de área suave
                ))
                # Linha de Visitantes
                fig_tendencia.add_trace(go.Scatter(
                    x=df_tendencia['Data'], y=df_tendencia['Vis_Celula'],
                    name="Visitantes", mode='lines+markers+text',
                    text=df_tendencia['Vis_Celula'], textposition="top center",
                    line=dict(color='#FACC15', width=3, dash='dot')
                ))
                
                fig_tendencia.update_layout(
                    template="plotly_dark", height=350,
                    margin=dict(l=10, r=10, t=30, b=10),
                    yaxis=dict(showgrid=False),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_tendencia, use_container_width=True)
