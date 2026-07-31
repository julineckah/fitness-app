# ... existing code ...
# --- VIZUALIZÁCIA (Budíky na ploche) ---
def create_gauge(title, current, goal, color):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = current,
        title = {'text': title, 'font': {'size': 16}},
        gauge = {
            'axis': {'range': [None, goal], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e2e8f0",
        }
    ))
    # ZMENA: Zväčšili sme height na 230 a horný okraj (t) na 70, aby sa nadpis neorezal
    fig.update_layout(height=230, margin=dict(l=10, r=10, t=70, b=10))
    return fig

# Zobrazenie grafov
st.plotly_chart(create_gauge("Kalórie (kcal)", current_totals["kcal"], GOALS["kcal"], "#3b82f6"), use_container_width=True)
# ... existing code ...
```

### 2. Pridanie 4. Tabu so Smart Analýzou a úpravou jedál
Zmeníme definíciu tabov a na koniec tabu 3 prilepíme úplne novú sekciu pre tab 4.

```python:Zdrojový kód Streamlit aplikácie:app.py
# ... existing code ...
# Výber chodu
meal_category = st.radio("Vyber chod:", ["Raňajky", "Obed", "Večera", "Snack"], horizontal=True)

# Taby pre výber zdroja - Pridaný 4. Tab
tab1, tab2, tab3, tab4 = st.tabs(["📚 Z mojich jedál", "✨ AI Zápisník", "➕ Vytvoriť nové jedlo", "⚙️ Správa jedál"])

with tab1:
    st.write("**Vyber si z uložených jedál:**")
# ... existing code ...
        if st.form_submit_button("💾 Uložiť do mojej databázy"):
            if new_name:
                st.session_state.custom_foods[new_name] = {
                    "desc": new_desc, "kcal": new_k, "protein": new_p, 
                    "carbs": new_c, "fats": new_f, "fiber": new_fib
                }
                st.success(f"{new_name} pridané do tvojho zoznamu!")
                st.rerun()
            else:
                st.error("Jedlo musí mať názov.")

with tab4:
    st.write("**Úprava uložených jedál a Smart Analýza:**")
    edit_food = st.selectbox("Vyber jedlo, ktoré chceš upraviť:", list(st.session_state.custom_foods.keys()))
    
    if edit_food:
        food_data = st.session_state.custom_foods[edit_food]
        
        # --- SMART ANALYZÁTOR JEDLA ---
        st.markdown("### 🧠 Smart Analýza tohto jedla")
        total_cal = food_data['kcal']
        p_cal = food_data['protein'] * 4 # 1g bielkovín = 4 kcal
        
        if total_cal > 0:
            p_pct = (p_cal / total_cal) * 100
            if p_pct < 20:
                st.warning(f"💡 **Tip na vylepšenie:** Toto jedlo má málo bielkovín (len {p_pct:.0f}% z kalórií). Pre lepšiu svalovú odozvu z gymu uber sacharidy (napr. o lyžicu vločiek menej) a pridaj bielkoviny (cottage, vajíčko, proteín), aby si dosiahla aspoň 25-30g bielkovín v porcii.")
            elif p_pct > 35:
                st.success("💪 **Super!** Toto jedlo je vynikajúci zdroj bielkovín, ideálne po tréningu.")
            else:
                st.success("✅ Pekne vyvážené jedlo!")
                
            if food_data['fiber'] < 5 and total_cal > 200:
                st.info("🥦 **Vláknina:** Hodilo by sa sem pridať trochu chia semienok, ľanu alebo zeleniny pre lepší mikrobióm.")
        
        st.markdown("---")
        st.write("*Zmeň hodnoty nižšie. Po uložení sa ihneď prepočíta analýza.*")
        
        # --- EDITOR JEDLA ---
        with st.form("edit_food_form"):
            e_desc = st.text_input("Zloženie (čo to obsahuje)", value=food_data['desc'])
            ec1, ec2 = st.columns(2)
            e_k = ec1.number_input("Kalórie (kcal)", min_value=0, step=10, value=int(food_data['kcal']))
            e_p = ec2.number_input("Bielkoviny (g)", min_value=0, step=1, value=int(food_data['protein']))
            e_c = ec1.number_input("Sacharidy (g)", min_value=0, step=1, value=int(food_data['carbs']))
            e_f = ec2.number_input("Tuky (g)", min_value=0, step=1, value=int(food_data['fats']))
            e_fib = ec1.number_input("Vláknina (g)", min_value=0, step=1, value=int(food_data['fiber']))
            
            if st.form_submit_button("💾 Uložiť zmeny v jedle"):
                st.session_state.custom_foods[edit_food] = {
                    "desc": e_desc, "kcal": e_k, "protein": e_p, 
                    "carbs": e_c, "fats": e_f, "fiber": e_fib
                }
                st.success("Jedlo bolo upravené!")
                st.rerun()

st.divider()

# --- HISTÓRIA A PREHĽAD DŇA ---
# ... existing code ...
