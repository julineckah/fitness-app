import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

# --- KONFIGURÁCIA STRÁNKY ---
st.set_page_config(page_title="My Fitness AI", page_icon="🍏", layout="centered")

# --- CIELE (Základné nastavenie na mieru pre teba) ---
GOALS = {
    "kcal": 1950,
    "protein": 130, # gramy (zvýšené kvôli silovému tréningu)
    "carbs": 200,   # gramy
    "fats": 65,     # gramy
    "fiber": 30     # gramy (pre zdravý mikrobióm)
}

# --- INICIALIZÁCIA DÁT (Session State) ---
if 'consumed' not in st.session_state:
    st.session_state.consumed = {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}

def add_macros(kcal, p, c, f, fib):
    st.session_state.consumed["kcal"] += kcal
    st.session_state.consumed["protein"] += p
    st.session_state.consumed["carbs"] += c
    st.session_state.consumed["fats"] += f
    st.session_state.consumed["fiber"] += fib

# --- HLAVIČKA A SMART RADCA ---
st.title("🍏 Môj Smart Nutričný Asistent")

current_hour = datetime.now().hour
missing_protein = GOALS["protein"] - st.session_state.consumed["protein"]

if 15 <= current_hour <= 17 and missing_protein > 40:
    st.info(f"💡 **Tip na olovrant:** Chýba ti ešte {missing_protein}g bielkovín. Čo tak dať si grécky jogurt / Skyr s trochou orieškov a odmerkou proteínu? Dodá ti to cca 35g bielkovín!")
elif current_hour >= 19 and st.session_state.consumed["kcal"] < 1000:
    st.warning("⚠️ Dnes si toho zjedla veľmi málo! Nezabudni, že pre rast svalov a regeneráciu po gyme potrebuješ palivo.")
else:
    st.success("✅ Všetko ide podľa plánu, pokračuj v skvelej práci!")

# --- ZADÁVANIE JEDLA ---
st.subheader("🍽️ Pridať jedlo")

# 1. Rýchle voľby (Presets)
st.write("**Moje obľúbené jedlá:**")
col1, col2 = st.columns(2)
with col1:
    if st.button("🥣 Moje štandardné raňajky"):
        # Odhadované hodnoty: Vločky, chia, jogurt, banán, arašidové maslo, atď.
        add_macros(kcal=480, p=18, c=65, f=16, fib=12)
        st.toast("Raňajky pridané!")
with col2:
    if st.button("🥤 Potréningový Proteín"):
        add_macros(kcal=120, p=25, c=3, f=1, fib=0)
        st.toast("Proteín pridaný!")

# 2. AI Zápisník
st.write("**Alebo napíš, čo si mala (AI to prepočíta):**")
ai_input = st.text_input("Napr.: Na obed som mala kuracie prsia s ryžou a šalátom...")
if st.button("✨ Zanalyzovať cez AI"):
    if ai_input:
        # TU PRÍDE REÁLNE PREPOJENIE NA AI (Gemini/OpenAI)
        # Zatiaľ je tu len ukážková "mockup" logika na ukážku
        st.success(f"AI zanalyzovala: '{ai_input}' (Mockup hodnoty pridané)")
        add_macros(kcal=550, p=45, c=50, f=15, fib=5) # Ukážkové hodnoty
    else:
        st.error("Najprv napíš jedlo do poľa vyššie.")

# --- VIZUALIZÁCIA (Budíky na ploche) ---
st.subheader("📊 Dnešný progres")

def create_gauge(title, current, goal, color):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = current,
        title = {'text': title, 'font': {'size': 18}},
        gauge = {
            'axis': {'range': [None, goal], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    return fig

# Kalórie na celú šírku
st.plotly_chart(create_gauge("Kalórie (kcal)", st.session_state.consumed["kcal"], GOALS["kcal"], "#3b82f6"), use_container_width=True)

# Makrá rozdelené do 4 stĺpcov
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.plotly_chart(create_gauge("Bielkoviny (g)", st.session_state.consumed["protein"], GOALS["protein"], "#ef4444"), use_container_width=True)
with c2:
    st.plotly_chart(create_gauge("Sacharidy (g)", st.session_state.consumed["carbs"], GOALS["carbs"], "#10b981"), use_container_width=True)
with c3:
    st.plotly_chart(create_gauge("Tuky (g)", st.session_state.consumed["fats"], GOALS["fats"], "#f59e0b"), use_container_width=True)
with c4:
    st.plotly_chart(create_gauge("Vláknina (g)", st.session_state.consumed["fiber"], GOALS["fiber"], "#8b5cf6"), use_container_width=True)

# Tlačidlo na reset dňa
st.divider()
if st.button("🔄 Resetovať deň (O polnoci)"):
    st.session_state.consumed = {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}
    st.rerun()
