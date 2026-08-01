def analyze_meal_to_recipe(meal_desc):
    prompt = f"""
    Zanalyzuj toto jedlo: "{meal_desc}". 
    Rozdeľ ho na jednotlivé suroviny. Pre každú surovinu odhadni kalórie (kcal) a makroživiny v gramoch (protein, carbs, fats, fiber) pre zadané množstvo.
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
    try:
        model = genai.GenerativeModel('gemini-3.5-flash')
        response = model.generate_content(prompt)
        # Očistenie odpovede, ak by AI pridala formátovacie značky
        txt = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(txt)
    except Exception as e:
        return None

with tab2:
    st.subheader("✨ AI Zápisník")
    st.write("Mala si niečo mimo svojich receptov? Napíš to sem a AI to rozoberie na drobné!")
    ai_meal = st.text_input("Napr.: '150g losos s hrstou ryže a šalátom'")
    
    if st.button("✨ Zanalyzovať jedlo"):
        if ai_meal:
            with st.spinner("AI analyzuje tvoje jedlo a suroviny..."):
                res = analyze_meal_to_recipe(ai_meal)
                if res and "ingredients" in res:
                    st.session_state.ai_last_meal = res
                    st.session_state.ai_last_meal_name = ai_meal
                else:
                    st.error("Chyba AI. Skús to preformulovať, alebo počkaj na limit.")
    
    if st.session_state.get("ai_last_meal"):
        res = st.session_state.ai_last_meal
        st.write("### 🥗 Výsledok analýzy (Rozložené na suroviny):")
        total_kcal = total_p = total_c = total_f = total_fib = 0
        
        # Zobrazenie každej suroviny zvlášť
        for item in res["ingredients"]:
            st.write(f"- **{item['name']}**: {item['kcal']} kcal (B: {item['protein']}g | S: {item['carbs']}g | T: {item['fats']}g | V: {item['fiber']}g)")
            total_kcal += item['kcal']
            total_p += item['protein']
            total_c += item['carbs']
            total_f += item['fats']
            total_fib += item['fiber']
            
        st.info(f"**Celé jedlo spolu:** {round(total_kcal,1)} kcal | B: {round(total_p,1)}g | S: {round(total_c,1)}g | T: {round(total_f,1)}g | V: {round(total_fib,1)}g")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Možnosť A: Len zjesť**")
            if st.button("🍽️ Pridať do dnešného denníka"):
                add_macros(total_kcal, total_p, total_c, total_f, total_fib)
                del st.session_state["ai_last_meal"]
                st.success("Pridané do tvojich dnešných budíkov!")
                time.sleep(1.5)
                st.rerun()
        with col2:
            st.write("**Možnosť B: Uložiť navždy**")
            new_recipe_name = st.text_input("Názov na uloženie (napr. Obed u mamy):")
            if st.button("💾 Uložiť ako nový recept do Moje jedlá"):
                if new_recipe_name:
                    new_ingredients = {}
                    for item in res["ingredients"]:
                        ing_name = item["name"]
                        # Uloženie presnej suroviny do databázy s hodnotami na danú porciu
                        st.session_state.ingredient_db[ing_name] = {
                            "kcal": item["kcal"], "protein": item["protein"],
                            "carbs": item["carbs"], "fats": item["fats"], "fiber": item["fiber"]
                        }
                        new_ingredients[ing_name] = 1.0 # Množstvo je 1.0, keďže hodnoty sú už prepočítané
                    
                    # Uloženie nového jedla s prepojením na tieto nové suroviny
                    st.session_state.custom_foods[new_recipe_name] = {
                        "desc": st.session_state.ai_last_meal_name,
                        "ingredients": new_ingredients
                    }
                    save_db()
                    del st.session_state["ai_last_meal"]
                    st.success(f"Recept '{new_recipe_name}' bol vytvorený! Nájdeš ho v Správe jedál.")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.warning("Najprv zadaj názov jedla pre uloženie.")

with tab3:
    st.subheader("➕ Vytvoriť nové jedlo")
    st.write("Vytvor si jedlo ručne, alebo rovno popíš zloženie a AI ti ho automaticky rozbije na suroviny a uloží!")
    
    new_name = st.text_input("Názov jedla (napr. 'Tofu so zeleninou'):")
    new_desc = st.text_area("Popis zloženia (napr. '150g tofu, 1 lyžica oleja, 200g brokolica'). Ak necháš prázdne, vytvorí sa prázdne jedlo.")
    
    if st.button("✨ Vytvoriť a Uložiť jedlo"):
        if new_name:
            if new_desc.strip(): # Ak si zadala nejaký text, spustíme AI
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
                        st.success(f"Jedlo '{new_name}' bolo kompletne zanalyzované a uložené! Prejdi do 'Správa a Suroviny'.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Nepodarilo sa zanalyzovať. Skús preformulovať text, alebo ho nechaj prázdny pre manuálne zadávanie.")
            else: # Ak text ostal prázdny, vytvoríme len čistú položku, tak ako to fungovalo doteraz
                st.session_state.custom_foods[new_name] = {"desc": "Bez popisu", "ingredients": {}}
                save_db()
                st.success(f"Prázdne jedlo '{new_name}' vytvorené! Prejdi do 'Správa a Suroviny' a vlož si tam suroviny ručne.")
                time.sleep(1.5)
                st.rerun()
        else:
            st.warning("Musíš zadať aspoň názov jedla (napríklad 'Môj obed').")

with tab4:
<!-- ... existing code ... -->
                new_name = ai_data["name"]
                st.session_state.ingredient_db[new_name] = {
                    "kcal": ai_data["kcal"], "protein": ai_data["protein"], 
                    "carbs": ai_data["carbs"], "fats": ai_data["fats"], "fiber": ai_data["fiber"]
                }
                st.session_state.edit_recipe[new_name] = 1.0
                save_db()
                st.success(f"{new_name} pridané do tvojej databázy aj do receptu!")
                time.sleep(1.5)
                st.rerun()

    live_macros = calc_macros(st.session_state.edit_recipe)
<!-- ... existing code ... -->
        else:
            st.success("✅ Krásne vyvážené jedlo!")
    
    if st.session_state.get("show_save_success"):
        st.success("Tento recept bol prepísaný a navždy uložený v databáze!")
        st.session_state.show_save_success = False

    if st.button("💾 ULOŽIŤ UPRAVENÝ RECEPT", type="primary"):
        st.session_state.custom_foods[edit_food]["ingredients"] = st.session_state.edit_recipe.copy()
        save_db()
        st.session_state.show_save_success = True
        st.rerun()

st.divider()
<!-- ... existing code ... -->
```

**Čo máš teraz urobiť:**
Vlož si tieto úpravy do svojho GitHubu. Keď si ich uložíš, aplikácia si priamo vedľa tvojho kódu sama vytvorí súbor `databaza.json`. 
Akonáhle si teraz zmeníš banán a klikneš na uložiť, na stotinu sekundy to preblikne (to je ten `st.rerun()`), vyhodí ti to zelenú správu a **nech sa preklikneš kamkoľvek, alebo appku úplne zavrieš, tvoje upravené raňajky ťa tam budú verne čakať.** 

Vyskúšaj to, či ti to už drží pamäť ako pribité!
