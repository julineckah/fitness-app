# ... existing code ...
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import uuid # Pridané pre unikátne ID jedál v histórii (kvôli mazaniu)

# --- DATABÁZA INGREDIENCIÍ (Na výpočty) ---
# Tieto hodnoty sú presne prepočítané. Aplikácia z nich skladá tvoje jedlá.
BASE_INGREDIENTS = {
    "Vločky (lyžica - 10g)": {"kcal": 38, "protein": 1.3, "carbs": 6.8, "fats": 0.7, "fiber": 1.0},
    "Banán (1 ks - 120g)": {"kcal": 107, "protein": 1.3, "carbs": 27.0, "fats": 0.4, "fiber": 3.1},
    "Chia (lyžica - 10g)": {"kcal": 49, "protein": 1.7, "carbs": 4.2, "fats": 3.1, "fiber": 3.4},
    "Domáci jogurt (100g)": {"kcal": 61, "protein": 3.5, "carbs": 4.7, "fats": 3.3, "fiber": 0.0},
    "Arašidové maslo (lyžička - 15g)": {"kcal": 88, "protein": 3.8, "carbs": 3.0, "fats": 7.6, "fiber": 1.0},
    "Ľanové semiačka (lyžica - 10g)": {"kcal": 53, "protein": 1.8, "carbs": 2.9, "fats": 4.2, "fiber": 2.7},
    "Goji (lyžica - 10g)": {"kcal": 35, "protein": 1.4, "carbs": 7.7, "fats": 0.1, "fiber": 1.3},
    "Čučoriedky (hrsť - 50g)": {"kcal": 29, "protein": 0.4, "carbs": 7.2, "fats": 0.2, "fiber": 1.2},
    "Kreatín (5g)": {"kcal": 0, "protein": 0.0, "carbs": 0.0, "fats": 0.0, "fiber": 0.0},
    "Srvátkový proteín (odmerka - 30g)": {"kcal": 115, "protein": 25.0, "carbs": 2.0, "fats": 1.0, "fiber": 0.0},
    "Kváskový chlieb (krajec - 50g)": {"kcal": 130, "protein": 4.0, "carbs": 25.0, "fats": 1.0, "fiber": 3.0},
    "Vajíčko (1 ks - 50g)": {"kcal": 72, "protein": 6.3, "carbs": 0.4, "fats": 4.8, "fiber": 0.0},
    "Syr Gouda (plátok - 20g)": {"kcal": 71, "protein": 5.0, "carbs": 0.0, "fats": 5.5, "fiber": 0.0},
    "Fermentovaná zelenina (50g)": {"kcal": 15, "protein": 0.5, "carbs": 3.0, "fats": 0.1, "fiber": 1.5},
    "Kuracie prsia (100g)": {"kcal": 110, "protein": 23.0, "carbs": 0.0, "fats": 1.2, "fiber": 0.0},
    "Ryža (varená - 100g)": {"kcal": 130, "protein": 2.7, "carbs": 28.0, "fats": 0.3, "fiber": 0.4},
}

def calc_macros(ingredients_dict):
    # Live kalkulačka, ktorá sčítava makrá zo surovín
    totals = {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}
    for ing, qty in ingredients_dict.items():
        if ing in BASE_INGREDIENTS:
            for key in totals:
                totals[key] += BASE_INGREDIENTS[ing][key] * qty
    # Zaokrúhlenie pre čistý dizajn
    for key in totals:
        totals[key] = round(totals[key], 1)
    return totals

# --- KONFIGURÁCIA STRÁNKY ---
# ... existing code ...
```

---

### Krok 2: Nové ukladanie dát (Session State)
Vyhľadaj časť `# --- INICIALIZÁCIA DÁT (Session State) ---` a nahraď ju celú týmto blokom. Meniť budeme aj funkciu na pridanie jedla, a rovno k nej pridáme funkciu pre **odstránenie jedla (mazanie s odčítaním grafov)**.

```python:Zdrojový kód Streamlit aplikácie:app.py
# ... existing code ...
# --- INICIALIZÁCIA DÁT (Session State) ---
if 'consumed' not in st.session_state:
    st.session_state.consumed = {"kcal": 0, "protein": 0, "carbs": 0, "fats": 0, "fiber": 0}

if 'history' not in st.session_state:
    st.session_state.history = [] # Tu budeme ukladať históriu jedál

if 'ai_pending' not in st.session_state:
    st.session_state.ai_pending = None # Pamäť pre dvojkrokovú AI

if 'custom_foods' not in st.session_state:
    # Predvyplnená databáza tvojich jedál (teraz zložená z ingrediencií!)
    st.session_state.custom_foods = {
        "Moje štandardné raňajky": {
            "desc": "Základné ranné kombo",
            "ingredients": {
                "Vločky (lyžica - 10g)": 3.0,
                "Chia (lyžica - 10g)": 1.0,
                "Domáci jogurt (100g)": 1.5,
                "Banán (1 ks - 120g)": 1.0,
                "Arašidové maslo (lyžička - 15g)": 1.0,
                "Ľanové semiačka (lyžica - 10g)": 1.0,
                "Goji (lyžica - 10g)": 1.0,
                "Kreatín (5g)": 1.0,
                "Čučoriedky (hrsť - 50g)": 1.0
            }
        },
        "Potréningový Proteín (Snack)": {
            "desc": "Rýchla regenerácia po gyme",
            "ingredients": {
                "Srvátkový proteín (odmerka - 30g)": 1.0
            }
        },
        "Kváskový chlieb s vajíčkami (Večera)": {
            "desc": "Bielkoviny a zdravý mikrobióm",
            "ingredients": {
                "Kváskový chlieb (krajec - 50g)": 2.0,
                "Vajíčko (1 ks - 50g)": 2.0,
                "Syr Gouda (plátok - 20g)": 1.5,
                "Fermentovaná zelenina (50g)": 1.0
            }
        }
    }

def add_food_to_log(name, data, category):
    # Pridá hodnoty do celkových denných súčtov
    st.session_state.consumed["kcal"] += data["kcal"]
    st.session_state.consumed["protein"] += data["protein"]
    st.session_state.consumed["carbs"] += data["carbs"]
    st.session_state.consumed["fats"] += data["fats"]
    st.session_state.consumed["fiber"] += data["fiber"]
    
    # Zapíše jedlo do histórie (spolu so surovými dátami kvôli možnosti odčítať ich pri vymazaní)
    now = datetime.now().strftime("%H:%M")
    st.session_state.history.append({
        "id": str(uuid.uuid4()), # Unikátne ID pre presné mazanie
        "time": now,
        "name": name,
        "category": category,
        "raw_data": data,
        "macros": f"{data['kcal']} kcal | {data['protein']}g B | {data['carbs']}g S | {data['fats']}g T"
    })

def delete_food_from_log(item_id):
    # Nájde jedlo podľa ID a naživo odčíta jeho hodnoty z grafov
    for i, item in enumerate(st.session_state.history):
        if item["id"] == item_id:
            data = item["raw_data"]
            st.session_state.consumed["kcal"] = max(0, st.session_state.consumed["kcal"] - data["kcal"])
            st.session_state.consumed["protein"] = max(0, st.session_state.consumed["protein"] - data["protein"])
            st.session_state.consumed["carbs"] = max(0, st.session_state.consumed["carbs"] - data["carbs"])
            st.session_state.consumed["fats"] = max(0, st.session_state.consumed["fats"] - data["fats"])
            st.session_state.consumed["fiber"] = max(0, st.session_state.consumed["fiber"] - data["fiber"])
            del st.session_state.history[i]
            break

# --- VIZUALIZÁCIA (Budíky na ploche) ---
# ... existing code ...
```

---

### Krok 3: Úplne nové ovládanie - Karty a História
Nájdi v kóde riadok `# --- ZADÁVANIE JEDLA ---`. Všetko **od tohto miesta až po úplný koniec súboru** zmaž a nahraď týmto veľkým finálnym blokom. Zabezpečí to Live prepočítavanie pri úpravách surovín (Tab 4) a mazanie z histórie.

```python:Zdrojový kód Streamlit aplikácie:app.py
# ... existing code ...
# --- ZADÁVANIE JEDLA ---
st.subheader("🍽️ Pridať jedlo")

# Výber chodu (dôležité pre históriu)
meal_category = st.radio("Vyber chod:", ["Raňajky", "Obed", "Večera", "Snack"], horizontal=True)

# Taby pre výber zdroja
tab1, tab2, tab3, tab4 = st.tabs(["📚 Z mojich jedál", "✨ AI Zápisník", "➕ Vytvoriť prázdne", "⚙️ Správa a Suroviny"])

with tab1:
    st.write("**Vyber si z uložených jedál:**")
    selected_food = st.selectbox("Moje jedlá:", list(st.session_state.custom_foods.keys()))
    
    if selected_food:
        food_recipe = st.session_state.custom_foods[selected_food]
        food_data = calc_macros(food_recipe["ingredients"]) # Live výpočet zo surovín
        
        st.caption(f"📝 {food_recipe['desc']}")
        
        # Vypísanie surovín pre prehľad
        ing_text = ", ".join([f"{k} ({v}x)" for k, v in food_recipe["ingredients"].items()])
        st.write(f"🥣 **Obsahuje:** {ing_text}")
        
        st.write(f"📊 **{food_data['kcal']} kcal** | Bielkoviny: **{food_data['protein']}g** | Sacharidy: **{food_data['carbs']}g** | Tuky: **{food_data['fats']}g** | Vláknina: **{food_data['fiber']}g**")
        
        if st.button(f"➕ Pridať ako {meal_category}"):
            add_food_to_log(selected_food, food_data, meal_category)
            st.success(f"{selected_food} pridané!")
            st.rerun()

with tab2:
    st.write("**Napíš, čo si mala (AI to prepočíta):**")
    ai_input = st.text_input("Napr.: Na obed som mala kuracie prsia s ryžou a šalátom...")
    
    if st.button("✨ Zanalyzovať cez AI"):
        if ai_input:
            # Mockup AI - dočasné dáta kým nenapojíme reálne API
            mock_data = {"kcal": 550, "protein": 45, "carbs": 50, "fats": 15, "fiber": 5}
            st.session_state.ai_pending = {"name": f"AI: {ai_input[:20]}...", "data": mock_data}
        else:
            st.error("Najprv napíš jedlo do poľa vyššie.")
            
    # Zobrazenie výsledku AI PREDTÝM, ako sa uloží do denníka
    if st.session_state.ai_pending:
        p_data = st.session_state.ai_pending["data"]
        st.info(f"💡 **AI zistila tieto hodnoty:**\n\n**{p_data['kcal']} kcal** | {p_data['protein']}g Bielkoviny | {p_data['carbs']}g Sacharidy | {p_data['fats']}g Tuky | {p_data['fiber']}g Vláknina")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Potvrdiť a pridať do denníka"):
                add_food_to_log(st.session_state.ai_pending["name"], p_data, meal_category)
                st.session_state.ai_pending = None
                st.success("Pridané do denníka!")
                st.rerun()
        with col_b:
            if st.button("❌ Zrušiť"):
                st.session_state.ai_pending = None
                st.rerun()

with tab3:
    st.write("**Vytvor nové prázdne jedlo (Suroviny si naklikáš v záložke 'Správa'):**")
    with st.form("new_food_form"):
        new_name = st.text_input("Názov jedla (napr. Moje palacinky)")
        new_desc = st.text_input("Popis (voliteľné)")
        
        if st.form_submit_button("💾 Vytvoriť položku"):
            if new_name:
                st.session_state.custom_foods[new_name] = {
                    "desc": new_desc, 
                    "ingredients": {} # Prázdne ingrediencie, pridá si ich v editore
                }
                st.success(f"{new_name} vytvorené! Preklikni sa do 'Správa a Suroviny' a pridaj zloženie.")
            else:
                st.error("Jedlo musí mať názov.")

with tab4:
    st.write("**Úprava surovín v uložených jedlách (Prepočítava sa LIVE):**")
    edit_food = st.selectbox("Vyber jedlo, ktoré chceš upraviť:", list(st.session_state.custom_foods.keys()))
    
    if edit_food:
        food_recipe = st.session_state.custom_foods[edit_food]
        
        st.markdown(f"#### 🥣 Suroviny pre: {edit_food}")
        
        # Inicializácia dočasného stavu pre Live editor
        if 'edit_recipe' not in st.session_state or st.session_state.get('edit_name') != edit_food:
            st.session_state.edit_recipe = food_recipe["ingredients"].copy()
            st.session_state.edit_name = edit_food
            
        # Zobrazenie existujúcich ingrediencií pekne pod sebou
        for ing, qty in list(st.session_state.edit_recipe.items()):
            ec1, ec2, ec3 = st.columns([3, 1, 1])
            with ec1:
                st.markdown(f"**{ing}**")
            with ec2:
                # Callback funkcia, ktorá sa spustí vždy pri kliknutí na plus/mínus
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
        
        # Pridanie novej suroviny priamo do receptu
        st.markdown("---")
        add_col1, add_col2 = st.columns([3, 1])
        with add_col1:
            new_ing = st.selectbox("Nová surovina z databázy:", list(BASE_INGREDIENTS.keys()), label_visibility="collapsed")
        with add_col2:
            if st.button("➕ Pridať"):
                if new_ing not in st.session_state.edit_recipe:
                    st.session_state.edit_recipe[new_ing] = 1.0
                    st.rerun()

        # --- SMART ANALYZÁTOR JEDLA (Počíta z Live Editovaných dát) ---
        live_macros = calc_macros(st.session_state.edit_recipe)
        st.markdown("### 🧠 Smart Analýza")
        
        total_cal = live_macros['kcal']
        st.write(f"📊 Live výpočet: **{total_cal} kcal** | Bielk.: **{live_macros['protein']}g** | Sach.: **{live_macros['carbs']}g** | Tuky: **{live_macros['fats']}g** | Vlákn.: **{live_macros['fiber']}g**")
        
        if total_cal > 0:
            p_pct = (live_macros['protein'] * 4 / total_cal) * 100
            if p_pct < 20:
                st.warning(f"💡 **Tip na vylepšenie:** Málo bielkovín (len {p_pct:.0f}% kalórií). Pridaj si v políčkach vyššie surovinu bohatú na bielkoviny (napr. proteín).")
            elif p_pct > 35:
                st.success("💪 **Super!** Ideálne po tréningu, samé bielkoviny.")
            else:
                st.success("✅ Krásne vyvážené jedlo!")
        
        if st.button("💾 ULOŽIŤ UPRAVENÝ RECEPT", type="primary"):
            st.session_state.custom_foods[edit_food]["ingredients"] = st.session_state.edit_recipe.copy()
            st.success("Tento recept bol prepísaný a navždy uložený!")

st.divider()

# --- DNEŠNÝ PROGRES A GRAFY ---
# ... (Grafy a layout zostávajú nezmenené, odstránil som len kvôli dĺžke návodu, ale kód si ich odtiaľto načíta normálne)
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
    # Zoskupenie histórie podľa chodov (S pridaným tlačidlom na výmaz)
    categories = ["Raňajky", "Obed", "Večera", "Snack"]
    for cat in categories:
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
