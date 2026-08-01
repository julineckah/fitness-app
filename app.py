import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import google.generativeai as genai
import json
import os
import time

st.set_page_config(page_title="My Fitness AI", page_icon="🍏", layout="centered")

DB_FILE = "databaza.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "consumed": {"kcal": 0, "protein": 0.0, "carbs": 0.0, "fats": 0.0, "fiber": 0.0},
        "history": [],
        "custom_foods": {
            "Moje štandardné raňajky": {
                "desc": "Vločky, chia, jogurt, banán...",
                "ingredients": {"Vločky (1g)": 40.0, "Banán (1g)": 120.0, "Grécky jogurt (1g)": 150.0}
            }
        },
        "ingredient_db": {
            "Vločky (1g)": {"kcal": 3.5, "protein": 0.14, "carbs": 0.6, "fats": 0.07, "fiber": 0.1},
            "Banán (1g)": {"kcal": 0.9, "protein": 0.01, "carbs": 0.23, "fats": 0.0, "fiber": 0.03},
            "Grécky jogurt (1g)": {"kcal": 0.57, "protein": 0.1, "carbs": 0.04, "fats": 0.0, "fiber": 0.0}
        }
    }

def save_db():
    data_to_save = {
        "consumed": st.session_state.consumed,
        "history": st.session_state.history,
        "custom_foods": st.session_state.custom_foods,
        "ingredient_db": st.session_state.ingredient_db
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)

db_data = load_db()
if 'consumed' not in st.session_state: st.session_state.consumed = db_data["consumed"]
if 'history' not in st.session_state: st.session_state.history = db_data.get("history", [])
if 'custom_foods' not in st.session_state: st.session_state.custom_foods = db_data["custom_foods"]
if 'ingredient_db' not in st.session_state: st.session_state.ingredient_db = db_data["ingredient_db"]
if 'edit_recipe' not in st.session_state: st.session_state.edit_recipe = {}
if 'show_save_success' not in st.session_state: st.session_state.show_save_success = False

GOALS = {"kcal": 1950, "protein": 130, "carbs": 200, "fats": 65, "fiber": 30}

def add_macros(kcal, p, c, f, fib, name, meal_type):
    st.session_state.consumed["kcal"] += kcal
    st.session_state.consumed["protein"] += p
    st.session_state.consumed["carbs"] += c
    st.session_state.consumed["fats"] += f
    st.session_state.consumed["fiber"] += fib
    st.session_state.history.append({
        "id": str(time.time()), "name": name, "type": meal_type,
        "kcal": kcal, "p": p, "c": c, "f": f, "fib": fib,
        "time": datetime.now().strftime("%H:%M")
    })
    save_db()

def calc_macros(recipe_ingredients):
    total = {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}
    for ing_name, amount in recipe_ingredients.items():
        if ing_name in st.session_state.ingredient_db:
            data = st.session_state.ingredient_db[ing_name]
            total["kcal"] += data["kcal"] * amount
            total["protein"] += data["protein"] * amount
            total["carbs"] += data["carbs"] * amount
            total["fats"] += data["fats"] * amount
            total["fiber"] += data["fiber"] * amount
    return total

def get_gemini_model():
    api_key = st.session_state.get("gemini_key", "").strip()
    if not api_key: return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-3.5-flash')

def analyze_meal_to_recipe(meal_desc):
    prompt = f"""
    Zanalyzuj toto jedlo: "{meal_desc}". 
    Rozdeľ ho na jednotlivé suroviny. Pre každú surovinu odhadni kalórie (kcal) a makroživiny v gramoch (protein, carbs, fats, fiber) pre to konkrétne odhadované množstvo v porcii.
    Vráť PRÍSNY JSON vo formáte:
    {{
        "ingredients": [
            {{
                "name": "Názov suroviny (množstvo)",
                "kcal": 150.5,
                "protein": 20.0,
                "carbs": 5.0,
                "fats": 5.0,
                "fiber": 1.0
            }}
        ]
    }}
    """
    model = get_gemini_model()
    if not model: return None
    try:
        response = model.generate_content(prompt)
        txt = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(txt)
    except Exception as e:
        if "429" in str(e):
            st.warning("⏳ Googlu sa zdá, že ideme prirýchlo. Dávam si 35 sekúnd pauzu a skúsim to znova, počkaj...")
            time.sleep(35)
            try:
                response = model.generate_content(prompt)
                txt = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(txt)
            except:
                return None
        return None

def call_gemini(query):
    prompt = f"""
    Zisti presné nutričné hodnoty pre túto surovinu/jedlo: "{query}".
    Vráť IBA čistý JSON formát s kľúčmi: name, kcal, protein, carbs, fats, fiber. Hodnoty nech sú čísla (float/int). Žiadny iný text.
    Príklad: {{"name": "100g Tofu", "kcal": 76.0, "protein": 8.0, "carbs": 1.9, "fats": 4.8, "fiber": 0.3}}
    """
    model = get_gemini_model()
    if not model: return None
    try:
        response = model.generate_content(prompt)
        txt = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(txt)
    except Exception as e:
        if "429" in str(e):
            st.warning("⏳ Mám pauzu od Googlu kvôli limitom (429). Počkám 35 sekúnd a doplním to automaticky.")
            time.sleep(35)
            try:
                response = model.generate_content(prompt)
                txt = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(txt)
            except:
                return None
        return None

with st.sidebar:
    st.header("🧠 AI Nastavenia")
    st.write("Aby AI fungovala, získaj bezplatný kľúč na [aistudio.google.com](https://aistudio.google.com) a vlož ho sem.")
    gemini_key = st.text_input("Gemini API Key:", type="password", key="gemini_key")
    st.divider()
    st.caption("Tvoje dáta sa ukladajú lokálne a bezpečne.")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dnešný prehľad", "✨ AI Zápisník", "➕ Nové jedlo", "⚙️ Správa a Suroviny"])

with tab1:
    st.subheader("🍽️ Záznamník z mojich jedál")
    
    colA, colB, colC = st.columns([2, 1, 1])
    with colA:
        selected_food = st.selectbox("Vyber si hotové jedlo:", ["(Nevybraté)"] + list(st.session_state.custom_foods.keys()))
    with colB:
        meal_type = st.selectbox("Druh:", ["Raňajky", "Obed", "Večera", "Snack"])
    
    if selected_food != "(Nevybraté)":
        food_data = st.session_state.custom_foods[selected_food]
        macros = calc_macros(food_data["ingredients"])
        st.info(f"**Zloženie:** {food_data['desc']}")
        st.write(f"📊 **Hodnoty porcie:** {round(macros['kcal'],1)} kcal | B: {round(macros['protein'],1)}g | S: {round(macros['carbs'],1)}g | T: {round(macros['fats'],1)}g")
        
        with colC:
            st.write("") 
            st.write("") 
            if st.button("➕ Zjesť", type="primary", use_container_width=True):
                add_macros(macros['kcal'], macros['protein'], macros['carbs'], macros['fats'], macros['fiber'], selected_food, meal_type)
                st.success(f"{selected_food} pridané ako {meal_type}!")
                time.sleep(1)
                st.rerun()

    st.subheader("📊 Denné ciele")
    def create_gauge(title, current, goal, color):
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = current,
            title = {'text': title, 'font': {'size': 16}},
            gauge = {
                'axis': {'range': [None, goal], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': color},
                'bgcolor': "white", 'borderwidth': 2, 'bordercolor': "gray",
            }
        ))
        fig.update_layout(height=200, margin=dict(l=10, r=10, t=50, b=10))
        return fig

    st.plotly_chart(create_gauge("Kalórie (kcal)", st.session_state.consumed["kcal"], GOALS["kcal"], "#3b82f6"), use_container_width=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.plotly_chart(create_gauge("Bielkoviny", st.session_state.consumed["protein"], GOALS["protein"], "#ef4444"), use_container_width=True)
    with c2: st.plotly_chart(create_gauge("Sacharidy", st.session_state.consumed["carbs"], GOALS["carbs"], "#10b981"), use_container_width=True)
    with c3: st.plotly_chart(create_gauge("Tuky", st.session_state.consumed["fats"], GOALS["fats"], "#f59e0b"), use_container_width=True)
    with c4: st.plotly_chart(create_gauge("Vláknina", st.session_state.consumed["fiber"], GOALS["fiber"], "#8b5cf6"), use_container_width=True)

    st.subheader("📝 Čo som dnes zjedla")
    if not st.session_state.history:
        st.write("Zatiaľ si dnes nič nepridala.")
    else:
        for meal in ["Raňajky", "Obed", "Večera", "Snack"]:
            meals_in_cat = [m for m in st.session_state.history if m["type"] == meal]
            if meals_in_cat:
                st.markdown(f"**{meal}**")
                for m in meals_in_cat:
                    col1, col2, col3 = st.columns([1, 4, 1])
                    with col1: st.caption(m["time"])
                    with col2: st.write(f"**{m['name']}** ({round(m['kcal'])} kcal)")
                    with col3:
                        if st.button("🗑️", key=m["id"]):
                            st.session_state.consumed["kcal"] -= m["kcal"]
                            st.session_state.consumed["protein"] -= m["p"]
                            st.session_state.consumed["carbs"] -= m["c"]
                            st.session_state.consumed["fats"] -= m["f"]
                            st.session_state.consumed["fiber"] -= m["fib"]
                            st.session_state.history = [x for x in st.session_state.history if x["id"] != m["id"]]
                            save_db()
                            st.rerun()
                st.divider()

with tab2:
    st.subheader("✨ AI Zápisník")
    st.write("Jedla si niečo mimo receptov? AI to rozoberie na suroviny. Ak ti to bude chutiť, môžeš si to trvalo uložiť!")
    ai_meal = st.text_input("Napr.: '150g losos s hrstou ryže a šalátom'")
    
    if st.button("✨ Zanalyzovať jedlo"):
        if ai_meal:
            if not st.session_state.get("gemini_key"):
                st.error("Najprv vlož API kľúč v bočnom paneli vľavo!")
            else:
                with st.spinner("AI analyzuje tvoje jedlo a suroviny..."):
                    res = analyze_meal_to_recipe(ai_meal)
                    if res and "ingredients" in res:
                        st.session_state.ai_last_meal = res
                        st.session_state.ai_last_meal_name = ai_meal
                    else:
                        st.error("Chyba AI. Skús to preformulovať.")
    
    if st.session_state.get("ai_last_meal"):
        res = st.session_state.ai_last_meal
        st.write("### 🥗 Výsledok analýzy:")
        total_kcal = total_p = total_c = total_f = total_fib = 0
        
        for item in res["ingredients"]:
            st.write(f"- **{item['name']}**: {item['kcal']} kcal (B: {item['protein']}g | S: {item['carbs']}g | T: {item['fats']}g)")
            total_kcal += item['kcal']
            total_p += item['protein']
            total_c += item['carbs']
            total_f += item['fats']
            total_fib += item['fiber']
            
        st.info(f"**Spolu:** {round(total_kcal,1)} kcal | B: {round(total_p,1)}g | S: {round(total_c,1)}g | T: {round(total_f,1)}g")
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Možnosť A: Len zjesť**")
            meal_type_ai = st.selectbox("Ako aký chod?", ["Obed", "Raňajky", "Večera", "Snack"], key="ai_type")
            if st.button("🍽️ Pridať do dnešného denníka"):
                add_macros(total_kcal, total_p, total_c, total_f, total_fib, st.session_state.ai_last_meal_name, meal_type_ai)
                del st.session_state["ai_last_meal"]
                st.success("Pridané!")
                time.sleep(1.5)
                st.rerun()
        with col2:
            st.write("**Možnosť B: Uložiť navždy (ako recept)**")
            new_recipe_name = st.text_input("Názov pre uloženie (napr. Môj top losos):")
            if st.button("💾 Uložiť do Moje jedlá"):
                if new_recipe_name:
                    new_ingredients = {}
                    for item in res["ingredients"]:
                        ing_name = item["name"]
                        st.session_state.ingredient_db[ing_name] = {
                            "kcal": item["kcal"], "protein": item["protein"],
                            "carbs": item["carbs"], "fats": item["fats"], "fiber": item["fiber"]
                        }
                        new_ingredients[ing_name] = 1.0 # 1 porcia
                    
                    st.session_state.custom_foods[new_recipe_name] = {
                        "desc": st.session_state.ai_last_meal_name,
                        "ingredients": new_ingredients
                    }
                    save_db()
                    del st.session_state["ai_last_meal"]
                    st.success(f"Recept uložený! Nájdeš ho v Správe jedál.")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.warning("Zadaj názov.")

with tab3:
    st.subheader("➕ Vytvoriť nové jedlo s pomocou AI")
    st.write("Popíš zloženie svojho nového jedla. AI ho automaticky rozbije na suroviny, priradí im hodnoty a jedlo uloží do tvojej databázy.")
    
    new_name = st.text_input("Názov jedla (napr. 'Kuracie rizoto'):")
    new_desc = st.text_area("Popis zloženia (napr. '100g kuracie prsia, 50g surová ryža, 1 lyžica olivového oleja').")
    
    if st.button("✨ Vygenerovať a Uložiť jedlo"):
        if new_name:
            if new_desc.strip():
                if not st.session_state.get("gemini_key"):
                    st.error("Najprv vlož API kľúč v bočnom paneli vľavo!")
                else:
                    with st.spinner("AI vytvára tvoj recept a analyzuje suroviny..."):
                        res = analyze_meal_to_recipe(new_desc)
                        if res and "ingredients" in res:
                            new_ingredients = {}
                            for item in res["ingredients"]:
                                ing_name = item["name"]
                                st.session_state.ingredient_db[ing_name] = {
                                    "kcal": item["kcal"], "protein": item["protein"],
                                    "carbs": item["carbs"], "fats": item["fats"], "fiber": item["fiber"]
                                }
                                new_ingredients[ing_name] = 1.0
                            
                            st.session_state.custom_foods[new_name] = {
                                "desc": new_desc,
                                "ingredients": new_ingredients
                            }
                            save_db()
                            st.success(f"Jedlo '{new_name}' bolo kompletne zanalyzované a uložené! Nájdeš ho v Správe a Suroviny.")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Nepodarilo sa zanalyzovať. Skús preformulovať.")
            else:
                st.session_state.custom_foods[new_name] = {"desc": "Bez popisu", "ingredients": {}}
                save_db()
                st.success("Prázdne jedlo vytvorené! Prejdi do Správy a vlož suroviny ručne.")
                time.sleep(1.5)
                st.rerun()
        else:
            st.warning("Musíš zadať aspoň názov jedla.")

with tab4:
    st.subheader("⚙️ Moje recepty a Suroviny")
    
    edit_food = st.selectbox("Vyber jedlo na úpravu:", list(st.session_state.custom_foods.keys()))
    
    if edit_food:
        if "current_edit_food" not in st.session_state or st.session_state.current_edit_food != edit_food:
            st.session_state.edit_recipe = st.session_state.custom_foods[edit_food]["ingredients"].copy()
            st.session_state.current_edit_food = edit_food
            st.session_state.show_save_success = False

        st.write(f"### 🥣 Suroviny pre: {edit_food}")
        
        updated_recipe = {}
        for ing, amount in list(st.session_state.edit_recipe.items()):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{ing}**")
            with col2:
                new_amount = st.number_input("Množstvo", min_value=0.0, value=float(amount), step=1.0, key=f"amt_{ing}")
                updated_recipe[ing] = new_amount
            with col3:
                st.write("")
                if st.button("🗑️", key=f"del_{ing}"):
                    del st.session_state.edit_recipe[ing]
                    st.rerun()
        
        st.session_state.edit_recipe = updated_recipe

        st.divider()
        st.write("**🤖 Alebo objav úplne novú surovinu cez AI:**")
        ai_ing = st.text_input("Napr. '1 odmerka hrachového proteínu' alebo '150g Tofu'")
        if st.button("✨ Zistiť živiny a pridať do receptu"):
            if ai_ing:
                if not st.session_state.get("gemini_key"):
                    st.error("Najprv vlož API kľúč!")
                else:
                    with st.spinner(f"Zisťujem hodnoty pre: {ai_ing}..."):
                        ai_data = call_gemini(ai_ing)
                        if ai_data:
                            new_name = ai_data["name"]
                            st.session_state.ingredient_db[new_name] = {
                                "kcal": ai_data["kcal"], "protein": ai_data["protein"], 
                                "carbs": ai_data["carbs"], "fats": ai_data["fats"], "fiber": ai_data["fiber"]
                            }
                            st.session_state.edit_recipe[new_name] = 1.0
                            save_db()
                            st.success(f"Surovina {new_name} pridaná!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Nepodarilo sa nájsť. Skús preformulovať.")
        
        st.divider()
        live_macros = calc_macros(st.session_state.edit_recipe)
        st.write("### 🧠 Smart Analýza")
        st.write(f"📊 Live výpočet: **{round(live_macros['kcal'],1)} kcal** | B: **{round(live_macros['protein'],1)}g** | S: **{round(live_macros['carbs'],1)}g** | T: **{round(live_macros['fats'],1)}g**")
        
        if live_macros["kcal"] > 0:
            protein_pct = (live_macros["protein"] * 4) / live_macros["kcal"]
            if protein_pct < 0.20:
                st.warning("💡 **Tip:** Toto jedlo má relatívne málo bielkovín (pod 20% z kalórií). Skús znížiť sacharidy (napr. menej banánu) alebo pridaj surovinu bohatú na bielkoviny.")
            else:
                st.success("✅ Krásne vyvážené jedlo pre svalový rast!")
        
        if st.session_state.get("show_save_success"):
            st.success("Tento recept bol prepísaný a navždy uložený v databáze!")
            st.session_state.show_save_success = False

        if st.button("💾 ULOŽIŤ UPRAVENÝ RECEPT", type="primary"):
            st.session_state.custom_foods[edit_food]["ingredients"] = st.session_state.edit_recipe.copy()
            save_db()
            st.session_state.show_save_success = True
            st.rerun()
