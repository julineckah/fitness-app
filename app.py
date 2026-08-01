import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date
import google.generativeai as genai
import json
import os
import time

st.set_page_config(page_title="My Fitness AI", page_icon="🍏", layout="centered")

DB_FILE = "databaza.json"
GOALS = {"kcal": 1950, "protein": 130, "carbs": 200, "fats": 65, "fiber": 30}

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # MIGRÁCIA: Ak má appka starý formát bez "daily_logs", preklopíme ho na dnešok
                if "daily_logs" not in data:
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    data["daily_logs"] = {
                        today_str: {
                            "consumed": data.get("consumed", {"kcal": 0, "protein": 0.0, "carbs": 0.0, "fats": 0.0, "fiber": 0.0}),
                            "history": data.get("history", [])
                        }
                    }
                return data
        except:
            pass
            
    today_str = datetime.now().strftime("%Y-%m-%d")
    return {
        "api_key": "",
        "daily_logs": {
            today_str: {"consumed": {"kcal": 0, "protein": 0.0, "carbs": 0.0, "fats": 0.0, "fiber": 0.0}, "history": []}
        },
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
        "api_key": st.session_state.gemini_key,
        "daily_logs": st.session_state.daily_logs,
        "custom_foods": st.session_state.custom_foods,
        "ingredient_db": st.session_state.ingredient_db
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)

db_data = load_db()

if 'gemini_key' not in st.session_state: st.session_state.gemini_key = db_data.get("api_key", "")
if 'daily_logs' not in st.session_state: st.session_state.daily_logs = db_data.get("daily_logs", {})
if 'custom_foods' not in st.session_state: st.session_state.custom_foods = db_data.get("custom_foods", {})
if 'ingredient_db' not in st.session_state: st.session_state.ingredient_db = db_data.get("ingredient_db", {})
if 'edit_recipe' not in st.session_state: st.session_state.edit_recipe = {}
if 'show_save_success' not in st.session_state: st.session_state.show_save_success = False
if 'current_date_str' not in st.session_state: st.session_state.current_date_str = datetime.now().strftime("%Y-%m-%d")

def add_macros(kcal, p, c, f, fib, name, meal_type, date_str):
    if date_str not in st.session_state.daily_logs:
        st.session_state.daily_logs[date_str] = {"consumed": {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}, "history": []}
        
    log = st.session_state.daily_logs[date_str]
    log["consumed"]["kcal"] += kcal
    log["consumed"]["protein"] += p
    log["consumed"]["carbs"] += c
    log["consumed"]["fats"] += f
    log["consumed"]["fiber"] += fib
    
    log["history"].append({
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

def call_gemini(query):
    prompt = f"""
    Zisti presné nutričné hodnoty pre túto surovinu/jedlo: "{query}".
    ⚠️ KRITICKÉ PRAVIDLO: Ak používateľ zadá KONKRÉTNU ZNAČKU a produkt (napríklad "Vilgain proteínová tyčinka Double Chocolate"), NEHÁDAJ. Použi presné oficiálne nutričné hodnoty od výrobcu pre daný produkt, ktoré máš v pamäti.
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
            st.warning("⏳ Prekročili sme limit žiadostí (príliš rýchlo). Dávam si 35 sekúnd pauzu a stiahnem to...")
            time.sleep(35)
            try:
                response = model.generate_content(prompt)
                txt = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(txt)
            except:
                return None
        return None

def analyze_meal_to_recipe(meal_desc):
    prompt = f"""
    Zanalyzuj toto jedlo: "{meal_desc}". 
    Rozdeľ ho na jednotlivé suroviny. 
    ⚠️ KRITICKÉ PRAVIDLO: Ak používateľ zadá KONKRÉTNU ZNAČKU a produkt (napríklad "Vilgain proteínová tyčinka Double Chocolate", "Rajo cottage cheese"), NEHÁDAJ. Použi presné oficiálne nutričné hodnoty od výrobcu pre daný produkt.
    Pre ostatné bežné suroviny odhadni kalórie (kcal) a makroživiny (protein, carbs, fats, fiber) v gramoch pre to konkrétne odhadované množstvo v porcii.
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
            st.warning("⏳ Prekročili sme limit žiadostí (príliš rýchlo). Dávam si 35 sekúnd pauzu a stiahnem to...")
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
    st.write("Tvoj Gemini API kľúč je bezpečne uložený. Nemusíš ho zadávať znova.")
    
    new_key = st.text_input("Gemini API Key:", value=st.session_state.gemini_key, type="password")
    
    if new_key != st.session_state.gemini_key:
        st.session_state.gemini_key = new_key.strip()
        save_db()
        st.success("Kľúč uložený! ✅")
        st.rerun()
        
    st.divider()
    st.caption("Tvoje dáta sa ukladajú lokálne a bezpečne v databaza.json")

tab1, tab2, tab3, tab4 = st.tabs(["📅 Môj Deň", "✨ AI Zápisník", "➕ Nové jedlo", "⚙️ Správa jedál"])

with tab1:
    col_date, _ = st.columns([1, 1])
    with col_date:
        default_date = datetime.strptime(st.session_state.current_date_str, "%Y-%m-%d").date()
        selected_date = st.date_input("📅 Vyber si deň:", default_date)
        
    date_str = selected_date.strftime("%Y-%m-%d")
    st.session_state.current_date_str = date_str
    
    if date_str not in st.session_state.daily_logs:
        st.session_state.daily_logs[date_str] = {"consumed": {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}, "history": []}
        save_db()
        
    current_log = st.session_state.daily_logs[date_str]

    st.subheader("🍽️ Pridať do tohto dňa")
    colA, colB, colC = st.columns([2, 1, 1])
    with colA:
        selected_food = st.selectbox("Začni písať pre vyhľadanie jedla:", ["(Nevybraté)"] + list(st.session_state.custom_foods.keys()))
    with colB:
        meal_type = st.selectbox("Druh:", ["Raňajky", "Obed", "Večera", "Snack"])
    
    if selected_food != "(Nevybraté)":
        food_data = st.session_state.custom_foods[selected_food]
        macros = calc_macros(food_data["ingredients"])
        st.info(f"**Zloženie:** {food_data['desc']}")
        st.write(f"📊 **Hodnoty:** {round(macros['kcal'],1)} kcal | B: {round(macros['protein'],1)}g | S: {round(macros['carbs'],1)}g | T: {round(macros['fats'],1)}g")
        
        with colC:
            st.write("") 
            st.write("") 
            if st.button("➕ Zjesť", type="primary", use_container_width=True):
                add_macros(macros['kcal'], macros['protein'], macros['carbs'], macros['fats'], macros['fiber'], selected_food, meal_type, date_str)
                st.success(f"Pridané!")
                time.sleep(1)
                st.rerun()

    st.divider()
    st.subheader(f"📊 Prehľad ({selected_date.strftime('%d.%m.%Y')})")
    
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
        fig.update_layout(height=200, margin=dict(l=10, r=10, t=70, b=10))
        return fig

    st.plotly_chart(create_gauge("Kalórie (kcal)", current_log["consumed"]["kcal"], GOALS["kcal"], "#3b82f6"), use_container_width=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.plotly_chart(create_gauge("Bielkoviny", current_log["consumed"]["protein"], GOALS["protein"], "#ef4444"), use_container_width=True)
    with c2: st.plotly_chart(create_gauge("Sacharidy", current_log["consumed"]["carbs"], GOALS["carbs"], "#10b981"), use_container_width=True)
    with c3: st.plotly_chart(create_gauge("Tuky", current_log["consumed"]["fats"], GOALS["fats"], "#f59e0b"), use_container_width=True)
    with c4: st.plotly_chart(create_gauge("Vláknina", current_log["consumed"]["fiber"], GOALS["fiber"], "#8b5cf6"), use_container_width=True)

    st.subheader("📝 Záznamník dňa")
    if not current_log["history"]:
        st.write("Zatiaľ žiadne záznamy pre tento deň.")
    else:
        for meal in ["Raňajky", "Obed", "Večera", "Snack"]:
            meals_in_cat = [m for m in current_log["history"] if m["type"] == meal]
            if meals_in_cat:
                st.markdown(f"**{meal}**")
                for m in meals_in_cat:
                    col1, col2, col3 = st.columns([1, 4, 1])
                    with col1: st.caption(m["time"])
                    with col2: st.write(f"**{m['name']}** ({round(m['kcal'])} kcal)")
                    with col3:
                        if st.button("🗑️", key=f"del_{date_str}_{m['id']}"):
                            current_log["consumed"]["kcal"] -= m["kcal"]
                            current_log["consumed"]["protein"] -= m["p"]
                            current_log["consumed"]["carbs"] -= m["c"]
                            current_log["consumed"]["fats"] -= m["f"]
                            current_log["consumed"]["fiber"] -= m["fib"]
                            # Poistka proti záporným hodnotám
                            for key in current_log["consumed"]:
                                if current_log["consumed"][key] < 0: current_log["consumed"][key] = 0
                                
                            current_log["history"] = [x for x in current_log["history"] if x["id"] != m["id"]]
                            save_db()
                            st.rerun()
                st.divider()

with tab2:
    st.subheader("✨ AI Zápisník")
    st.write("Zjedla si niečo úplne mimo plánu (napr. špecifickú proteínovú tyčinku)? AI ti to zanalyzuje a môžeš to rovno uložiť!")
    
    ai_meal = st.text_area("Napr.: '150g losos s hrstou ryže a brokolicou' alebo '1 Vilgain proteínová tyčinka Double Chocolate'.", height=100)
    
    if st.button("✨ Zanalyzovať jedlo"):
        if ai_meal:
            if not st.session_state.gemini_key:
                st.error("Chýba API kľúč!")
            else:
                with st.spinner("AI analyzuje tvoje jedlo (a hľadá presné značky)..."):
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
        new_ingredients = {}
        
        for item in res["ingredients"]:
            st.write(f"- **{item['name']}**: {item['kcal']} kcal (B: {item['protein']}g | S: {item['carbs']}g | T: {item['fats']}g)")
            total_kcal += item['kcal']
            total_p += item['protein']
            total_c += item['carbs']
            total_f += item['fats']
            total_fib += item['fiber']
            
            ing_name = item["name"]
            st.session_state.ingredient_db[ing_name] = {
                "kcal": item["kcal"], "protein": item["protein"],
                "carbs": item["carbs"], "fats": item["fats"], "fiber": item["fiber"]
            }
            new_ingredients[ing_name] = 1.0 
            
        st.info(f"**Spolu:** {round(total_kcal,1)} kcal | B: {round(total_p,1)}g | S: {round(total_c,1)}g | T: {round(total_f,1)}g")
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Možnosť A: Len zjesť DNES**")
            meal_type_ai = st.selectbox("Ako aký chod?", ["Obed", "Raňajky", "Večera", "Snack"], key="ai_type")
            if st.button("🍽️ Pridať do aktuálneho dňa"):
                add_macros(total_kcal, total_p, total_c, total_f, total_fib, "AI: " + st.session_state.ai_last_meal_name[:20]+"...", meal_type_ai, st.session_state.current_date_str)
                del st.session_state["ai_last_meal"]
                st.success("Záznam pridaný!")
                time.sleep(1.5)
                st.rerun()
                
        with col2:
            st.write("**Možnosť B: Uložiť NAVŽDY (Aj zjesť)**")
            new_recipe_name = st.text_input("Vymysli si názov (napr. Losos s ryžou):")
            meal_type_ai_save = st.selectbox("A zjesť ho dnes ako:", ["Obed", "Raňajky", "Večera", "Snack"], key="ai_type_save")
            if st.button("💾 Uložiť jedlo + Zjesť"):
                if new_recipe_name:
                    st.session_state.custom_foods[new_recipe_name] = {
                        "desc": st.session_state.ai_last_meal_name,
                        "ingredients": new_ingredients
                    }
                    save_db()
                    add_macros(total_kcal, total_p, total_c, total_f, total_fib, new_recipe_name, meal_type_ai_save, st.session_state.current_date_str)
                    
                    del st.session_state["ai_last_meal"]
                    st.success(f"Jedlo '{new_recipe_name}' trvalo uložené a pridané do dňa!")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.warning("Musíš zadať názov!")

with tab3:
    st.subheader("➕ Vytvoriť nový recept pomocou AI")
    st.write("Nadiktuj zloženie jedla alebo vymenuj suroviny. AI z neho vyrobí presný recept so všetkými oficiálnymi živinami.")
    
    new_name = st.text_input("Krátky Názov (napr. 'Kuracie rizoto s hráškom'):")
    new_desc = st.text_area("Rozpíš presné zloženie (napr. '100g kuracie prsia, 50g ryža, 1 Vilgain tyčinka').")
    
    if st.button("✨ Vygenerovať a Trvalo uložiť"):
        if new_name and new_desc:
            if not st.session_state.gemini_key:
                st.error("Chýba API kľúč!")
            else:
                with st.spinner("AI buduje tvoj nový recept a hľadá presné hodnoty..."):
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
                        st.success(f"BOMBA! Jedlo '{new_name}' bolo zanalyzované a uložené. Nájdeš ho v 'Správe jedál'.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("AI to nezvládla zanalyzovať. Skús to napísať inak.")
        else:
            st.warning("Vyplň názov aj popis jedla.")

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
        st.write("**🤖 Pridať nové suroviny do tohto receptu (Cez AI):**")
        ai_ing = st.text_input("Môžeš aj viacero naraz! Napr. '1 odmerka proteínu, 150g Tofu, 1 lyžica chia'")
        if st.button("✨ Zistiť živiny a pridať do receptu"):
            if ai_ing:
                if not st.session_state.gemini_key:
                    st.error("Chýba API kľúč!")
                else:
                    with st.spinner(f"Zisťujem hodnoty pre tvoje suroviny..."):
                        res = analyze_meal_to_recipe(ai_ing)
                        if res and "ingredients" in res:
                            for item in res["ingredients"]:
                                new_name = item["name"]
                                st.session_state.ingredient_db[new_name] = {
                                    "kcal": item["kcal"], "protein": item["protein"], 
                                    "carbs": item["carbs"], "fats": item["fats"], "fiber": item["fiber"]
                                }
                                if new_name in st.session_state.edit_recipe:
                                    st.session_state.edit_recipe[new_name] += 1.0
                                else:
                                    st.session_state.edit_recipe[new_name] = 1.0
                            
                            save_db()
                            st.success(f"Všetky suroviny úspešne pridané!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Nepodarilo sa analyzovať. Skús preformulovať.")
                            
        st.divider()
        st.write("**✍️ Alebo pridať špecifickú surovinu RUČNE (z etikety na obale):**")
        with st.expander("Rozbaliť formulár pre ručné zadanie"):
            man_name = st.text_input("Názov (napr. 'Vilgain tyčinka Double Trouble 55g')")
            colK, colP, colC, colF, colFib = st.columns(5)
            with colK: man_kcal = st.number_input("Kcal", min_value=0.0, step=1.0)
            with colP: man_p = st.number_input("Bielkoviny", min_value=0.0, step=0.1)
            with colC: man_c = st.number_input("Sacharidy", min_value=0.0, step=0.1)
            with colF: man_f = st.number_input("Tuky", min_value=0.0, step=0.1)
            with colFib: man_fib = st.number_input("Vláknina", min_value=0.0, step=0.1)
            
            if st.button("💾 Uložiť ručne a pridať do receptu"):
                if man_name:
                    st.session_state.ingredient_db[man_name] = {
                        "kcal": man_kcal, "protein": man_p,
                        "carbs": man_c, "fats": man_f, "fiber": man_fib
                    }
                    if man_name in st.session_state.edit_recipe:
                        st.session_state.edit_recipe[man_name] += 1.0
                    else:
                        st.session_state.edit_recipe[man_name] = 1.0
                    save_db()
                    st.success("Surovina pridaná!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Musíš zadať názov.")
        
        st.divider()
        live_macros = calc_macros(st.session_state.edit_recipe)
        st.write("### 🧠 Smart Analýza")
        st.write(f"📊 Live výpočet: **{round(live_macros['kcal'],1)} kcal** | B: **{round(live_macros['protein'],1)}g** | S: **{round(live_macros['carbs'],1)}g** | T: **{round(live_macros['fats'],1)}g**")
        
        if live_macros["kcal"] > 0:
            protein_pct = (live_macros["protein"] * 4) / live_macros["kcal"]
            if protein_pct < 0.20:
                st.warning("💡 **Tip:** Toto jedlo má málo bielkovín. Pridaj v políčkach vyššie surovinu bohatú na bielkoviny (napr. proteín).")
            else:
                st.success("✅ Krásne vyvážené jedlo!")
        
        if st.session_state.get("show_save_success"):
            st.success("Tento recept bol prepísaný a navždy uložený!")
            st.session_state.show_save_success = False

        colA, colB = st.columns(2)
        with colA:
            if st.button("💾 ULOŽIŤ ÚPRAVY", type="primary", use_container_width=True):
                st.session_state.custom_foods[edit_food]["ingredients"] = st.session_state.edit_recipe.copy()
                save_db()
                st.session_state.show_save_success = True
                st.rerun()
        
        with colB:
            if st.button("🚨 VYMAZAŤ CELÝ RECEPT", type="secondary", use_container_width=True):
                del st.session_state.custom_foods[edit_food]
                save_db()
                if "current_edit_food" in st.session_state:
                    del st.session_state["current_edit_food"]
                st.success("Recept bol trvalo vymazaný z databázy!")
                time.sleep(1.5)
                st.rerun()
