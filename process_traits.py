import os
import re
import json
import requests
from bs4 import BeautifulSoup
from play_style_configs import play_style_configs
from skills_effects import skills_effects
from legacy_traits_power_scores import legacy_traits_power_scores
import math

DEBUG = False

# ------------------------- Parsing Helpers -------------------------

# ------------------------- CATEGORY_CONDITIONS -------------------------
CATEGORY_CONDITIONS = [
    # Food category conditions
    (["food consumed overall", "food consumed per day", "max food storage"], "food", .1),
    (["food per day", "sometimes wastes food"], "food", 1),

    # Ammo category conditions
    (["category_ammo"], "ammo", 1),
    (["ammo per day", "sometimes wastes ammo", "sometimes waster ammo"], "ammo", 1),
    (["max ammo storage"], "ammo", 0.1),

    # Fuel category conditions
    (["fuel efficiency", "fuel storage"], "fuel", 0.1),
    (["fuel per day", "sometimes wastes fuel"], "fuel", 1),

    #Vehicle category conditions
    (["category_vehicle"], "vehicle", 1),
    (["vehicle endurance", "vehicle stealth"], "vehicle", 0.1),


    # Materials category conditions
    (["materials storage"], "materials", 0.1),
    (["materials per day", "sometimes wastes materials"], "materials", 1),

    # Parts category conditions
    (["parts salvaged", "parts per day"], "parts", 0.1),

    # Medicine category conditions
    (["category_medicine"], "medicine", 1),
    (["meds storage"], "medicine", 0.1),
    (["infirmary", "meds per day", "sometimes wastes medicine"], "medicine", 1),

    # Training category conditions
    (["experience rate", "xp rate", "experience"], "training", 0.1),

    # Morale category conditions
    (["keep their morale at", "can become frustrated at", "morale without frustration"], "morale", 0.2),
    (["morale bonus from"], "morale", 0.4),
    (["morale (community)"], "morale", 2),
    (["beds"], "morale", 3.5),
    (["avoids getting into conflicts", "often the target when conflicts occur", "easiliy frustrated"], "morale", 2),
    (["morale"], "morale", 1),

    # Melee category conditions
    (["durability loss per hit (melee)"], "melee", 0.1),
    (["category_melee"], "melee", 1),

    # Guns category conditions
    (["durability loss per shot (guns)"], "guns", 0.1),
    (["category_guns"], "guns", 1),

    
    # Infection category conditions
    (["-100% plague infection"], "infection", 0.3),
    (["infection"], "infection", 0.1),

    # Health category conditions
    (["max health (community)"], "health", 0.2),
    (["injury chance"], "health", 0.2),
    (["resting trauma & hp recovery"], "health", 0.1),
    (["health", "injury severity", "healing item efficacy"], "health", 0.1),

    # Stamina category conditions
    (["stamina", "fatigue severity"], "stamina", 0.1),
    (["max stamina (community)"], "stamina", 0.2),

    # Carrying Capacity category conditions
    (["max carrying capacity", "carry capacity", "compact ordnance(+1 max consumable stack)"], "carrying_capacity", .1),
    (["light carrying capacity"], "carrying_capacity", 0.1),
    (["+1 max item stack", "+1 inventory slot"], "carrying_capacity", 1),

    # Standing Rewards category conditions
    (["standing rewards", "standing reward"], "standing_rewards", 0.1),

    # Stealth category conditions
    (["unlocks rooftop recon"], "stealth", 1),
    (["category_stealth"], "stealth", 1),
    (["enemy sight range", "enemy detection range"], "stealth", 1),

    # Radio Usage category conditions
    (["radio cooldowns"], "radio_usage", 0.1),
    (["(unlocks "], "radio_usage", 5),

    # Influence category conditions
    (["influence"], "influence", 0.1),

    # Noise category conditions
    (["noise"], "noise", 1),

    # Labor category conditions
    (["action speed", "facility action speed"], "labor", 0.1),
    (["labor"], "labor", 1),
]

# List of all the fifth skills in the game
FIFTH_SKILLS_LIST = [
    "empty", "chemistry", "computers", "cooking", "craftsmanship", "gardening", "mechanics", 
    "medicine", "utilities", "acting", "animal facts", "bartending", "business", 
    "comedy", "design", "driving", "excuses", "farting around", "fishing", "geek trivia", 
    "hairdressing", "hygiene", "ikebana", "law", "lichenology", "literature", 
    "making coffee", "movie trivia", "music", "painting", "people skills", 
    "pinball", "poker face", "political science", "recycling", "scrum certification", 
    "self-promotion", "sewing", "sexting", "shopping", "sleep psychology", 
    "sports trivia", "soundproofing", "tattoos", "tv trivia"
]

def assign_category(effect_text: str):
    full_text = effect_text.lower()
    for condition in CATEGORY_CONDITIONS:
        if len(condition) == 3:
            terms, category, multiplier = condition
        else:
            terms, category = condition
            multiplier = 1
        if any(term in full_text for term in terms):
            return category, multiplier
    print(f"Category not found for: {effect_text}")
    return "unknown", 1

def extract_value(effect_text: str):
    match = re.search(r"([+-]?\d+)", effect_text)
    if match:
        return abs(int(match.group(1)))
    return None

def parse_effects_from_list(effects):
    result = {}
    for effect_text in effects:
        effect_text = effect_text.strip()
        if not effect_text or effect_text.lower().startswith("none"):
            continue
        category, multiplier = assign_category(effect_text)
        value = extract_value(effect_text)
        if value is None:
            value = 1
        value = floor1(value * multiplier)
        # Warn if the value is too high or too low
        if value > 10:
            print(f"Value too high: {effect_text} - ({category}:{value})")
        elif value < 1 and category not in ["morale", "health", "stamina", "carrying_capacity"]:
            print(f"Value too low: {effect_text} - ({category}:{value})")
        result[effect_text] = {category: value}
    return result

def parse_skills_from_list(skills_list):
    skills = {}
    pattern = re.compile(r'^(.*?)\s*\(max\s*(\d+)\s*level(?:s)?\)\s*$', re.IGNORECASE)
    for line in skills_list:
        original_line = line.strip()
        if not original_line:
            continue
        match = pattern.match(original_line)
        if match:
            # Extract the training value from the max levels
            max_levels = int(match.group(2))
            training_value = abs(max_levels - 14)
            # Use the original line as key
            skills[original_line] = {"training": training_value}
        else:    
            skills[original_line] = {"provided_skills": [original_line]}
            if skills_effects.get(original_line):
                for effect in parse_effects_from_list(skills_effects[original_line]).values():
                        for key, value in effect.items():
                            skills[original_line][key] = skills[original_line].get(key, 0) + value
    return skills

def format_value(value: str):
    """Converts HTML content into a list of formatted strings."""
    soup = BeautifulSoup(value, "html.parser")
    ul = soup.find("ul")
    if ul:
        items = [" ".join(li.get_text(strip=True).lower().split()) for li in ul.find_all("li") if li.get_text(strip=True)]
        return items
    text = " ".join(soup.get_text().lower().split())
    return [text] if text else []

def clean_string(s: str):
    return s.strip()

def write_to_file(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        for item in sorted(set(data)):
            if item:
                f.write(item + '\n')
    print(f'File {filename} written successfully!')

# ------------------------- Trait Processing -------------------------

def add_effect(effects, key, value):
    effects[key] = floor1(effects.get(key, 0) + value)

def floor1(num: float) -> float:
    """Rounds down keeping one decimal place."""
    return math.floor(num * 10) / 10

def process_mapping(effects, mapping, source, raw):
    for prop, value in mapping.items():
        if not isinstance(value, (int, float)):
            continue
        if source == "hero":
            if prop not in ["ammo", "food", "medicine", "fuel", "materials", "parts", "labor"]:
                cont = floor1(abs(value) * 2)
            else:
                cont = floor1(abs(value))
            add_effect(effects, prop, cont)
            raw["positive"] = floor1(raw["positive"] + cont)
        elif source == "skills":
            if prop == "training":
                cont = floor1(-value)
                add_effect(effects, prop, cont)
                raw["negative"] = floor1(raw["negative"] + value)
            else:
                cont = floor1(value)
                add_effect(effects, prop, cont)
                raw["positive"] = floor1(raw["positive"] + cont)
        elif source == "positive":
            cont = floor1(abs(value))
            add_effect(effects, prop, cont)
            raw["positive"] = floor1(raw["positive"] + cont)
        elif source == "negative":
            cont = floor1(-abs(value))
            add_effect(effects, prop, cont)
            raw["negative"] = floor1(raw["negative"] + abs(value))

def compile_trait(trait, hero_map, negative_map, positive_map, skills_map):
    effects = {}
    raw = {"positive": 0, "negative": 0}

    # Process hero bonus
    for hero_effect in trait.get("provided hero bonus", []):
        if hero_effect == "none":
            continue
        if hero_effect not in hero_map:
            print(f"Hero bonus not found: {hero_effect}")
            continue
        process_mapping(effects, hero_map[hero_effect], "hero", raw)

    # Process skills
    provided_skills = []
    for skill_effect in trait.get("provided skill(s)", []):
        if skill_effect not in skills_map:
            print(f"Skill not found: {skill_effect}")
            continue
        process_mapping(effects, skills_map[skill_effect], "skills", raw)
        if skills_map[skill_effect].get("provided_skills"):
            provided_skills.extend(skills_map[skill_effect]["provided_skills"])

    if provided_skills:
        effects["provided_skills"] = provided_skills
    # Process negative effects
    for neg_effect in trait.get("negative effect(s)", []):
        process_mapping(effects, negative_map[neg_effect], "negative", raw)

    # Process positive effects
    for pos_effect in trait.get("positive effect(s)", []):
        process_mapping(effects, positive_map[pos_effect], "positive", raw)

    effects["positive"] = raw["positive"]
    effects["negative"] = raw["negative"]

    return effects

# ------------------------- HTML Handling -------------------------

def load_cached_page(cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            content = f.read()
        print("HTML page loaded from cache.")
        return content
    return None

def download_page(url, cache_file):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error downloading page. Status code: {response.status_code}")
        return None
    content = response.content
    with open(cache_file, 'wb') as f:
        f.write(content)
    print("HTML page downloaded and saved to cache.")
    return content

def get_html_content():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cache_file = os.path.join(current_dir, 'cached_page.html')
    content = load_cached_page(cache_file)
    if content is None:
        url = "https://state-of-decay-2.fandom.com/wiki/Traits"
        content = download_page(url, cache_file)
    return content

# ------------------------- Table Parsing -------------------------

def get_table(soup: BeautifulSoup):
    table = soup.find("table")
    if not table:
        print("No table found on the page.")
    return table

def parse_headers(table):
    header_row = table.find("tr")
    headers = [" ".join(th.get_text(strip=True).split()) for th in header_row.find_all("th")]
    if not headers:
        print("No headers found in the table.")
    return headers

def get_column_indices(headers, desired_columns):
    col_indices = {}
    for col in desired_columns:
        if col in headers:
            col_indices[col] = headers.index(col)
        else:
            print(f"Column not found: {col}")
    return col_indices

def parse_traits(table, col_indices):
    traits = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < len(col_indices):
            continue  # skip incomplete rows
        row_data = {}
        for col, idx in col_indices.items():
            raw_value = cells[idx].decode_contents() if idx < len(cells) else ""
            row_data[col.lower()] = format_value(raw_value)
        traits.append(row_data)
    return traits

# ------------------------- Output Helpers -------------------------

def save_json(data, filename, description=""):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    if description:
        print(f"{description} saved in {filename}")

# ------------------------- Main Process -------------------------

def calc_game_mode_score(trait_data, priorities, mode):
    """
    Calcula el score para un modo de juego dado usando los datos de trait_data y prioridades.
    Para cada categoría definida en prioridades se utiliza el valor de trait_data; si no existe,
    se aplica el peso por defecto.
    """
    score = 0
    if mode == "minmaxer":
        return 0
    elif mode == "prodigy":
        not_fifth_skills = [
            skill for skill in trait_data.get("provided_skills", [])
            if skill not in FIFTH_SKILLS_LIST
        ]
        score += len(not_fifth_skills) * 7

    default_value = priorities.get("default", 0)
    for category, value in trait_data.items():
        if category == "provided_skills":
            continue
        weight = priorities.get(category, default_value)
        score += floor1(value * weight)
    return floor1(score)

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cleaned_file = os.path.join(current_dir, 'cleaned_traits.jsonl')

    if os.path.exists(cleaned_file):
        traits = []
        with open(cleaned_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    traits.append(json.loads(line))
                except Exception as e:
                    print(f"Error loading the line: {line} - {e}")
        print(f"Read from {cleaned_file}")
    else:
        content = get_html_content()
        if not content:
            return

        soup = BeautifulSoup(content, "html.parser")
        table = get_table(soup)
        if not table:
            return

        headers = parse_headers(table)
        desired_columns = [
            "Name", 
            "Positive Effect(s)", 
            "Negative Effect(s)", 
            "Provided Skill(s)", 
            "Provided Hero Bonus"
        ]
        col_indices = get_column_indices(headers, desired_columns)
        traits = parse_traits(table, col_indices)

    # add the extra traits from the file extra_traits.jsonl

    # add the extra traits from the file extra_traits.jsonl
    extra_traits_file = os.path.join(current_dir, 'extra_traits.jsonl')
    if os.path.exists(extra_traits_file):
        with open(extra_traits_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    extra_trait = json.loads(line)
                    traits.append(extra_trait)
                    print(f"Added extra trait: {extra_trait.get('name', ['unnamed'])[0]}")
                except Exception as e:
                    print(f"Error loading extra trait: {line} - {e}")
        print(f"Extra traits loaded from {extra_traits_file}")
    else:
        print(f"No extra traits file found at {extra_traits_file}")

    traits_dir = current_dir
    output_folder = os.path.join(traits_dir, 'output')
    os.makedirs(traits_dir, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    if DEBUG:
        output_cleaned_file = os.path.join(traits_dir, 'cleaned_traits.jsonl')
        with open(output_cleaned_file, 'w', encoding='utf-8') as outfile:
            for trait in traits:
                json.dump(trait, outfile, ensure_ascii=False)
                outfile.write('\n')
        print(f"File {output_cleaned_file} written successfully!")

    # Separate lists for effects and skills
    negative_effects = []
    positive_effects = []
    provided_hero_bonus = []
    provided_skills = []

    for trait in traits:
        if trait.get("negative effect(s)"):
            negative_effects.extend(trait["negative effect(s)"])
        if trait.get("positive effect(s)"):
            positive_effects.extend(trait["positive effect(s)"])
        if trait.get("provided hero bonus"):
            provided_hero_bonus.extend(trait["provided hero bonus"])
        if trait.get("provided skill(s)"):
            provided_skills.extend(trait["provided skill(s)"])

    # Parsing of effects and skills
    negative_json = parse_effects_from_list(negative_effects)
    positive_json = parse_effects_from_list(positive_effects)
    hero_json = parse_effects_from_list(provided_hero_bonus)
    skills_json = parse_skills_from_list(provided_skills)

    if DEBUG:
        save_json(negative_json, os.path.join(output_folder, 'negative.json'), "Negative effects")
        save_json(positive_json, os.path.join(output_folder, 'positive.json'), "Positive effects")
        save_json(hero_json, os.path.join(output_folder, 'hero.json'), "Hero bonus")
        save_json(skills_json, os.path.join(output_folder, 'skills.json'), "Skills")

    # Compilation of traits
    compiled = {}
    for trait in traits:
        name_list = trait.get("name", [])
        name = name_list[0].strip() if name_list else ""
        if not name:
            continue
        compiled[name] = compile_trait(trait, hero_json, negative_json, positive_json, skills_json)

    # Each trait is reorganized into two keys: "original" and "styles", grouping variants by base name.
    grouped_compiled = {}
    for full_name, data in compiled.items():
        # Detect variant if the name ends with " <letter>"
        if len(full_name) > 2 and full_name[-2] == " " and full_name[-1].isalpha():
            base_name = full_name[:-2]
        else:
            base_name = full_name
        grouped_compiled.setdefault(base_name, []).append((full_name, data))

    integrated_traits = {}
    for base_name, variants in grouped_compiled.items():
        if len(variants) == 1:
            selected_name, selected_data = variants[0]
        else:
            worst_variant = None
            worst_total = None
            # Calculates the total scores in all styles for each variant
            for variant_name, comp_data in variants:
                total = 0
                for mode, priorities in play_style_configs.items():
                    total += calc_game_mode_score(comp_data, priorities, mode)
                if worst_total is None or total < worst_total:
                    worst_total = total
                    worst_variant = (variant_name, comp_data)
            selected_name, selected_data = worst_variant
            if DEBUG:
                print(f"[DEBUG] Merged variants for '{base_name}': selected variant '{selected_name}' with total score {worst_total}")
        
        # Compute intersection of provided skills among all variants with skills
        all_have_skills = all("provided_skills" in data and data["provided_skills"] for _, data in variants)
        
        common_skills = None
        if all_have_skills:
            # Only compute intersection if all variants have skills
            for _, comp_data in variants:
                skills = set(comp_data["provided_skills"])
                if common_skills is None:
                    common_skills = skills
                else:
                    common_skills &= skills

            # Update when all variants have the same skills
            if common_skills and len(common_skills) > 0:
                selected_data["provided_skills"] = list(common_skills)
            else:
                selected_data["provided_skills"] = []
        else:
            selected_data["provided_skills"] = []
        
        if selected_data["provided_skills"] == []:
            selected_data.pop("provided_skills")

        styles = {}
        for mode, priorities in play_style_configs.items():
            if mode == "legacy":
                continue
            styles[mode] = calc_game_mode_score(selected_data, priorities, mode)

        # Add legacy power score
        styles["legacy"] = legacy_traits_power_scores.get(base_name, 0)

        integrated_traits[base_name] = {
            "categories": selected_data,
            "styles": styles
        }

        

    # Save the result as a Python module for easy import
    compiled_out = os.path.join(traits_dir, 'compiled_traits.py')
    with open(compiled_out, 'w', encoding='utf-8') as f:
        f.write("compiled_traits = " + json.dumps(integrated_traits, indent=4, ensure_ascii=False))
    print(f"Compiled traits with styles saved as module in {compiled_out}")

    # Save the result as a JavaScript module for easy import
    compiled_js_out = os.path.join(traits_dir, 'compiled_traits.js')
    with open(compiled_js_out, 'w', encoding='utf-8') as f:
        f.write("var compiled_traits = " + json.dumps(integrated_traits, indent=4, ensure_ascii=False) + ";\n")
    print(f"Compiled traits with styles saved as module in {compiled_js_out}")

if __name__ == "__main__":
    main()