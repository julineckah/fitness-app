import streamlit as st
from datetime import datetime, date
from zoneinfo import ZoneInfo
import google.generativeai as genai
import json
import os
import time
import re

st.set_page_config(page_title="My Fitness AI", page_icon="🍏", layout="centered")

DB_FILE = "databaza.json"

def get_default_profile():
    return {
        "gender": "Žena", "age": 28, "weight": 71.0, "height": 175.0,
        "activity": "Mierne aktívny (1-3x týždenne tréning)", 
        "goal": "Rekompozícia (Chudnúť tuk, naberať svaly)"
    }

def calculate_targets(profile):
    if profile['gender'] == 'Žena':
        bmr = 10 * profile['weight'] + 6.25 * profile['height'] - 5 * profile['age'] - 161
    else:
        bmr = 10 * profile['weight'] + 6.25 * profile['height'] - 5 * profile['age'] + 5
    
    multipliers = {
        "Sedavý (kancelária, bez tréningu)": 1.2, 
        "Mierne aktívny (1-3x týždenne tréning)": 1.375, 
        "Veľmi aktívny (4-5x týždenne tréning)": 1.55,
        "Extrémne aktívny (každý deň)": 1.725
    }
    tdee = bmr * multipliers.get(profile['activity'], 1.2)
    
    if profile['goal'] == 'Chudnutie (Tuk)': target_kcal = tdee - 400
    elif profile['goal'] == 'Rekompozícia (Chudnúť tuk, naberať svaly)': target_kcal = tdee - 200
    elif profile['goal'] == 'Naberanie (Svaly)': target_kcal = tdee + 300
    else: target_kcal = tdee

    protein = profile['weight'] * 2.0
    fats = profile['weight'] * 1.0
    carbs = (target_kcal - (protein * 4) - (fats * 9)) / 4
    if carbs < 0: carbs = 0
    fiber = (target_kcal / 1000) * 14
    
    return {
        "kcal": int(target_kcal), "protein": int(protein), 
        "carbs": int(carbs), "fats": int(fats), "fiber": int(fiber)
    }

def load_full_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Migrácia zo starej single-user databázy na multi-user s profilom Juli
                if "users" not in data:
                    new_db = {"users": {}}
                    new_db["users"]["Juli"] = {
                        "pin": "1234",
                        "api_key": data.get("api_key", ""),
                        "profile": data.get("profile", get_default_profile()),
                        "daily_logs": data.get("daily_logs", {}),
                        "custom_foods": data.get("custom_foods", {}),
                        "ingredient_db": data.get("ingredient_db", {}),
                        "onboarding_done": True # Juli už onboaring robiť nemusí
                    }
                    with open(DB_FILE, "w", encoding="utf-8") as fw:
                        json.dump(new_db, fw, ensure_ascii=False, indent=4)
                    return new_db
                return data
        except:
            pass
    return {"users": {}}

def save_db():
    if not st.session_state.get("logged_in"): return
    user = st.session_state.current_user
    full_db = load_full_db()
    
    if user not in full_db["users"]:
        full_db["users"][user] = {}
        
    full_db["users"][user]["pin"] = st.session_state.user_pin
    full_db["users"][user]["api_key"] = st.session_state.gemini_key
    full_db["users"][user]["profile"] = st.session_state.profile
    full_db["users"][user]["daily_logs"] = st.session_state.daily_logs
    full_db["users"][user]["custom_foods"] = st.session_state.custom_foods
    full_db["users"][user]["ingredient_db"] = st.session_state.ingredient_db
    full_db["users"][user]["onboarding_done"] = st.session_state.onboarding_done
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(full_db, f, ensure_ascii=False, indent=4)

full_db = load_full_db()

if 'logged_in' not in st.session_state: 
    st.session_state.logged_in = False
if 'current_user' not in st.session_state: 
    st.session_state.current_user = ""
if 'user_pin' not in st.session_state: 
    st.session_state.user_pin = ""

if not st.session_state.logged_in:
    st.title("🍏 Smart Nutričný Asistent")
    st.write("Vitaj v aplikácii! Prosím, prihlás sa, alebo si vytvor nový profil.")
    
    tab_login, tab_reg = st.tabs(["Prihlásenie", "Nová registrácia"])
    
    with tab_login:
        l_name = st.text_input("Tvoje meno:", key="l_name")
        l_pin = st.text_input("PIN kód:", type="password", key="l_pin")
        if st.button("Prihlásiť sa", type="primary"):
            if l_name in full_db["users"]:
                if full_db["users"][l_name]["pin"] == l_pin:
                    st.session_state.logged_in = True
                    st.session_state.current_user = l_name
                    st.session_state.user_pin = l_pin
                    st.success(f"Vitaj späť, {l_name}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Nesprávny PIN kód!")
            else:
                st.error("Používateľ s týmto menom neexistuje. Prejdi na registráciu.")
                
    with tab_reg:
        r_name = st.text_input("Zvoľ si meno:", key="r_name")
        r_pin = st.text_input("Zvoľ si 4-miestny PIN:", type="password", key="r_pin")
        r_pin2 = st.text_input("Zopakuj PIN:", type="password", key="r_pin2")
        if st.button("Vytvoriť profil", type="primary"):
            if not r_name.strip() or not r_pin:
                st.error("Vyplň všetky políčka.")
            elif r_name in full_db["users"]:
                st.error("Toto meno už je obsadené. Zvoľ si iné.")
            elif r_pin != r_pin2:
                st.error("PIN kódy sa nezhodujú!")
            else:
                full_db["users"][r_name] = {
                    "pin": r_pin,
                    "api_key": "",
                    "profile": get_default_profile(),
                    "daily_logs": {},
                    "custom_foods": {},
                    "ingredient_db": {},
                    "onboarding_done": False # Noví užívatelia musia prejsť privítaním
                }
                with open(DB_FILE, "w", encoding="utf-8") as fw:
                    json.dump(full_db, fw, ensure_ascii=False, indent=4)
                    
                st.session_state.logged_in = True
                st.session_state.current_user = r_name
                st.session_state.user_pin = r_pin
                st.success("Profil úspešne vytvorený!")
                time.sleep(1)
                st.rerun()
    
    st.stop()

if "session_loaded" not in st.session_state or st.session_state.session_loaded != st.session_state.current_user:
    user_data = full_db["users"][st.session_state.current_user]
    st.session_state.gemini_key = user_data.get("api_key", "")
    st.session_state.profile = user_data.get("profile", get_default_profile())
    st.session_state.daily_logs = user_data.get("daily_logs", {})
    st.session_state.custom_foods = user_data.get("custom_foods", {})
    st.session_state.ingredient_db = user_data.get("ingredient_db", {})
    
    # Skontrolujeme, či má používateľ API kľúč. Ak áno, budeme predpokladať, že už onboarding absolvoval.
    has_key = bool(st.session_state.gemini_key.strip())
    st.session_state.onboarding_done = user_data.get("onboarding_done", has_key)
    
    st.session_state.edit_recipe = {}
    
    # Lokálny čas a dátum (Europe/Bratislava)
    st.session_state.current_date_str = datetime.now(ZoneInfo("Europe/Bratislava")).strftime("%Y-%m-%d")
    st.session_state.session_loaded = st.session_state.current_user
    
    # AI Skener gramáží v starých receptoch
    migration_needed = False
    for food_name, food_data in st.session_state.custom_foods.items():
        if food_data.get("weight_g", 0) == 0:
            est_weight = 0
            for ing, amt in food_data.get("ingredients", {}).items():
                matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*(g|ml)\b', ing.lower())
                if matches:
                    try:
                        val = float(matches[-1][0].replace(',', '.'))
                        est_weight += val * amt
                    except: pass
            if est_weight > 0:
                food_data["weight_g"] = int(est_weight)
                migration_needed = True
    if migration_needed:
        save_db()

GOALS = calculate_targets(st.session_state.profile)

if not st.session_state.onboarding_done:
    if "onboard_step" not in st.session_state:
        st.session_state.onboard_step = 1
        
    st.title("🎉 Vitaj v Smart Nutričnom Asistentovi!")
    st.progress(st.session_state.onboard_step / 2.0)
    
    if st.session_state.onboard_step == 1:
        st.markdown("### Krok 1/2: Aktivácia AI mozgu 🧠")
        st.markdown("""
        **Táto appka nie je obyčajná kalkulačka kalórií. Je to tvoj osobný, múdry AI asistent.**
        
        ### 🌟 Čo všetko s ňou dokážeš:
        *   ✨ **AI Zápisník:** Už žiadne nudné klikanie surovín! Napíš *"150g losos s ryžou"* a AI jedlo sama roztriedi, odváži a vypočíta makrá.
        *   🤖 **Osobný Radca:** Povie ti, čo presne by si si mala dať na večeru podľa toho, koľko bielkovín ti ešte dnes chýba a čo ťa čaká.
        *   ⚖️ **Smart Porcie:** Sama prepočíta, akú presnú porciu si naložiť na tanier bez zložitého prepočítavania.
        """)
        
        st.info("Aby toto všetko fungovalo, aplikácia potrebuje prepojenie na umelú inteligenciu od Googlu. Vytvorenie kľúča je zadarmo a zaberie len 1 minútu.")
        st.markdown("""
        1. Klikni na tento odkaz: 👉 **[Google AI Studio](https://aistudio.google.com/app/apikey)** (prihlás sa bežným Google účtom).
        2. Klikni na modré tlačidlo **"Create API Key"** (Vytvoriť API kľúč).
        3. Skopíruj dlhý kód a vlož ho do políčka nižšie.
        """)
        
        onb_key = st.text_input("Sem vlož svoj vygenerovaný API kľúč:", type="password")
        
        if st.button("Pokračovať na profil ➡️", type="primary"):
            if not onb_key.strip():
                st.error("Pre fungovanie aplikácie je nutné zadať API kľúč. Postupuj podľa návodu vyššie.")
            else:
                st.session_state.gemini_key = onb_key.strip()
                save_db()
                st.session_state.onboard_step = 2
                st.rerun()
                
    elif st.session_state.onboard_step == 2:
        st.markdown("### Krok 2/2: Tvoj osobný cieľ 🎯")
        st.write("Aby sme ti vedeli vypočítať ideálne porcie a presné makrá na mieru, potrebujeme o tebe pár údajov.")
        
        p = st.session_state.profile
        col1, col2 = st.columns(2)
        with col1:
            o_gender = st.selectbox("Pohlavie:", ["Žena", "Muž"], index=0 if p["gender"]=="Žena" else 1)
            o_age = st.number_input("Vek:", min_value=10, max_value=100, value=int(p["age"]))
            o_weight = st.number_input("Váha (kg):", min_value=30.0, max_value=200.0, value=float(p["weight"]), step=0.5)
        with col2:
            o_height = st.number_input("Výška (cm):", min_value=100.0, max_value=250.0, value=float(p["height"]), step=1.0)
            o_activity = st.selectbox("Aktivita:", [
                "Sedavý (kancelária, bez tréningu)", 
                "Mierne aktívny (1-3x týždenne tréning)", 
                "Veľmi aktívny (4-5x týždenne tréning)",
                "Extrémne aktívny (každý deň)"
            ], index=["Sedavý (kancelária, bez tréningu)", "Mierne aktívny (1-3x týždenne tréning)", "Veľmi aktívny (4-5x týždenne tréning)", "Extrémne aktívny (každý deň)"].index(p["activity"]))
            
        o_goal = st.selectbox("Hlavný cieľ:", [
            "Chudnutie (Tuk)", 
            "Rekompozícia (Chudnúť tuk, naberať svaly)", 
            "Naberanie (Svaly)", 
            "Udržiavanie váhy"
        ], index=["Chudnutie (Tuk)", "Rekompozícia (Chudnúť tuk, naberať svaly)", "Naberanie (Svaly)", "Udržiavanie váhy"].index(p["goal"]))
        
        if st.button("Dokončiť nastavenie a vstúpiť do aplikácie 🚀", type="primary", use_container_width=True):
            st.session_state.profile = {
                "gender": o_gender, "age": o_age, "weight": o_weight, 
                "height": o_height, "activity": o_activity, "goal": o_goal
            }
            st.session_state.onboarding_done = True
            save_db()
            st.balloons()
            time.sleep(2)
            st.rerun()

    # Zastavíme vykresľovanie zvyšku aplikácie, kým používateľ nedokončí onboarding
    st.stop()

def add_macros(kcal, p, c, f, fib, name, meal_type, date_str):
    if date_str not in st.session_state.daily_logs:
        st.session_state.daily_logs[date_str] = {"consumed": {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}, "history": []}
        
    log = st.session_state.daily_logs[date_str]
    log["consumed"]["kcal"] += kcal
    log["consumed"]["protein"] += p
    log["consumed"]["carbs"] += c
    log["consumed"]["fats"] += f
    log["consumed"]["fiber"] += fib
    
    # Použitie lokálneho časového pásma na ukladanie času konzumácie jedla
    log["history"].append({
        "id": str(time.time()), "name": name, "type": meal_type,
        "kcal": kcal, "p": p, "c": c, "f": f, "fib": fib,
        "time": datetime.now(ZoneInfo("Europe/Bratislava")).strftime("%H:%M")
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
    Zanalyzuj toto jedlo alebo zoznam surovín: "{meal_desc}". 
    Rozdeľ ho na jednotlivé suroviny.
    ⚠️ KRITICKÉ PRAVIDLO: Ak používateľ zadá KONKRÉTNU ZNAČKU a produkt (napr. "Vilgain tyčinka"), NEHÁDAJ. Použi presné oficiálne nutričné hodnoty od výrobcu pre daný produkt.
    Pre ostatné bežné suroviny odhadni kalórie (kcal) a makroživiny (protein, carbs, fats, fiber) v gramoch pre to konkrétne množstvo.
    Odhadni aj celkovú hmotnosť tohto jedla v gramoch (total_weight_g).
    
    Vráť PRÍSNY JSON vo formáte:
    {{
        "total_weight_g": 350,
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
    Nevracaj nič iné ako tento JSON.
    """
    model = get_gemini_model()
    if not model: return None
    try:
        response = model.generate_content(prompt)
        txt = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(txt)
    except Exception as e:
        if "429" in str(e):
            st.warning("⏳ Prekročený limit Googlu! Zasahuje Smart Auto-Pilot: Čakám 35 sekúnd...")
            time.sleep(35)
            try:
                response = model.generate_content(prompt)
                txt = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(txt)
            except:
                return None
        st.error(f"Iná chyba: {e}")
        return None

def ask_ai_advisor(rem_kcal, rem_p, rem_c, rem_f, logged_meals):
    eaten_str = ", ".join(logged_meals) if logged_meals else "zatiaľ vôbec nič"
    
    prompt = f"""
    Môj denný cieľ ešte nie je splnený. Do konca dňa mi zostáva presne: {rem_kcal} kcal.
    Z toho by malo byť približne: {rem_p}g bielkovín, {rem_c}g sacharidov a {rem_f}g tukov.
    
    Dnes som už mala tieto chody: {eaten_str}.
    
    Tvoja úloha:
    1. Vydedukuj, aké logické chody (z klasických Raňajky, Obed, Večera, Snack) ma ešte dnes logicky čakajú. (Ak som mala Raňajky, čaká ma Obed, Snack, Večera. Ak som mala aj Obed, čaká ma Snack a Večera atď.)
    2. Zvyšné kalórie a makrá ({rem_kcal} kcal) logicky rozdeľ len medzi TIETO ZOSTÁVAJÚCE chody, aby to dávalo zmysel.
    3. Navrhni 2-3 konkrétne tipy na jedlo presne pre ten chod, ktorý ma čaká ako najbližší, aby som naplnila zvyšné makrá (hlavne bielkoviny). Navrhni aj vhodné veľkosti/gramáže, aby sa to zmestilo do plánu.
    
    Buď veľmi stručný, povzbudivý, píš priateľsky po slovensky.
    """
    model = get_gemini_model()
    if not model: return "Chýba API kľúč."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            st.warning("⏳ Počítam odporúčanie, daj mi ešte cca 30 sekúnd...")
            time.sleep(35)
            try:
                response = model.generate_content(prompt)
                return response.text
            except:
                return "AI je dočasne preťažená, skús to za chvíľku."
        return "Chyba spojenia s AI."

with st.sidebar:
    st.markdown(f"### 👋 Ahoj, {st.session_state.current_user}!")
    st.divider()
    
    st.header("🧠 AI Nastavenia")
    if not st.session_state.gemini_key:
        st.warning("⚠️ Pridaj si API kľúč pre odomknutie funkcií.")
        
    st.write("Tvoj kľúč sa bezpečne ukladá len do tvojho profilu.")
    new_key = st.text_input("Gemini API Key:", value=st.session_state.gemini_key, type="password")
    
    if new_key != st.session_state.gemini_key:
        st.session_state.gemini_key = new_key.strip()
        save_db()
        st.success("Kľúč trvalo uložený! ✅")
        time.sleep(1)
        st.rerun()
        
    st.divider()
    if st.button("🚪 Odhlásiť sa", type="secondary", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.current_user = ""
        st.session_state.user_pin = ""
        del st.session_state["session_loaded"]
        st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 Môj Deň", "✨ AI Zápisník", "➕ Nové jedlo", "⚙️ Správa jedál", "👤 Môj Profil"])

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
        selected_food = st.selectbox("Vyhľadaj jedlo z databázy (Začni písať):", ["(Nevybraté)"] + list(st.session_state.custom_foods.keys()))
    with colB:
        meal_type = st.selectbox("Druh:", ["Raňajky", "Obed", "Večera", "Snack"])
        portion = st.number_input("Veľkosť porcie (1.0 = celá)", min_value=0.1, value=1.0, step=0.1)
    
    if selected_food != "(Nevybraté)":
        food_data = st.session_state.custom_foods[selected_food]
        base_macros = calc_macros(food_data["ingredients"])
        weight_g = food_data.get("weight_g", 0)
        
        p_kcal = base_macros['kcal'] * portion
        p_p = base_macros['protein'] * portion
        p_c = base_macros['carbs'] * portion
        p_f = base_macros['fats'] * portion
        p_fib = base_macros['fiber'] * portion
        
        st.info(f"**Zloženie:** {food_data['desc']}")
        
        if weight_g > 0:
            p_weight = weight_g * portion
            st.write(f"⚖️ **Celý recept má:** {weight_g}g ➔ 🍽️ **Na tanier (váhu) si nalož:** **{int(p_weight)} g**")
            
        rem_kcal = max(0, GOALS['kcal'] - current_log["consumed"]["kcal"])
        st.write(f"📊 **Hodnoty tvojej porcie ({portion}x):** {round(p_kcal,1)} kcal | B: {round(p_p,1)}g | S: {round(p_c,1)}g | T: {round(p_f,1)}g")
        
        meal_proportions = {"Raňajky": 0.25, "Obed": 0.35, "Večera": 0.30, "Snack": 0.10}
        target_meal_kcal = GOALS['kcal'] * meal_proportions.get(meal_type, 0.25)
        
        if base_macros['kcal'] > 0:
            ideal_portion = round(target_meal_kcal / base_macros['kcal'], 1)
            max_portion = round(rem_kcal / base_macros['kcal'], 1)
            
            ideal_portion = min(ideal_portion, max_portion)
            ideal_portion = max(0.1, ideal_portion)
            
            if max_portion <= 0:
                st.warning("⚠️ Na dnes už máš limit naplnený, táto porcia ťa dostane do prebytku.")
            elif portion > max_portion:
                st.warning(f"⚠️ Pozor: Táto porcia ťa hodí do prebytku! Na dnes ti zostali kalórie už len na max **{max_portion}x** násobok.")
            else:
                diff = abs(portion - ideal_portion)
                if diff <= 0.2:
                    st.success(f"✅ Skvelá voľba! Veľkosť {portion}x je pre tvoj '{meal_type}' úplne ideálna.")
                else:
                    st.info(f"💡 Tip pre vyvážený deň: Ak si na '{meal_type}' dáš **{ideal_portion}x** porciu, zostane ti ideálny priestor aj pre ďalšie chody.")

        with colC:
            st.write("") 
            st.write("") 
            if st.button("➕ Zjesť", type="primary", use_container_width=True):
                meal_name_to_save = selected_food if portion == 1.0 else f"{selected_food} ({portion}x)"
                add_macros(p_kcal, p_p, p_c, p_f, p_fib, meal_name_to_save, meal_type, date_str)
                st.success(f"Pridané a trvalo uložené!")
                time.sleep(1)
                st.rerun()

    st.divider()
    st.subheader(f"📊 Tvoj deň ({selected_date.strftime('%d.%m.%Y')})")
    
    c_kcal = current_log["consumed"]["kcal"]
    st.metric(label="🔥 Kalórie (kcal)", value=f"{int(c_kcal)} / {GOALS['kcal']}")
    st.progress(min(c_kcal / GOALS['kcal'] if GOALS['kcal'] else 0, 1.0))
    st.write("")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        c_p = current_log["consumed"]["protein"]
        st.metric("Bielkoviny", f"{int(c_p)} / {GOALS['protein']}g")
        st.progress(min(c_p / GOALS['protein'] if GOALS['protein'] else 0, 1.0))
    with col2:
        c_c = current_log["consumed"]["carbs"]
        st.metric("Sacharidy", f"{int(c_c)} / {GOALS['carbs']}g")
        st.progress(min(c_c / GOALS['carbs'] if GOALS['carbs'] else 0, 1.0))
    with col3:
        c_f = current_log["consumed"]["fats"]
        st.metric("Tuky", f"{int(c_f)} / {GOALS['fats']}g")
        st.progress(min(c_f / GOALS['fats'] if GOALS['fats'] else 0, 1.0))
    with col4:
        c_fib = current_log["consumed"]["fiber"]
        st.metric("Vláknina", f"{int(c_fib)} / {GOALS['fiber']}g")
        st.progress(min(c_fib / GOALS['fiber'] if GOALS['fiber'] else 0, 1.0))

    st.write("")
    
    logged_meal_types = list(set([m["type"] for m in current_log["history"]]))
    
    with st.expander("💡 AI Radca: Čo by som mala ešte dnes zjesť?"):
        if st.button("✨ Zistiť tipy pre zvyšok dňa"):
            rem_kcal = max(0, GOALS['kcal'] - c_kcal)
            rem_p = max(0, GOALS['protein'] - c_p)
            rem_c = max(0, GOALS['carbs'] - c_c)
            rem_f = max(0, GOALS['fats'] - c_f)
            
            if rem_kcal < 100:
                st.success("Tvoje dnešné ciele sú už naplnené! Skvelá práca. 👏")
            else:
                with st.spinner("AI číta tvoj denník a vymýšľa, čo ďalej..."):
                    ai_tip = ask_ai_advisor(int(rem_kcal), int(rem_p), int(rem_c), int(rem_f), logged_meal_types)
                    st.info(ai_tip)

    st.divider()
    st.subheader("📝 Denník")
    if not current_log["history"]:
        st.write("Zatiaľ si dnes nič nezjedla.")
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
                            for key in current_log["consumed"]:
                                if current_log["consumed"][key] < 0: current_log["consumed"][key] = 0
                                
                            current_log["history"] = [x for x in current_log["history"] if x["id"] != m["id"]]
                            save_db()
                            st.rerun()
                st.divider()

with tab2:
    st.subheader("✨ AI Zápisník")
    st.write("Jedným klikom zjedz alebo navždy ulož celé jedlo. AI ho roztriedi na suroviny a zistí váhu.")
    ai_meal = st.text_area("Napríklad: '150g losos s ryžou a brokolicou' alebo '1 Vilgain tyčinka Double Trouble 55g'", height=100)
    
    if st.button("✨ Zanalyzovať jedlo"):
        if ai_meal:
            if not st.session_state.gemini_key: st.error("Chýba API kľúč!")
            else:
                with st.spinner("Umelá inteligencia pripravuje rozbor..."):
                    res = analyze_meal_to_recipe(ai_meal)
                    if res and "ingredients" in res:
                        st.session_state.ai_last_meal = res
                        st.session_state.ai_last_meal_name = ai_meal
                    else:
                        st.error("Chyba analýzy. Skús preformulovať jedlo.")
    
    if st.session_state.get("ai_last_meal"):
        res = st.session_state.ai_last_meal
        st.write("### 🥗 Výsledok:")
        total_kcal = total_p = total_c = total_f = total_fib = 0
        new_ingredients = {}
        total_weight = res.get("total_weight_g", 0)
        
        for item in res["ingredients"]:
            st.write(f"- **{item['name']}**: {item['kcal']} kcal (B: {item['protein']}g | S: {item['carbs']}g | T: {item['fats']}g)")
            total_kcal += item['kcal']; total_p += item['protein']; total_c += item['carbs']; total_f += item['fats']; total_fib += item['fiber']
            
            ing_name = item["name"]
            st.session_state.ingredient_db[ing_name] = {
                "kcal": item["kcal"], "protein": item["protein"], "carbs": item["carbs"], "fats": item["fats"], "fiber": item["fiber"]
            }
            new_ingredients[ing_name] = 1.0 
            
        st.info(f"**Spolu:** {round(total_kcal,1)} kcal | B: {round(total_p,1)}g | S: {round(total_c,1)}g | T: {round(total_f,1)}g | ⚖️ Odhad. hmotnosť: {total_weight}g")
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**A: Len zjesť DNES**")
            meal_type_ai = st.selectbox("Ako aký chod?", ["Obed", "Raňajky", "Večera", "Snack"], key="ai_type")
            if st.button("🍽️ Zjesť a nezakladať recept"):
                add_macros(total_kcal, total_p, total_c, total_f, total_fib, "AI: " + st.session_state.ai_last_meal_name[:20]+"...", meal_type_ai, st.session_state.current_date_str)
                del st.session_state["ai_last_meal"]
                st.success("Zapísané do denníka!")
                time.sleep(1)
                st.rerun()
                
        with col2:
            st.write("**B: Zjesť + Uložiť do receptov**")
            new_recipe_name_ai = st.text_input("Ako sa toto jedlo bude volať?")
            meal_type_ai_save = st.selectbox("Dnes zjesť ako:", ["Obed", "Raňajky", "Večera", "Snack"], key="ai_type_save")
            if st.button("💾 Uložiť trvalo + Zjesť"):
                if new_recipe_name_ai:
                    st.session_state.custom_foods[new_recipe_name_ai] = {
                        "desc": st.session_state.ai_last_meal_name, 
                        "ingredients": new_ingredients,
                        "weight_g": total_weight
                    }
                    save_db()
                    add_macros(total_kcal, total_p, total_c, total_f, total_fib, new_recipe_name_ai, meal_type_ai_save, st.session_state.current_date_str)
                    del st.session_state["ai_last_meal"]
                    st.success("Zjedné a navždy uložené do tvojej databázy!")
                    time.sleep(1)
                    st.rerun()

with tab3:
    st.subheader("➕ Vytvoriť recept (cez AI)")
    st.write("Len opíš, čo si varila, AI sa postará o zvyšok vrátane odhadu hmotnosti.")
    new_name = st.text_input("Názov jedla (napr. 'Moje lievance so sirupom'):")
    new_desc = st.text_area("Vymenuj všetky ingrediencie aj s množstvami (odmerky, lyžice, gramy...):")
    
    if st.button("✨ Vygenerovať a Uložiť do zoznamu", type="primary"):
        if new_name and new_desc:
            with st.spinner("Budujem tvoj nový recept..."):
                res = analyze_meal_to_recipe(new_desc)
                if res and "ingredients" in res:
                    new_ingredients = {}
                    for item in res["ingredients"]:
                        ing_name = item["name"]
                        st.session_state.ingredient_db[ing_name] = {
                            "kcal": item["kcal"], "protein": item["protein"], "carbs": item["carbs"], "fats": item["fats"], "fiber": item["fiber"]
                        }
                        new_ingredients[ing_name] = 1.0
                    
                    st.session_state.custom_foods[new_name] = {
                        "desc": new_desc, 
                        "ingredients": new_ingredients,
                        "weight_g": res.get("total_weight_g", 0)
                    }
                    save_db()
                    st.success(f"Jedlo uložené! Nájdeš ho v záložke 'Správa jedál'.")
                    time.sleep(1.5)
                    st.rerun()

with tab4:
    st.subheader("⚙️ Správa jedál a surovín")
    edit_food = st.selectbox("Vyber jedlo na úpravu:", ["(Nevybraté)"] + list(st.session_state.custom_foods.keys()))
    
    if edit_food != "(Nevybraté)":
        if "current_edit_food" not in st.session_state or st.session_state.current_edit_food != edit_food:
            st.session_state.edit_recipe = st.session_state.custom_foods[edit_food]["ingredients"].copy()
            st.session_state.current_edit_food = edit_food

        st.write("### 🥣 Úprava receptu")
        new_recipe_name_input = st.text_input("Názov jedla:", value=edit_food)
        
        colW1, colW2 = st.columns([3, 1])
        with colW1:
            new_weight_input = st.number_input("Celková hmotnosť uvareného jedla (v gramoch, 0 = neznáma):", value=int(st.session_state.custom_foods[edit_food].get("weight_g", 0)), step=10)
        with colW2:
            st.write("")
            st.write("")
            if st.button("✨ Spočítaj váhu", use_container_width=True):
                est = 0
                for ing, amt in st.session_state.edit_recipe.items():
                    matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*(g|ml)\b', ing.lower())
                    if matches:
                        try: est += float(matches[-1][0].replace(',', '.')) * amt
                        except: pass
                if est > 0:
                    st.session_state.custom_foods[edit_food]["weight_g"] = int(est)
                    save_db()
                    st.success(f"Váha zistená: {int(est)}g")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Nenašli sa gramy.")
        
        st.write("**Suroviny:**")
        updated_recipe = {}
        for ing, amount in list(st.session_state.edit_recipe.items()):
            # Vyťažíme aktuálnu hodnotu widgetu pre živý prepočet
            current_amt = st.session_state.get(f"amt_{ing}", amount)
            
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1: 
                st.markdown(f"**{ing}**")
                # Výpis konkrétnych makroživín pre túto surovinu priamo pod názvom
                if ing in st.session_state.ingredient_db:
                    d = st.session_state.ingredient_db[ing]
                    st.caption(f"*(🔥 {round(d['kcal'] * current_amt, 1)} kcal | B: {round(d['protein'] * current_amt, 1)}g | S: {round(d['carbs'] * current_amt, 1)}g | T: {round(d['fats'] * current_amt, 1)}g)*")
            with col2: 
                new_amount = st.number_input("Násobok porcie", min_value=0.0, value=float(amount), step=0.1, key=f"amt_{ing}")
                updated_recipe[ing] = new_amount
            with col3:
                st.write("")
                if st.button("🗑️", key=f"del_{ing}"):
                    del st.session_state.edit_recipe[ing]
                    st.rerun()
        
        st.session_state.edit_recipe = updated_recipe

        st.divider()
        st.write("**🤖 Pridať nové suroviny do tohto receptu (Cez AI):**")
        ai_ing = st.text_input("Napr. '1 lyžica chia, 1 čajová lyžička arašidového masla':")
        if st.button("✨ Zistiť živiny a pridať suroviny"):
            if ai_ing:
                with st.spinner("AI rozdeľuje tvoje suroviny..."):
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
                        st.success("Suroviny úspešne pridané do zoznamu!")
                        time.sleep(1)
                        st.rerun()
                            
        st.divider()
        st.write("**✍️ Alebo pridať surovinu RUČNE z etikety:**")
        with st.expander("Rozbaliť formulár pre ručné zadanie"):
            man_name = st.text_input("Presný Názov (napr. 'Vilgain tyčinka 55g')")
            colK, colP, colC, colF, colFib = st.columns(5)
            with colK: man_kcal = st.number_input("Kcal", min_value=0.0, step=1.0)
            with colP: man_p = st.number_input("Bielk. (g)", min_value=0.0, step=0.1)
            with colC: man_c = st.number_input("Sach. (g)", min_value=0.0, step=0.1)
            with colF: man_f = st.number_input("Tuky (g)", min_value=0.0, step=0.1)
            with colFib: man_fib = st.number_input("Vlák. (g)", min_value=0.0, step=0.1)
            
            if st.button("💾 Uložiť ručne"):
                if man_name:
                    st.session_state.ingredient_db[man_name] = {
                        "kcal": man_kcal, "protein": man_p, "carbs": man_c, "fats": man_f, "fiber": man_fib
                    }
                    if man_name in st.session_state.edit_recipe: st.session_state.edit_recipe[man_name] += 1.0
                    else: st.session_state.edit_recipe[man_name] = 1.0
                    save_db()
                    st.success("Ručná surovina pridaná!")
                    time.sleep(1)
                    st.rerun()
        
        st.divider()
        live_macros = calc_macros(st.session_state.edit_recipe)
        st.write("### 🧠 Smart Analýza")
        st.write(f"📊 Live výpočet: **{round(live_macros['kcal'],1)} kcal** | B: **{round(live_macros['protein'],1)}g** | S: **{round(live_macros['carbs'],1)}g** | T: **{round(live_macros['fats'],1)}g**")
        
        if live_macros["kcal"] > 0:
            protein_pct = (live_macros["protein"] * 4) / live_macros["kcal"]
            if protein_pct < 0.20:
                st.warning("💡 **Tip:** Toto jedlo má málo bielkovín (pod 20% energie). Pridaj trochu kvalitného proteínu, aby si naplnila ciele pre rast svalov.")
            else:
                st.success("✅ Krásne vyvážené jedlo!")

        colA, colB = st.columns(2)
        with colA:
            if st.button("💾 ULOŽIŤ UPRAVENÝ RECEPT", type="primary", use_container_width=True):
                final_name = new_recipe_name_input.strip()
                if final_name != edit_food and final_name != "":
                    if final_name in st.session_state.custom_foods:
                        st.error(f"Jedlo s názvom '{final_name}' už existuje! Zvoľ iný názov.")
                    else:
                        st.session_state.custom_foods[final_name] = {
                            "desc": st.session_state.custom_foods[edit_food].get("desc", ""),
                            "ingredients": st.session_state.edit_recipe.copy(),
                            "weight_g": new_weight_input
                        }
                        del st.session_state.custom_foods[edit_food]
                        if "current_edit_food" in st.session_state: del st.session_state["current_edit_food"]
                        save_db()
                        st.success("Názov, váha aj zmeny v recepte boli uložené.")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.session_state.custom_foods[edit_food]["ingredients"] = st.session_state.edit_recipe.copy()
                    st.session_state.custom_foods[edit_food]["weight_g"] = new_weight_input
                    save_db()
                    st.success("Zmeny v recepte boli uložené.")
                    time.sleep(1)
                    st.rerun()
        with colB:
            if st.button("🚨 VYMAZAŤ CELÝ RECEPT", type="secondary", use_container_width=True):
                del st.session_state.custom_foods[edit_food]
                save_db()
                if "current_edit_food" in st.session_state: del st.session_state["current_edit_food"]
                st.success("Recept trvalo vymazaný!")
                time.sleep(1)
                st.rerun()

with tab5:
    st.subheader("👤 Môj Profil a Ciele")
    st.write("Aplikácia prispôsobuje ciele zmenám v tvojej váhe. Stačí sem občas aktualizovať čísla.")
    
    p = st.session_state.profile
    
    col1, col2 = st.columns(2)
    with col1:
        new_gender = st.selectbox("Pohlavie:", ["Žena", "Muž"], index=0 if p["gender"]=="Žena" else 1)
        new_age = st.number_input("Vek:", min_value=10, max_value=100, value=int(p["age"]))
        new_weight = st.number_input("Váha (kg):", min_value=30.0, max_value=200.0, value=float(p["weight"]), step=0.5)
    with col2:
        new_height = st.number_input("Výška (cm):", min_value=100.0, max_value=250.0, value=float(p["height"]), step=1.0)
        new_activity = st.selectbox("Aktivita:", [
            "Sedavý (kancelária, bez tréningu)", 
            "Mierne aktívny (1-3x týždenne tréning)", 
            "Veľmi aktívny (4-5x týždenne tréning)",
            "Extrémne aktívny (každý deň)"
        ], index=["Sedavý (kancelária, bez tréningu)", "Mierne aktívny (1-3x týždenne tréning)", "Veľmi aktívny (4-5x týždenne tréning)", "Extrémne aktívny (každý deň)"].index(p["activity"]))
        
    new_goal = st.selectbox("Hlavný cieľ (Rekompozícia = Svaly + Chudnutie):", [
        "Chudnutie (Tuk)", 
        "Rekompozícia (Chudnúť tuk, naberať svaly)", 
        "Naberanie (Svaly)", 
        "Udržiavanie váhy"
    ], index=["Chudnutie (Tuk)", "Rekompozícia (Chudnúť tuk, naberať svaly)", "Naberanie (Svaly)", "Udržiavanie váhy"].index(p["goal"]))

    if st.button("💾 Uložiť profil a prepočítať ciele", type="primary"):
        st.session_state.profile = {
            "gender": new_gender, "age": new_age, "weight": new_weight, 
            "height": new_height, "activity": new_activity, "goal": new_goal
        }
        save_db()
        st.success("Profil uložený! Ciele boli prepočítané na najnovšiu váhu.")
        time.sleep(1)
        st.rerun()
        
    st.divider()
    st.write("### 🎯 Aktuálne denné ciele na základe vedy (ISSN):")
    st.info(f"Kalórie: **{GOALS['kcal']} kcal** | Bielkoviny: **{GOALS['protein']}g** | Sacharidy: **{GOALS['carbs']}g** | Tuky: **{GOALS['fats']}g** | Vláknina: **{GOALS['fiber']}g**")
