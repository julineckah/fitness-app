import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd

# --- KONFIGURÁCIA STRÁNKY ---
st.set_page_config(page_title="My Fitness AI", page_icon="🍏", layout="centered")

# --- CIELE ---
GOALS = {
    "kcal": 1950,
    "protein": 130, 
    "carbs": 200,   
    "fats": 65,     
    "fiber": 30     
}

# --- INICIALIZÁCIA DÁT (Session State) ---
# 1. Zoznam uložených jedál (Databáza)
if 'custom_foods' not in st.session_state:
    st.session_state.custom_foods = {
        "Moje štandardné raňajky": {
            "desc": "3 PL vločiek, 1 PL chia, 1 PL arašid. maslo, domáci jogurt, goji, banán, ľan, 5g kreatín, čučoriedky",
            "kcal": 480, "protein": 18, "carbs": 65, "fats": 16, "fiber": 12
        },
        "Potréningový Proteín (Srvátka)": {
            "desc": "1 odmerka srvátkového proteínu vo vode",
            "kcal": 120, "protein": 25, "carbs": 3, "fats": 1, "fiber": 0
        },
        "Večerný kváskový chlieb s vajíčkami": {
            "desc": "2 krajce kváskového chleba, 3 vajíčka, syr, fermentovaná zelenina",
            "kcal": 550, "protein": 30, "carbs": 45, "fats": 25, "fiber": 8
        }
    }

# 2. Dnešný denník jedál
if 'daily_log' not in st.session_state:
    st.session_state.daily_log = []

# --- POMOCNÉ FUNKCIE ---
def get_current_totals():
    totals = {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}
    for item in st.session_state.daily_log:
        for key in totals.keys():
            totals[key] += item[key]
    return totals

def add_to_log(meal_type, food_name, macros):
    entry = {"time": datetime.now().strftime("%H:%M"), "meal": meal_type, "name": food_name}
    entry.update(macros)
    st.session_state.daily_log.append(entry)
    st.toast(f"✅ Pridané do kategórie: {meal_type}")

# --- HLAVIČKA A SMART RADCA ---
st.title("🍏 Môj Smart Denník")
current_totals = get_current_totals()
current_hour = datetime.now().hour
missing_protein = GOALS["protein"] - current_totals["protein"]

if 15 <= current_hour <= 17 and missing_protein > 40:
    st.info(f"💡 **Tip na olovrant:** Chýba ti ešte {missing_protein}g bielkovín. Ideálny snack: 150g Skyr s odmerkou proteínu a orieškami (cca 35g bielkovín).")

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
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=40, b=10))
    return fig

# Zobrazenie grafov
st.plotly_chart(create_gauge("Kalórie (kcal)", current_totals["kcal"], GOALS["kcal"], "#3b82f6"), use_container_width=True)

c1, c2, c3, c4 = st.columns(4)
with c1: st.plotly_chart(create_gauge("Bielkoviny", current_totals["protein"], GOALS["protein"], "#ef4444"), use_container_width=True)
with c2: st.plotly_chart(create_gauge("Sacharidy", current_totals["carbs"], GOALS["carbs"], "#10b981"), use_container_width=True)
with c3: st.plotly_chart(create_gauge("Tuky", current_totals["fats"], GOALS["fats"], "#f59e0b"), use_container_width=True)
with c4: st.plotly_chart(create_gauge("Vláknina", current_totals["fiber"], GOALS["fiber"], "#8b5cf6"), use_container_width=True)

st.divider()

# --- PRIDÁVANIE JEDLA (Jadro aplikácie) ---
st.subheader("🍽️ Zapísať jedlo")

# Výber chodu
meal_category = st.radio("Vyber chod:", ["Raňajky", "Obed", "Večera", "Snack"], horizontal=True)

# Taby pre výber zdroja
tab1, tab2, tab3 = st.tabs(["📚 Z mojich jedál", "✨ AI Zápisník", "➕ Vytvoriť nové jedlo"])

with tab1:
    st.write("**Vyber si z uložených jedál:**")
    selected_food = st.selectbox("Moje jedlá:", list(st.session_state.custom_foods.keys()))
    
    if selected_food:
        food_details = st.session_state.custom_foods[selected_food]
        st.caption(f"📝 *Zloženie:* {food_details['desc']}")
        st.write(f"📊 *Hodnoty:* {food_details['kcal']} kcal | Bielkoviny: {food_details['protein']}g | Sach: {food_details['carbs']}g | Tuky: {food_details['fats']}g")
        
        if st.button("➕ Pridať do denníka", key="add_saved"):
            add_to_log(meal_category, selected_food, food_details)
            st.rerun()

with tab2:
    st.write("**Napíš, čo si jedla, a AI to rozoberie:**")
    ai_input = st.text_area("Napríklad: Na obed som mala 150g lososa s pečenými zemiakmi a brokolicou...")
    if st.button("Zanalyzovať cez AI"):
        if ai_input:
            # Tu sa neskôr napojí reálna umelá inteligencia
            mockup_macros = {"kcal": 600, "protein": 40, "carbs": 45, "fats": 20, "fiber": 7}
            add_to_log(meal_category, "AI Odhad: " + ai_input[:20] + "...", mockup_macros)
            st.success("Jedlo bolo (akože) zanalyzované a pridané!")
            st.rerun()
        else:
            st.error("Musíš niečo napísať.")

with tab3:
    st.write("**Uložiť si nové vlastné jedlo do zoznamu:**")
    with st.form("new_food_form"):
        new_name = st.text_input("Názov jedla (napr. Moja proteínová kaša)")
        new_desc = st.text_input("Zloženie (čo to obsahuje)")
        col_a, col_b = st.columns(2)
        new_k = col_a.number_input("Kalórie (kcal)", min_value=0, step=10)
        new_p = col_b.number_input("Bielkoviny (g)", min_value=0, step=1)
        new_c = col_a.number_input("Sacharidy (g)", min_value=0, step=1)
        new_f = col_b.number_input("Tuky (g)", min_value=0, step=1)
        new_fib = col_a.number_input("Vláknina (g)", min_value=0, step=1)
        
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

st.divider()

# --- HISTÓRIA A PREHĽAD DŇA ---
st.subheader("📋 Čo som dnes zjedla")

if not st.session_state.daily_log:
    st.info("Zatiaľ si dnes nič nezapísala. Dobrú chuť!")
else:
    # Zoskupenie jedál podľa chodu
    categories = ["Raňajky", "Obed", "Večera", "Snack"]
    for cat in categories:
        cat_items = [item for item in st.session_state.daily_log if item["meal"] == cat]
        if cat_items:
            st.markdown(f"**{cat}**")
            for i, item in enumerate(cat_items):
                st.markdown(f"- *{item['time']}* | {item['name']} **({item['kcal']} kcal, {item['protein']}g bielkovín)**")
    
    st.write("")
    if st.button("🗑️ Vymazať celý dnešný deň (Reset)"):
        st.session_state.daily_log = []
        st.rerun()
