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

if 'history' not in st.session_state:
    st.session_state.history = [] # Tu budeme ukladať históriu jedál

if 'custom_foods' not in st.session_state:
    # Predvyplnená databáza tvojich jedál
    st.session_state.custom_foods = {
        "Moje štandardné raňajky (Vločky, jogurt, chia, banán...)": {
            "desc": "3 lyžice vločiek, 1 lyž. chia, domáci jogurt, 1 banán, arašidové maslo, ľan, goji, proteín/kreatín",
            "kcal": 480, "protein": 18, "carbs": 65, "fats": 16, "fiber": 12
        },
        "Potréningový Proteín (Snack)": {
            "desc": "1 odmerka srvátkového proteínu s vodou",
            "kcal": 120, "protein": 25, "carbs": 3, "fats": 1, "fiber": 0
        },
        "Kváskový chlieb s vajíčkami (Večera)": {
            "desc": "2 krajce kváskového chleba, 2 vajíčka, kúsok syra, fermentovaná zelenina",
            "kcal": 450, "protein": 22, "carbs": 40, "fats": 20, "fiber": 8
        }
    }

def add_food_to_log(name, data, category):
    # Pridá hodnoty do celkových denných súčtov
    st.session_state.consumed["kcal"] += data["kcal"]
    st.session_state.consumed["protein"] += data["protein"]
    st.session_state.consumed["carbs"] += data["carbs"]
    st.session_state.consumed["fats"] += data["fats"]
    st.session_state.consumed["fiber"] += data["fiber"]
    
    # Zapíše jedlo do histórie
    now = datetime.now().strftime("%H:%M")
    st.session_state.history.append({
        "time": now,
        "name": name,
        "category": category,
        "macros": f"{data['kcal']} kcal | {data['protein']}g B | {data['carbs']}g S | {data['fats']}g T"
    })

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
    # OPRAVA OREZANIA: Zväčšený height a horný okraj (t) na 70
    fig.update_layout(height=230, margin=dict(l=10, r=10, t=70, b=10))
    return fig

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

st.divider()

# --- ZADÁVANIE JEDLA ---
st.subheader("🍽️ Pridať jedlo")

# Výber chodu (dôležité pre históriu)
meal_category = st.radio("Vyber chod:", ["Raňajky", "Obed", "Večera", "Snack"], horizontal=True)

# Taby pre výber zdroja
tab1, tab2, tab3, tab4 = st.tabs(["📚 Z mojich jedál", "✨ AI Zápisník", "➕ Vytvoriť nové", "⚙️ Správa a Analýza"])

with tab1:
    st.write("**Vyber si z uložených jedál:**")
    selected_food = st.selectbox("Moje jedlá:", list(st.session_state.custom_foods.keys()))
    
    if selected_food:
        food_data = st.session_state.custom_foods[selected_food]
        st.caption(f"📝 Zloženie: {food_data['desc']}")
        st.write(f"📊 **{food_data['kcal']} kcal** | Bielkoviny: **{food_data['protein']}g** | Sacharidy: **{food_data['carbs']}g** | Tuky: **{food_data['fats']}g** | Vláknina: **{food_data['fiber']}g**")
        
        if st.button(f"➕ Pridať ako {meal_category}"):
            add_food_to_log(selected_food, food_data, meal_category)
            st.success(f"{selected_food} pridané!")
            st.rerun()

with tab2:
    st.write("**Napíš, čo si mala (AI to prepočíta):**")
    ai_input = st.text_input("Napr.: Na obed som mala kuracie prsia s ryžou...")
    if st.button("✨ Zanalyzovať cez AI"):
        if ai_input:
            # Mockup AI - sem neskôr napojíme reálne API
            mock_data = {"kcal": 550, "protein": 45, "carbs": 50, "fats": 15, "fiber": 5}
            add_food_to_log(f"AI: {ai_input[:20]}...", mock_data, meal_category)
            st.success("Analyzované a pridané do denníka!")
            st.rerun()
        else:
            st.error("Najprv napíš jedlo do poľa vyššie.")

with tab3:
    st.write("**Pridaj vlastné jedlo do svojej databázy:**")
    with st.form("new_food_form"):
        new_name = st.text_input("Názov jedla (napr. Moje palacinky)")
        new_desc = st.text_input("Zloženie (čo to obsahuje)")
        c1, c2 = st.columns(2)
        new_k = c1.number_input("Kalórie (kcal)", min_value=0, step=10)
        new_p = c2.number_input("Bielkoviny (g)", min_value=0, step=1)
        new_c = c1.number_input("Sacharidy (g)", min_value=0, step=1)
        new_f = c2.number_input("Tuky (g)", min_value=0, step=1)
        new_fib = c1.number_input("Vláknina (g)", min_value=0, step=1)
        
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
    edit_food = st.selectbox("Vyber jedlo, ktoré chceš upraviť (alebo otestovať jeho pomery):", list(st.session_state.custom_foods.keys()))
    
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
        st.write("*Zmeň hodnoty nižšie. Po uložení sa ihneď prepočíta analýza. Môžeš si tak ladiť svoje porcie.*")
        
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

# --- DNEŠNÝ PROGRES A GRAFY ---
st.subheader("📊 Dnešný progres")

current_totals = st.session_state.consumed

st.plotly_chart(create_gauge("Kalórie (kcal)", current_totals["kcal"], GOALS["kcal"], "#3b82f6"), use_container_width=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.plotly_chart(create_gauge("Bielkoviny (g)", current_totals["protein"], GOALS["protein"], "#ef4444"), use_container_width=True)
with c2:
    st.plotly_chart(create_gauge("Sacharidy (g)", current_totals["carbs"], GOALS["carbs"], "#10b981"), use_container_width=True)
with c3:
    st.plotly_chart(create_gauge("Tuky (g)", current_totals["fats"], GOALS["fats"], "#f59e0b"), use_container_width=True)
with c4:
    st.plotly_chart(create_gauge("Vláknina (g)", current_totals["fiber"], GOALS["fiber"], "#8b5cf6"), use_container_width=True)


# --- HISTÓRIA A PREHĽAD DŇA ---
st.divider()
st.subheader("🕒 Čo som dnes zjedla")

if not st.session_state.history:
    st.write("*Zatiaľ si dnes nič nepridala.*")
else:
    # Zoskupenie histórie podľa chodov
    categories = ["Raňajky", "Obed", "Večera", "Snack"]
    for cat in categories:
        cat_items = [item for item in st.session_state.history if item["category"] == cat]
        if cat_items:
            st.markdown(f"**{cat}**")
            for item in cat_items:
                st.write(f"• {item['time']} - {item['name']} ({item['macros']})")

st.divider()
if st.button("🔄 Resetovať deň (O polnoci)"):
    st.session_state.consumed = {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}
    st.session_state.history = []
    st.rerun()
