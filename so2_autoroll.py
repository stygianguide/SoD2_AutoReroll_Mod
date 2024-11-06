import pyautogui
import pytesseract
from PIL import Image, ImageOps  # Reemplaza cv2 con PIL
import time
import csv
import pygetwindow as gw
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
import os
import sys

# Attempt to set Tesseract path from common installation directories
for path in [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
    if os.path.isfile(path):
        pytesseract.pytesseract.tesseract_cmd = path
        print(f"[INFO] Tesseract found at: {path}")
        break
else:
    # If no valid path is found, display an error and exit
    print("[ERROR] Tesseract OCR not found. Please install Tesseract OCR.")
    print("You can download it from: https://github.com/UB-Mannheim/tesseract/wiki")
    sys.exit(1)

# Load trait power scores from CSV file
traits_power_scores = {}
try:
    with open('Traits_Power_Scores.csv', mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            trait_name = row['Name'].strip().lower()  # Adjust column names if needed
            trait_power = int(row['Power'])  # Ensure Power is an integer
            traits_power_scores[trait_name] = trait_power
except FileNotFoundError:
    print("[ERROR] Traits_Power_Scores.csv file not found. Ensure it's in the same directory as the script.")

def load_config():
    config = {
        "RUN_DURATION": 120,
        "REROLL_WAIT_TIME": 0.01,
        "SIMILARITY_THRESHOLD": 0.8,
        "POWER_THRESHOLD": 30,
        "DEBUG": False,
        "DEBUG_OCR": False,
        "PREFERRED_SKILLS": []  # Default list of preferred skills
    }
    
    if os.path.isfile("config.txt"):
        with open("config.txt", "r") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key in config:
                        if key == "DEBUG":
                            config[key] = value.lower() == "true"
                        elif key == "DEBUG_OCR":
                            config[key] = value.lower() == "true"
                        elif key == "PREFERRED_SKILLS":
                            # Split skills and replace "empty" with an empty string
                            skills = [skill.strip() if skill.strip().lower() != "empty" else "" for skill in value.split(",")]
                            # Only assign if there are skills specified, otherwise keep as empty list
                            if skills != [""]:
                                config[key] = skills
                        elif key in ["RUN_DURATION", "POWER_THRESHOLD"]:
                            config[key] = int(value)
                        elif key in ["REROLL_WAIT_TIME", "SIMILARITY_THRESHOLD"]:
                            config[key] = float(value)
                except ValueError:
                    print(f"[WARNING] Invalid value for '{key}': '{value}'. Using default: {config[key]}")
                except Exception as e:
                    print(f"[ERROR] Unexpected error reading '{key}': {e}. Using default: {config[key]}")
    # Convert RUN_DURATION from minutes to seconds
    config["RUN_DURATION"] *= 60
    return config

# Load configuration at the start
config = load_config()

# Use config values in the script
RUN_DURATION = config["RUN_DURATION"]
REROLL_WAIT_TIME = config["REROLL_WAIT_TIME"]
SIMILARITY_THRESHOLD = config["SIMILARITY_THRESHOLD"]
POWER_THRESHOLD = config["POWER_THRESHOLD"]
DEBUG = config["DEBUG"]
DEBUG_OCR = config["DEBUG_OCR"]
PREFERRED_SKILLS = config["PREFERRED_SKILLS"]

# Game window title
GAME_WINDOW_TITLE = "StateOfDecay2 "
SKILL_POWER = POWER_THRESHOLD / 2  # Additional power value for having a preferred skill

def debug_message(msg):
    if DEBUG:
        print(msg)

def get_game_window_position(title):
    try:
        # Encuentra la ventana con el título específico
        window = gw.getWindowsWithTitle(title)[0]  # Tomamos la primera coincidencia
        if DEBUG_OCR:
            screenshot = pyautogui.screenshot(region=(window.left, window.top, window.width, window.height))
            # Guarda la imagen con un nombre que incluya el índice del personaje o un identificador único
            unix_time = int(time.time())
            screenshot.save(f"debug_game_window_capture_{window.width}x{window.height}_{unix_time}.png")

        left, top, width, height = window.left, window.top, window.width, window.height
        return window, window.left, window.top, window.width, window.height
    except IndexError:
        raise Exception(f"Could not find window '{title}'.")


def calculate_dynamic_positions(width, height):
    skill_positions = [(int(288 / 1298 * width), int(700 / 1007 * height)),
                       (int(588 / 1298 * width), int(700 / 1007 * height)),
                       (int(878 / 1298 * width), int(700 / 1007 * height))]
    
    trait_positions = [(int(246 / 1298 * width), int(393 / 1007 * height)),
                       (int(543 / 1298 * width), int(393 / 1007 * height)),
                       (int(834 / 1298 * width), int(393 / 1007 * height))]
    
    skill_width = int(165 / 1298 * width)
    skill_height = int(25 / 1007 * height)
    trait_width = int(209 / 1298 * width)
    trait_height = int(75 / 1007 * height)

    return skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height


def capture_region(left, top, position, width, height):
    x, y = position
    region_x = left + x
    region_y = top + y
    screenshot = pyautogui.screenshot(region=(region_x, region_y, width, height))
    image = screenshot.convert('RGB')  # Convert to RGB for Pillow
    return image

def preprocess_image_for_ocr(image):
    # Convert to grayscale
    gray_image = ImageOps.grayscale(image)
    # Apply a binary threshold to make the text more distinct
    binary_image = gray_image.point(lambda p: p > 150 and 255)
    return binary_image


def extract_text(image):
    processed_image = preprocess_image_for_ocr(image)
    text = pytesseract.image_to_string(processed_image, config="--psm 6 -l eng -c tessedit_char_blacklist=.!@#$%^&*()[]{};:<>")
    return text.lower().strip()

def calculate_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def get_character_power(trait_text):
    ocr_traits = trait_text.splitlines()
    detected_traits = []
    power = 0

    # First, try an exact match
    for ocr_trait in ocr_traits:
        if ocr_trait in traits_power_scores:
            detected_traits.append(ocr_trait)
            power += traits_power_scores[ocr_trait]
        else:
            # If no exact match, look for an approximate match
            similar_trait = max(traits_power_scores.keys(), key=lambda trait: calculate_similarity(ocr_trait, trait))
            similarity = calculate_similarity(ocr_trait, similar_trait)
            if similarity >= SIMILARITY_THRESHOLD:
                detected_traits.append(similar_trait)
                power += traits_power_scores[similar_trait]
                debug_message(f"Approximate match: '{ocr_trait}' -> '{similar_trait}' (Similarity: {similarity:.2f})")
    debug_message(f"Traits from OCR: {ocr_traits}")
    debug_message(f"Detected Traits: {detected_traits}")
        
    return detected_traits, power

def reroll():
    pyautogui.press("t")
    time.sleep(REROLL_WAIT_TIME)  # Additional wait time for character to update after reroll
    debug_message("Rerolling...")

# List of all possible skills (ensuring lowercase for case-insensitive matching)
skill_list = [
    "chemistry", "computers", "cooking", "craftsmanship", "gardening", "mechanics", 
    "medicine", "utilities", "acting", "animal facts", "bartending", "business", 
    "comedy", "design", "driving", "excuses", "farting around", "fishing", "geek trivia", 
    "hairdressing", "hygiene", "ikebana", "law", "lichenology", "literature", 
    "making coffee", "movie trivia", "music", "painting", "people skills", 
    "pinball", "poker face", "political science", "recycling", "scrum certification", 
    "self-promotion", "sewing", "sexting", "shopping", "sleep psychology", 
    "sports trivia", "soundproofing", "tattoos", "tv trivia"
]

def clean_skill_text(text):
    # Cleans detected skill text by first trying an exact match, then by approximation
    text = text.strip().lower()

    # If the text is empty, immediately return an empty string
    if text == "":
        return ""

    # Attempt an exact match
    if text in skill_list:
        return text
    
    # Debug log when exact match fails
    debug_message(f"[DEBUG] Exact match failed for skill: '{text}'")
    
    # If no exact match, look for the closest skill in skill_list
    best_match = ""
    highest_similarity = 0
    
    for skill in skill_list:
        similarity = SequenceMatcher(None, text, skill).ratio()
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = skill
    
    # Return the closest match if it meets the similarity threshold; otherwise, return an empty string
    return best_match if highest_similarity >= SIMILARITY_THRESHOLD else ""

def analyze_character(left, top, index, skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height):
    # Capture images for traits and skills of a specific character
    skill_image = capture_region(left, top, skill_positions[index], skill_width, skill_height)
    trait_image = capture_region(left, top, trait_positions[index], trait_width, trait_height)

    with ThreadPoolExecutor() as executor:
        skill_text_future = executor.submit(extract_text, skill_image)
        trait_text_future = executor.submit(extract_text, trait_image)
        skill_text = clean_skill_text(skill_text_future.result())
        trait_text = trait_text_future.result()

    traits, power = get_character_power(trait_text)
    
    # Add SKILL_POWER if the skill is in PREFERRED_SKILLS
    if skill_text in PREFERRED_SKILLS:
        power += SKILL_POWER
        debug_message(f"Skill '{skill_text}' is in target skills, adding SKILL_POWER. Total Power: {power}")
    debug_message(f"S{index + 1}:, Power={power}, Skill='{skill_text}', Traits={traits}")

    return {'traits': traits, 'power': power, 'skill': skill_text}

def main():
    print("Starting... Select the game window.")
    time.sleep(2)

    # Get game window and its initial position
    game_window, left, top, width, height = get_game_window_position(GAME_WINDOW_TITLE)
    skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height = calculate_dynamic_positions(width, height)

    # Start initially at the first survivor
    current_position = 0
    pyautogui.press("right")
    
    # Initialize data for all three characters
    survivors = [analyze_character(left, top, i, skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height) for i in range(3)]
    reroll_history = []  # Store the last characters generated in the active slot

    start_time = time.time()
    while time.time() - start_time < RUN_DURATION:
    # Check if the game window is still active
        if not game_window.isActive:
            print("[ERROR] The game window is no longer active. Exiting script.")
            sys.exit(1)

        # Identify the character with the lowest power and reroll them
        weakest_index = min(range(3), key=lambda x: survivors[x].get('power', float('inf')))
        weakest_power = survivors[weakest_index]['power']

        # Stop if the lowest power character exceeds the threshold
        if weakest_power > POWER_THRESHOLD:
            debug_message(f"Stopping early as all characters have power above {POWER_THRESHOLD}.")
            break

        # Move to the position of the weakest character
        moves_needed = weakest_index - current_position
        if moves_needed != 0:
            reroll_history = []  # Clear reroll history when changing slots
            if moves_needed > 0:
                for _ in range(moves_needed):
                    pyautogui.press("right")
                current_position = weakest_index
            elif moves_needed < 0:
                for _ in range(-moves_needed):
                    pyautogui.press("left")
                current_position = weakest_index

        # Perform reroll and save character to history for final evaluation
        reroll()
        rerolled_character = analyze_character(left, top, weakest_index, skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height)
        
        # Add character to reroll history
        reroll_history.append(rerolled_character)

        # Explicitly block rerolls in the last second
        time_elapsed = time.time() - start_time
        if time_elapsed >= RUN_DURATION - 1:
            debug_message(f"-- Near End Explicit Lock: Evaluating Best Character from Last 2 Rerolls in Slot {weakest_index + 1}. No more rerolls will be done. --")
            # Use "r" up to two times to go back to the best character in reroll history (limit to 2 characters)
            if reroll_history:
                best_character = max(reroll_history, key=lambda x: x['power'])
                best_index = reroll_history.index(best_character)
                # Press "r" once if best character is the second in history, twice if it's the first
                for _ in range(2 - best_index):
                    pyautogui.press("r")
                    time.sleep(REROLL_WAIT_TIME)
                survivors[weakest_index] = best_character
            break

        # Keep only the last 2
        if len(reroll_history) > 2:
            reroll_history.pop(0)

        survivors[weakest_index] = rerolled_character

    # Display characters in the same order as in the game
    print("Final survivors:")
    for idx, survivor in enumerate(survivors, 1):
        print(f"S{idx}: Power='{survivor.get('power', 0)}', Skill={survivor.get('skill', '')}, Traits={survivor.get('traits', [])}")
    
    # Pause if DEBUG is True to keep console open
    if DEBUG:
        input("\n[DEBUG] Press Enter to exit...")
if __name__ == "__main__":
    main()
