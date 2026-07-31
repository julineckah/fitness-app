import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import uuid
import json

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

st.set_page_config(page_title="My Fitness AI", page_icon="🍏", layout="centered")

GOALS = {
    "kcal": 1950,
    "protein": 130,
    "carbs": 200,
    "fats": 65,
    "fiber": 30
}

if 'consumed' not in st.session_state:
    st.session_state.consumed = {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}

if 'history' not in st.session_state:
    st.session_state.history = []

if 'ai_pending' not in st.session_state:
    st.session_state.ai_pending = None

if 'ingredient_db' not in st.session_state:
    st.session_state.ingredient_db = {
        "Vločky (10g)": {"kcal": 38.0, "protein": 1.3, "carbs": 6.8, "fats": 0.7, "fiber": 1.0},
        "Banán (120g)": {"kcal": 107.0, "protein": 1.3, "carbs": 27.0, "fats": 0.4, "fiber": 3.1},
    }

if 'custom_foods' not in st.session_state:
    st.session_state.custom_foods = {
        "Moje štandardné raňajky": {
            "desc": "Základné ranné kombo",
            "ingredients": {
                "Vločky (10g)": 4.0,
                "Banán (120g)": 1.0,
            }
        }
    }

st.sidebar.title("🧠 AI Nastavenia")
st.sidebar.markdown("Aby AI fungovala, získaj bezplatný kľúč na [aistudio.google.com](https://aistudio.google.com) a vlož ho sem.")
api_key = st.sidebar.text_input("Gemini API Key:", type="password").strip()

if api_key and HAS_GENAI:
    genai.configure(api_key=api_key)
elif api_key and not HAS_GENAI:
    st.sidebar.error("⚠️ Prepojovacia knižnica chýba. Pridaj `google-generativeai` do requirements.txt.")

def call_gemini(prompt_text):
    if not api_key:
        st.error("⚠️ Najprv musíš zadať API kľúč v ľavom bočnom paneli!")
        return None
    if not HAS_GENAI:
        st.error("⚠️ Knižnica google-generativeai nie je nainštalovaná.")
        return None
        
    model = genai.GenerativeModel('gemini-1.5-flash')
    sys_prompt = """Si nutričný expert. Vypočítaj kalórie a makroživiny.
Vráť VÝHRADNE JSON formát. Žiadny text okolo, žiadne formátovanie ```json. Len čistý JSON objekt.
Štruktúra:
{
  "name": "Názov jedla/suroviny",
  "kcal": 150.0,
  "protein": 10.5,
  "carbs": 20.0,
  "fats": 5.0,
  "fiber": 2.0
}"""
    try:
        with st.spinner("🧠 AI analyzuje a počíta makrá..."):
            response = model.generate_content(sys_prompt + "\n\nZadanie: " + prompt_text)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
            
            for key in ["kcal", "protein", "carbs", "fats", "fiber"]:
                if key in data:
                    data[key] = round(float(data[key]), 1)
            return data
    except Exception as e:
        st.error(f"Nepodarilo sa spracovať odpoveď AI. Skús to preformulovať. (Detail: {e})")
        return None

def calc_macros(ingredients_dict):
    totals = {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}
    for ing, qty in ingredients_dict.items():
        if ing in st.session_state.ingredient_db:
            for key in totals:
                totals[key] += st.session_state.ingredient_db[ing][key] * qty
    for key in totals:
        totals[key] = round(totals[key], 1)
    return totals

def add_food_to_log(name, data, category):
    for k in ["kcal", "protein", "carbs", "fats", "fiber"]:
        st.session_state.consumed[k] += data[k]
    
    now = datetime.now().strftime("%H:%M")
    st.session_state.history.append({
        "id": str(uuid.uuid4()),
        "time": now,
        "name": name,
        "category": category,
        "raw_data": data.copy(),
        "macros": f"{data['kcal']} kcal | {data['protein']}g B | {data['carbs']}g S | {data['fats']}g T"
    })

def delete_food_from_log(item_id):
    for i, item in enumerate(st.session_state.history):
        if item["id"] == item_id:
            data = item["raw_data"]
            for k in ["kcal", "protein", "carbs", "fats", "fiber"]:
                st.session_state.consumed[k] = max(0, st.session_state.consumed[k] - data[k])
            del st.session_state.history[i]
            break

st.title("🍏 Môj Smart Nutričný Asistent")

current_hour = datetime.now().hour
missing_protein = GOALS["protein"] - st.session_state.consumed["protein"]

if 15 <= current_hour <= 17 and missing_protein > 40:
    st.info(f"💡 **Tip na olovrant:** Chýba ti ešte {round(missing_protein)}g bielkovín. Daj si grécky jogurt s proteínom!")

st.subheader("🍽️ Pridať jedlo")
meal_category = st.radio("Vyber chod:", ["Raňajky", "Obed", "Večera", "Snack"], horizontal=True)

tab1, tab2, tab3, tab4 = st.tabs(["📚 Moje jedlá", "✨ AI Zápisník", "➕ Nové prázdne", "⚙️ Správa a Suroviny"])

with tab1:
    st.write("**Vyber si z uložených jedál:**")
    selected_food = st.selectbox("Moje jedlá:", list(st.session_state.custom_foods.keys()))
    
    if selected_food:
        food_recipe = st.session_state.custom_foods[selected_food]
        food_data = calc_macros(food_recipe["ingredients"])
        
        st.caption(f"📝 {food_recipe['desc']}")
        ing_text = ", ".join([f"{k} ({v}x)" for k, v in food_recipe["ingredients"].items()])
        st.write(f"🥣 **Obsahuje:** {ing_text}")
        st.write(f"📊 **{food_data['kcal']} kcal** | B: **{food_data['protein']}g** | S: **{food_data['carbs']}g** | T: **{food_data['fats']}g**")
        
        if st.button(f"➕ Pridať ako {meal_category}"):
            add_food_to_log(selected_food, food_data, meal_category)
            st.success(f"{selected_food} pridané!")
            st.rerun()

with tab2:
    st.write("**Napíš celé jedlo (AI rozoberie zloženie a vypočíta makrá):**")
    ai_meal = st.text_area("Napr.: Na obed som mala 150g kuracích pŕs s ryžou a polovicou avokáda.")
    
    if st.button("✨ Zanalyzovať jedlo"):
        if ai_meal:
            ai_data = call_gemini(ai_meal)
            if ai_data:
                st.session_state.ai_pending = ai_data
            
    if st.session_state.ai_pending:
        p_data = st.session_state.ai_pending
        st.info(f"💡 **AI zistila tieto hodnoty pre '{p_data['name']}':**\n\n**{p_data['kcal']} kcal** | {p_data['protein']}g B | {p_data['carbs']}g S | {p_data['fats']}g T | {p_data['fiber']}g Vláknina")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Potvrdiť a pridať do denníka"):
                add_food_to_log(p_data["name"], p_data, meal_category)
                st.session_state.ai_pending = None
                st.success("Pridané do denníka!")
                st.rerun()
        with col_b:
            if st.button("❌ Zrušiť"):
                st.session_state.ai_pending = None
                st.rerun()

with tab3:
    st.write("**Vytvor nové prázdne jedlo (Suroviny pridáš v záložke Správa):**")
    with st.form("new_food_form"):
        new_name = st.text_input("Názov (napr. Moje palacinky)")
        new_desc = st.text_input("Popis (voliteľné)")
        
        if st.form_submit_button("💾 Vytvoriť prázdnu položku"):
            if new_name:
                st.session_state.custom_foods[new_name] = {"desc": new_desc, "ingredients": {}}
                st.success(f"{new_name} vytvorené! Preklikni sa do 'Správa a Suroviny'.")

with tab4:
    st.write("**Úprava surovín (Množstvá sa prepočítavajú naživo):**")
    edit_food = st.selectbox("Vyber jedlo na úpravu:", list(st.session_state.custom_foods.keys()))
    
    if edit_food:
        food_recipe = st.session_state.custom_foods[edit_food]
        
        if 'edit_recipe' not in st.session_state or st.session_state.get('edit_name') != edit_food:
            st.session_state.edit_recipe = food_recipe["ingredients"].copy()
            st.session_state.edit_name = edit_food
            
        st.markdown(f"#### 🥣 Suroviny pre: {edit_food}")
        
        for ing, qty in list(st.session_state.edit_recipe.items()):
            ec1, ec2, ec3 = st.columns([3, 1, 1])
            with ec1:
                st.markdown(f"**{ing}**")
            with ec2:
                def update_qty(ingredient_name=ing):
                    val = st.session_state[f"num_{ingredient_name}"]
                    if val <= 0:
                        del st.session_state.edit_recipe[ingredient_name]
                    else:
                        st.session_state.edit_recipe[ingredient_name] = val

                st.number_input("Množstvo", value=float(qty), min_value=0.0, step=0.5, key=f"num_{ing}", on_change=update_qty, label_visibility="collapsed")
            with ec3:
                if st.button("🗑️", key=f"del_{ing}"):
                    del st.session_state.edit_recipe[ing]
                    st.rerun()
        
        st.markdown("---")
        st.write("**➕ Pridať surovinu do tohto receptu:**")
        add_col1, add_col2 = st.columns([3, 1])
        with add_col1:
            new_ing = st.selectbox("Z mojej databázy:", ["-- Vyber --"] + list(st.session_state.ingredient_db.keys()), label_visibility="collapsed")
        with add_col2:
            if st.button("Pridať", key="add_known_ing"):
                if new_ing != "-- Vyber --" and new_ing not in st.session_state.edit_recipe:
                    st.session_state.edit_recipe[new_ing] = 1.0
                    st.rerun()
        
        st.write("**🤖 Alebo objav úplne novú surovinu cez AI:**")
        ai_ing = st.text_input("Napr. '1 odmerka hrachového proteínu' alebo '150g Tofu'")
        if st.button("✨ Zistiť živiny a pridať do databázy"):
            if ai_ing:
                ai_data = call_gemini(ai_ing)
                if ai_data:
                    new_name = ai_data["name"]
                    st.session_state.ingredient_db[new_name] = {
                        "kcal": ai_data["kcal"], "protein": ai_data["protein"], 
                        "carbs": ai_data["carbs"], "fats": ai_data["fats"], "fiber": ai_data["fiber"]
                    }
                    st.session_state.edit_recipe[new_name] = 1.0
                    st.success(f"{new_name} pridané do tvojej databázy aj do receptu!")
                    st.rerun()

        live_macros = calc_macros(st.session_state.edit_recipe)
        st.markdown("### 🧠 Smart Analýza")
        
        total_cal = live_macros['kcal']
        st.write(f"📊 Live výpočet: **{total_cal} kcal** | B: **{live_macros['protein']}g** | S: **{live_macros['carbs']}g** | T: **{live_macros['fats']}g**")
        
        if total_cal > 0:
            p_pct = (live_macros['protein'] * 4 / total_cal) * 100
            if p_pct < 20:
                st.warning("💡 **Tip:** Toto jedlo má málo bielkovín. Pridaj v políčkach vyššie surovinu bohatú na bielkoviny (napr. proteín).")
            else:
                st.success("✅ Krásne vyvážené jedlo!")
        
        if st.button("💾 ULOŽIŤ UPRAVENÝ RECEPT", type="primary"):
            st.session_state.custom_foods[edit_food]["ingredients"] = st.session_state.edit_recipe.copy()
            st.success("Tento recept bol prepísaný a navždy uložený!")

st.divider()

st.subheader("📊 Dnešný progres")
current_totals = st.session_state.consumed

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
            'bordercolor': "gray",
        }
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=70, b=20))
    return fig

st.plotly_chart(create_gauge("Kalórie (kcal)", current_totals["kcal"], GOALS["kcal"], "#3b82f6"), use_container_width=True)

c1, c2, c3, c4 = st.columns(4)
with c1: st.plotly_chart(create_gauge("Bielkoviny (g)", current_totals["protein"], GOALS["protein"], "#ef4444"), use_container_width=True)
with c2: st.plotly_chart(create_gauge("Sacharidy (g)", current_totals["carbs"], GOALS["carbs"], "#10b981"), use_container_width=True)
with c3: st.plotly_chart(create_gauge("Tuky (g)", current_totals["fats"], GOALS["fats"], "#f59e0b"), use_container_width=True)
with c4: st.plotly_chart(create_gauge("Vláknina (g)", current_totals["fiber"], GOALS["fiber"], "#8b5cf6"), use_container_width=True)

st.divider()
st.subheader("🕒 Čo som dnes zjedla")

if not st.session_state.history:
    st.write("*Zatiaľ si dnes nič nepridala.*")
else:
    for cat in ["Raňajky", "Obed", "Večera", "Snack"]:
        cat_items = [item for item in st.session_state.history if item["category"] == cat]
        if cat_items:
            st.markdown(f"**{cat}**")
            for item in cat_items:
                hc1, hc2 = st.columns([5, 1])
                with hc1:
                    st.write(f"• {item['time']} - {item['name']} ({item['macros']})")
                with hc2:
                    if st.button("🗑️", key=f"del_hist_{item['id']}"):
                        delete_food_from_log(item['id'])
                        st.rerun()

st.divider()
if st.button("🔄 Resetovať deň (O polnoci)"):
    st.session_state.consumed = {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}
    st.session_state.history = []
    st.rerun()
