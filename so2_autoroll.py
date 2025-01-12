import pyautogui
import pytesseract
from PIL import ImageDraw
import time
import csv
import pygetwindow as gw
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import keyboard
import tkinter as tk
from tkinter import ttk
import ctypes

# Set the path to the local tesseract executable
pytesseract.pytesseract.tesseract_cmd = os.path.join(os.path.dirname(__file__), 'tesseract', 'tesseract.exe')

# Load trait power scores from CSV file
traits_power_scores = {}
try:
    # Adjust the path to work with PyInstaller
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_path, 'Traits_Power_Scores.csv')
    with open(csv_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            trait_name = row['Name'].strip().lower()
            trait_power = int(row['Power'])
            traits_power_scores[trait_name] = trait_power
except FileNotFoundError:
    print("[ERROR] Traits_Power_Scores.csv file not found. Ensure it's in the same directory as the script.")

# List of all possible skills (ensuring lowercase for case-insensitive matching)
SKILLS_LIST = [
    "empty", "chemistry", "computers", "cooking", "craftsmanship", "gardening", "mechanics", 
    "medicine", "utilities", "acting", "animal facts", "bartending", "business", 
    "comedy", "design", "driving", "excuses", "farting around", "fishing", "geek trivia", 
    "hairdressing", "hygiene", "ikebana", "law", "lichenology", "literature", 
    "making coffee", "movie trivia", "music", "painting", "people skills", 
    "pinball", "poker face", "political science", "recycling", "scrum certification", 
    "self-promotion", "sewing", "sexting", "shopping", "sleep psychology", 
    "sports trivia", "soundproofing", "tattoos", "tv trivia"
]

class Config:
    def __init__(self):
        self.RUN_DURATION = 2
        self.REROLL_WAIT_TIME = 0.01
        self.SIMILARITY_THRESHOLD = 0.8
        self.POWER_THRESHOLD = 25
        self.SKILL_POWER = 10
        self.DEBUG = False
        self.DEBUG_OCR = False
        self.PREFERRED_SKILLS = []

    def __str__(self):
        return str(self.__dict__)

def load_config():
    config = Config()
    
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
                    
                    if hasattr(config, key):
                        if key in ["DEBUG", "DEBUG_OCR"]:
                            setattr(config, key, value.lower() == "true")
                        elif key == "PREFERRED_SKILLS":
                            skills = [skill.strip().lower() for skill in value.split(",") if skill.strip() and skill.strip().lower() != ""]
                            # Filter based on SKILLS_LIST
                            filtered_skills = [skill for skill in skills if skill in SKILLS_LIST]
                            setattr(config, key, filtered_skills)
                        elif key in ["POWER_THRESHOLD", "SKILL_POWER", "RUN_DURATION"]:
                            setattr(config, key, int(value))
                        elif key == "REROLL_WAIT_TIME" or key == "SIMILARITY_THRESHOLD":
                            setattr(config, key, float(value))
                except ValueError:
                    continue

    if config.DEBUG:
        print(f"Loaded configuration: {config}")
        if not config.PREFERRED_SKILLS:
            print(f"Skipping skill analysis as there are no preferred skills")
    return config

# Load configuration at the start
config = load_config()

# Game window title
GAME_WINDOW_TITLE = "StateOfDecay2 "

# Window selected global flag
window_selected = False

# Variable de control global para cancelar el proceso
cancel_process_flag = False

def cancel_process():
    global cancel_process_flag
    cancel_process_flag = True
    print("[INFO] Process cancel has been requested.")
    status_label.config(text="Process cancel has been requested.")

def debug_message(msg):
    if config.DEBUG:
        print(msg)

def debug_image(image, msg):
    if config.DEBUG_OCR:
        # Save the image with a timestamp
        unix_time = int(time.time())
        image.save(f"{msg}_{unix_time}.png")

def debug_image_with_boxes(image, skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height, msg):
    draw = ImageDraw.Draw(image)
    for pos in skill_positions:
        x, y = pos
        draw.rectangle([x, y, x + skill_width, y + skill_height], outline="red", width=2)
    for pos in trait_positions:
        x, y = pos
        draw.rectangle([x, y, x + trait_width, y + trait_height], outline="blue", width=2)
    unix_time = int(time.time())
    image.save(f"{msg}_{unix_time}.png")
    print(f"[DEBUG] Image with boxes saved as {msg}_{unix_time}.png")

def get_game_window_position(title):
    try:
        # Find the game window by title
        window = gw.getWindowsWithTitle(title)[0]  # Take the first window if there are multiple
        if config.DEBUG_OCR:
            screenshot = pyautogui.screenshot(region=(window.left, window.top, window.width, window.height))
            debug_image(screenshot, f"debug_game_window_capture_{window.width}x{window.height}")

        left, top, width, height = window.left, window.top, window.width, window.height
        return window, window.left, window.top, window.width, window.height
    except IndexError:
        print(f"Could not find window '{title}'.")
        status_label.config(text="Could not find the game window. Prepare the game window and click 'Run' again.")
    
def get_aspect_ratio_category(width, height):
    aspect_ratio = width / height
    debug_message(f"width:{width} height:{height}")
    if 1.5 <= aspect_ratio <= 1.85:  # Expand the range for 16:9 and similar wide ratios
        return "16:9"
    elif 1.25 <= aspect_ratio <= 1.4:  # Expand the range for 4:3 and similar ratios
        return "4:3"
    else:
        return "unknown"

def calculate_dynamic_positions(width, height):
    # Define reference resolutions
    ref_width = 1298
    ref_height_16_9 = 767
    ref_height_4_3 = 1007

    # Determine aspect ratio category
    aspect_category = get_aspect_ratio_category(width, height)
    debug_message(f"Aspect ratio detected '{aspect_category}'.")

    # Helper function to scale positions based on reference dimensions
    def get_scaled_positions(reference_positions, ref_width, ref_height):
        return [(int(x / ref_width * width), int(y / ref_height * height)) for x, y in reference_positions]

    # Define positions and dimensions for each aspect ratio
    if aspect_category == "16:9":
        skill_positions_ref = [(292, 580), (588, 580), (879, 580)]
        trait_positions_ref = [(246, 273), (542, 273), (834, 273)]
        skill_width = int(163 / ref_width * width)
        skill_height = int(24 / ref_height_16_9 * height)
        trait_width = int(209 / ref_width * width)
        trait_height = int(76 / ref_height_16_9 * height)
        ref_height = ref_height_16_9  # Use 16:9 reference height
    elif aspect_category == "4:3":
        skill_positions_ref = [(288, 700), (588, 700), (878, 700)]
        trait_positions_ref = [(246, 393), (543, 393), (834, 393)]
        skill_width = int(165 / ref_width * width)
        skill_height = int(25 / ref_height_4_3 * height)
        trait_width = int(209 / ref_width * width)
        trait_height = int(75 / ref_height_4_3 * height)
        ref_height = ref_height_4_3  # Use 4:3 reference height
    else:
        raise Exception("Unsupported aspect ratio")

    # Scale positions based on the selected aspect ratio
    skill_positions = get_scaled_positions(skill_positions_ref, ref_width, ref_height)
    trait_positions = get_scaled_positions(trait_positions_ref, ref_width, ref_height)

    return skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height


def capture_region(left, top, position, width, height):
    x, y = position
    region_x = left + x
    region_y = top + y
    screenshot = pyautogui.screenshot(region=(region_x, region_y, width, height))
    image = screenshot.convert('RGB')  # Convert to RGB for Pillow
    return image

def extract_text(processed_image):
    text = pytesseract.image_to_string(processed_image, config="--psm 6 -l eng -c tessedit_char_blacklist=.!@#$%^&*()[]{};:<>")
    text = text.strip()
    # Guardar la imagen si el texto extraído está vacío
    if config.DEBUG_OCR and  not text:
        debug_image(processed_image, "empty_processed_image")
        debug_message("[DEBUG] Processed image text is empty, saved image as 'empty_processed_image'")
    
    return text.lower()

def calculate_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def get_character_power(ocr_traits):
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
            if similarity >= config.SIMILARITY_THRESHOLD:
                detected_traits.append(similar_trait)
                power += traits_power_scores[similar_trait]
                debug_message(f"Approximate match: '{ocr_trait}' -> '{similar_trait}' (Similarity: {similarity:.2f})")
    if config.DEBUG_OCR:
        debug_message(f"Traits from OCR: {ocr_traits}")
    debug_message(f"Detected Traits: {detected_traits}")
        
    return detected_traits, power

def reroll():
    pyautogui.press("t")
    time.sleep(config.REROLL_WAIT_TIME)  # Additional wait time for character to update after reroll
    debug_message("Rerolling...")

def remove_non_letters(text):
    """Remove all non-letter characters from the text."""
    return ''.join([char for char in text if char.isalpha() or char.isspace()])

def remove_single_letters(text):
    """Remove single letters at the end of the text."""
    words = text.split()
    return ' '.join([word for word in words if len(word) > 1])

def clean_ocr_text(text):
    """Clean and process the OCR text."""
    text = remove_non_letters(text)
    text = remove_single_letters(text)
    return text.strip().lower()


def clean_skill_text(text, config):
    """Clean and process the skill text, trying exact match first, then similarity."""
    text = clean_ocr_text(text)

    # If the text is empty, immediately return an empty skill
    if text == "":
        return "empty"

    # Attempt an exact match
    if text in SKILLS_LIST:
        return text
    
    # Debug log when exact match fails
    if config.DEBUG:
        debug_message(f"[DEBUG] Exact match failed for skill: '{text}'")
    
    # If no exact match, look for the closest skill in SKILLS_LIST
    best_match = ""
    highest_similarity = 0
    
    for skill in SKILLS_LIST:
        similarity = SequenceMatcher(None, text, skill).ratio()
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = skill
    
    # Return the closest match if it meets the similarity threshold; otherwise, return an empty string
    return best_match if highest_similarity >= config.SIMILARITY_THRESHOLD else ""


def analyze_skills(skill_image, config):
    """Analyze skills from the skill image."""
    skill_text = extract_text(skill_image)
    return clean_skill_text(skill_text, config)

def analyze_traits(trait_image, config):
    """Analyze traits and power from the trait image."""
    trait_text = extract_text(trait_image)
    
    # Save the image if the text is empty
    if not trait_text.strip():
        debug_image(trait_image, "empty_trait_image")
        if config.DEBUG_OCR:
            debug_message("[DEBUG] Trait image text is empty, saved image")
    
    lines = trait_text.splitlines()
    cleaned_lines = [clean_ocr_text(line) for line in lines]
    traits, power = get_character_power(cleaned_lines)
    return traits, power

def analyze_character(left, top, index, skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height, config):
    futures = []
    with ThreadPoolExecutor() as executor:
        # Capture image for traits
        trait_image = capture_region(left, top, trait_positions[index], trait_width, trait_height)
        futures.append(executor.submit(analyze_traits, trait_image, config))

        # Capture image for skills only if there are preferred skills
        if config.PREFERRED_SKILLS:
            skill_image = capture_region(left, top, skill_positions[index], skill_width, skill_height)
            futures.append(executor.submit(analyze_skills, skill_image, config))

        results = [future.result() for future in futures]

    if config.PREFERRED_SKILLS:
        skill_text = results[1]
        traits, power = results[0]
    else:
        skill_text = ""
        traits, power = results[0]

    # Create the result dictionary
    result = {
        "power": power,
        "traits": traits
    }

    if config.PREFERRED_SKILLS:
        result["skill"] = skill_text
            # Add SKILL_POWER if the skill is in PREFERRED_SKILLS
        if  skill_text in config.PREFERRED_SKILLS:
            result["skill_power"] = config.SKILL_POWER
            debug_message(f"Skill '{skill_text}' is in target skills, adding SKILL_POWER: {config.SKILL_POWER}.")

    # Debug log for the analyzed character
    debug_message(f"S{index + 1}: {result}")

    return result

def move_cursor_below_traits_square(left, top, trait_position, trait_width, trait_height):
    """Move the cursor to 20 pixels below the center of the traits square."""
    x, y = trait_position
    center_x = left + x + trait_width // 2
    center_y = top + y + trait_height + 20  # Move 20 pixels below the traits square
    pyautogui.moveTo(center_x, center_y)

def start_roll():
    global window_selected, cancel_process_flag
    if not window_selected:
        status_label.config(text="Starting... Select the game window.")
        print("Starting... Select the game window.")
        time.sleep(2)
        window_selected = True
    print("Rolling the characters...")

    # Get game window and its initial position
    game_window, left, top, width, height = get_game_window_position(GAME_WINDOW_TITLE)
    skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height = calculate_dynamic_positions(width, height)

    if config.DEBUG_OCR:
         # Capture initial screenshot and draw boxes for verification
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        print(f"skill_positions: {skill_positions}")
        print(f"trait_positions: {trait_positions}")
        debug_image_with_boxes(screenshot, skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height, f"debug_game_window_capture_{width}x{height}")


    # Start initially at the first survivor by moving the cursor to the traits square
    current_position = 0
    move_cursor_below_traits_square(left, top, trait_positions[current_position], trait_width, trait_height)
    
    # Initialize data for all three characters
    survivors = [analyze_character(left, top, i, skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height, config) for i in range(3)]
    reroll_history = []  # Store the last characters generated in the active slot

    start_time = time.time()
    while time.time() - start_time < (config.RUN_DURATION * 60):
    # Check if the process has been cancelled
        if cancel_process_flag:
            print("[INFO] Process cancelled by user.")
            break
    
    # Check if the game window is still active
        if not game_window.isActive:
            print("[ERROR] The game window is no longer active. Exiting script.")
            sys.exit(1)

        # Determine the weakest character
        temp_powers = []
        for i, survivor in enumerate(survivors):
            power = survivor['power']
            temp_powers.append(power)

        # Add SKILL_POWER to the strongest character with a preferred skill
        if config.PREFERRED_SKILLS:
            for skill in config.PREFERRED_SKILLS:
                characters_with_skill = [s for s in survivors if s.get('skill') == skill]
                if characters_with_skill:
                    strongest_with_skill = max(characters_with_skill, key=lambda s: s['power'])
                    index_of_strongest = survivors.index(strongest_with_skill)
                    temp_powers[index_of_strongest] += config.SKILL_POWER
                    debug_message(
                        f"Adding SKILL_POWER to the strongest survivor with preferred skill '{skill}': "
                        f"Survivor {index_of_strongest + 1}, new temp power: {temp_powers[index_of_strongest]}."
                    )
        weakest_index = min(range(3), key=lambda x: temp_powers[x])
        weakest_power = temp_powers[weakest_index]

        # Stop if the lowest power character exceeds the threshold
        if weakest_power > config.POWER_THRESHOLD:
            print(f"Stopping early as all characters have power above {config.POWER_THRESHOLD}.")
            break

        # Move to the position of the weakest character by moving the cursor to the traits square
        move_cursor_below_traits_square(left, top, trait_positions[weakest_index], trait_width, trait_height)
        current_position = weakest_index

        # Perform reroll and save character to history for final evaluation
        reroll()
        rerolled_character = analyze_character(left, top, weakest_index, skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height, config)
        
        # Add character to reroll history
        reroll_history.append(rerolled_character)

        # Explicitly block rerolls in the last second
        time_elapsed = time.time() - start_time
        if time_elapsed >= (config.RUN_DURATION * 60) - 1:
            debug_message(f"-- Near End Explicit Lock: Evaluating Best Character from Last 2 Rerolls in Slot {weakest_index + 1}. No more rerolls will be done. --")
            # Use "r" up to two times to go back to the best character in reroll history (limit to 2 characters)
            if reroll_history:
                best_character = max(reroll_history, key=lambda x: x['power'])
                best_index = reroll_history.index(best_character)
                # Press "r" once if best character is the second in history, twice if it's the first
                for _ in range(2 - best_index):
                    pyautogui.press("r")
                    time.sleep(config.REROLL_WAIT_TIME)
                survivors[weakest_index] = best_character
            break

        # Keep only the last 2
        if len(reroll_history) > 2:
            reroll_history.pop(0)

        survivors[weakest_index] = rerolled_character

    # Display characters in the same order as in the game
    print("Final survivors:")
    for idx, survivor in enumerate(survivors):
        print(f"S{idx + 1}: {survivor}")
        create_survivor_summary(survivors_frame, 8, idx, survivor['power'], survivor['traits'], survivor.get('skill', ''))

def run():
    start_roll()


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text, background="yellow", relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class SelectableListbox:
    def __init__(self, parent, row, label_text, tooltip_text, options_list, selected_list):
        self.parent = parent
        self.label_text = label_text
        self.tooltip_text = tooltip_text
        self.options_list = options_list
        self.selected_list = selected_list
        self.default_selected_list = selected_list.copy()
        
        self.original_positions = {}
        self.selected_items = []
        self.create_widgets(row)
        self.populate_listbox()
        
    def create_widgets(self, row):
        self.label = ttk.Label(self.parent, text=self.label_text)
        self.label.grid(row=row, column=0, sticky=tk.W)
        
        ToolTip(self.label, self.tooltip_text)
        
        self.listbox_frame = ttk.Frame(self.parent)
        self.listbox_frame.grid(row=row, column=1, sticky="ew")
        
        self.listbox = tk.Listbox(self.listbox_frame, selectmode=tk.MULTIPLE, height=6, width=20)   
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = ttk.Scrollbar(self.listbox_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
    
    def populate_listbox(self):
        self.listbox.delete(0, tk.END)
        sorted_options = sorted(self.options_list)
        selected_items = [item for item in sorted_options if item in self.selected_list]
        non_selected_items = [item for item in sorted_options if item not in self.selected_list]
        
        # Insert selected items at the top
        for item in selected_items:
            self.listbox.insert(tk.END, item)
            self.selected_items.append(item)
            self.original_positions[item] = sorted_options.index(item)
            self.listbox.selection_set(tk.END)
        
        # Insert non-selected items
        for item in non_selected_items:
            self.listbox.insert(tk.END, item)
            self.original_positions[item] = sorted_options.index(item)
        
        # Move the scroll to the top
        self.listbox.see(0)
    
    def on_select(self, event):
        selected_indices = self.listbox.curselection()
        new_selected_items = [self.listbox.get(i) for i in selected_indices]
        
        # Handle newly selected items
        for item in new_selected_items:
            if item not in self.selected_items:
                self.selected_items.append(item)
                self.original_positions[item] = self.listbox.get(0, tk.END).index(item)
        
        # Handle deselected items
        for item in self.selected_items[:]:
            if item not in new_selected_items:
                self.selected_items.remove(item)
                original_index = self.original_positions.pop(item)
                self.listbox.delete(self.listbox.get(0, tk.END).index(item))
                self.listbox.insert(original_index, item)
        
        # Move selected items to the top
        for item in reversed(self.selected_items):
            self.listbox.delete(self.listbox.get(0, tk.END).index(item))
            self.listbox.insert(0, item)
            self.listbox.selection_set(0)
        # Move the scroll to the top
        self.listbox.see(0)

    def get_selected_items(self):
        return self.selected_items
    
    def reset_selection(self):
        self.listbox.selection_clear(0, tk.END)
        self.selected_items.clear()
        self.original_positions.clear()
        self.selected_list = self.default_selected_list.copy()
        self.populate_listbox()

# Crear the main window
root = tk.Tk()
root.title("SO2 Auto-Reroll Mod")


# Create the main frame
frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# Create the frame for the survivor summaries
survivors_frame = ttk.Frame(frame, padding=0, relief=tk.FLAT)
survivors_frame.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E))
survivors_frame.grid_columnconfigure(0, weight=1)
survivors_frame.grid_columnconfigure(1, weight=1)
survivors_frame.grid_columnconfigure(2, weight=1)

def create_survivor_summary(frame, row, index, power, traits, skill):
    global root
    row_number = 0
    summary_frame = ttk.LabelFrame(frame, text=f"Survivor {index +1}")
    summary_frame.grid(row=row_number, column=index, padx=3, pady=5, sticky=(tk.W, tk.E))

    power_label = ttk.Label(summary_frame, text=f"Power: {power}")
    power_label.grid(row=row_number, column=0, sticky=tk.W)

    if len(config.PREFERRED_SKILLS) > 0:
        row_number += 1
        skills_label = ttk.Label(summary_frame, text=f"Skill:")
        skills_label.grid(row=row_number, column=0, sticky=tk.W)
        row_number += 1
        skills_text = ttk.Label(summary_frame, text=f"{skill}", font=("default", 8))
        skills_text.grid(row=row_number, column=0, sticky=tk.W)    

    root = frame.winfo_toplevel()
    bg_color = root.cget("background")
    bg_color_rgb = root.winfo_rgb(bg_color)
    bg_color_hex = f"#{bg_color_rgb[0]//256:02x}{bg_color_rgb[1]//256:02x}{bg_color_rgb[2]//256:02x}"
    row_number += 1
    traits_label = ttk.Label(summary_frame, text=f"Traits:")
    traits_label.grid(row=row_number, column=0, sticky=tk.W)
    row_number += 1
    traits_text = tk.Text(summary_frame, height=4, width=15, font=("default", 8), borderwidth=0, highlightthickness=0,  bg=bg_color_hex)
    traits_text.grid(row=row_number, column=0, sticky=tk.W)
    for trait in traits:
        if len(trait) > 15:
            trait_text = trait[:15]
        else:
            trait_text = trait
        traits_text.insert(tk.END, trait_text + "\n")
    traits_text.config(state=tk.DISABLED)


def ui():
    global root, status_label, frame
    default_config = config

    def validate_integer(P, minval, maxval):
        if P == "":
            return True
        try:
            value = int(P)
            return minval <= value <= maxval
        except ValueError:
            return False

    def validate_float(P, minval, maxval):
        if P in ["", "0", ".", "0.", "0.0"]:
            return True
        try:
            value = float(P)
            return minval <= value <= maxval
        except ValueError:
            return False

    vcmd_duration = (root.register(lambda P: validate_integer(P, 1, 60)), '%P')
    vcmd_reroll_wait = (root.register(lambda P: validate_float(P, 0.01, 10.0)), '%P')
    vcmd_power = (root.register(lambda P: validate_integer(P, 1, 100)), '%P')

    entry_width = 22
    row_number = 0 
    run_duration_label = ttk.Label(frame, text="Run Duration:")
    run_duration_label.grid(row=row_number, column=0, sticky=tk.W)
    run_duration_entry = ttk.Entry(frame, width=entry_width, validate="key", validatecommand=vcmd_duration)
    run_duration_entry.insert(0, str(config.RUN_DURATION))
    run_duration_entry.grid(row=row_number, column=1, sticky=tk.W)
    ToolTip(run_duration_label, "Duration of the run in minutes (1-60)")

    row_number += 1 
    power_threshold_label = ttk.Label(frame, text="Power Threshold:")
    power_threshold_label.grid(row=row_number, column=0, sticky=tk.W)
    power_threshold_entry = ttk.Entry(frame, width=entry_width, validate="key", validatecommand=vcmd_power)
    power_threshold_entry.insert(0, str(config.POWER_THRESHOLD))
    power_threshold_entry.grid(row=row_number, column=1, sticky=tk.W)
    ToolTip(power_threshold_label, "Power threshold to stop rerolling (1-100)")

    row_number += 1
    preferred_skills_selectable = SelectableListbox (frame, row_number, "Preferred Skills:", "Select preferred skills", SKILLS_LIST, default_config.PREFERRED_SKILLS)

    row_number += 1
    skill_power_label = ttk.Label(frame, text="Skill Power:")
    skill_power_label.grid(row=row_number, column=0, sticky=tk.W)
    skill_power_entry = ttk.Entry(frame, width=entry_width, validate="key", validatecommand=vcmd_power)
    skill_power_entry.insert(0, str(config.SKILL_POWER))
    skill_power_entry.grid(row=row_number, column=1, sticky=tk.W)
    ToolTip(skill_power_label, "Power added for preferred skills (1-100)")

    row_number += 1
    debug_label = ttk.Label(frame, text="Debug:")
    debug_label.grid(row=row_number, column=0, sticky=tk.W)
    debug_ocr_var = tk.BooleanVar(value=config.DEBUG)
    debug_ocr_check = ttk.Checkbutton(frame, variable=debug_ocr_var)
    debug_ocr_check.grid(row=row_number, column=1, sticky=tk.W)
    ToolTip(debug_label, "Enable or disable debug mode")

    row_number += 1
    reroll_wait_time_label = ttk.Label(frame, text="Reroll Wait Time:")
    reroll_wait_time_label.grid(row=row_number, column=0, sticky=tk.W)
    reroll_wait_time_entry = ttk.Entry(frame, width=entry_width, validate="key", validatecommand=vcmd_reroll_wait)
    reroll_wait_time_entry.insert(0, str(config.REROLL_WAIT_TIME))
    reroll_wait_time_entry.grid(row=row_number, column=1, sticky=tk.W)
    ToolTip(reroll_wait_time_label, "Wait time between rerolls in seconds (0.01-3.0)") 

    def show_console():
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 1)

    def hide_console():
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    def on_run():
        
        config.RUN_DURATION = int(run_duration_entry.get())
        config.REROLL_WAIT_TIME = float(reroll_wait_time_entry.get())
        config.POWER_THRESHOLD = int(power_threshold_entry.get())
        config.SKILL_POWER = int(skill_power_entry.get())
        config.DEBUG = debug_ocr_var.get()
        config.PREFERRED_SKILLS = preferred_skills_selectable.get_selected_items()
        if config.DEBUG:
            show_console()
        else:
            hide_console()
        run()

    
    def reset_to_defaults():
        run_duration_entry.delete(0, tk.END)
        run_duration_entry.insert(0, str(default_config.RUN_DURATION))
        
        reroll_wait_time_entry.delete(0, tk.END)
        reroll_wait_time_entry.insert(0, str(default_config.REROLL_WAIT_TIME))

        power_threshold_entry.delete(0, tk.END)
        power_threshold_entry.insert(0, str(default_config.POWER_THRESHOLD))

        skill_power_entry.delete(0, tk.END)
        skill_power_entry.insert(0, str(default_config.SKILL_POWER))

        debug_ocr_var.set(default_config.DEBUG)

        preferred_skills_selectable.reset_selection()

    row_number += 1
    reset_button = ttk.Button(frame, text="Reset to Defaults", command=reset_to_defaults)
    reset_button.grid(row=row_number, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))

    run_button = ttk.Button(frame, text="Run", command=on_run)
    run_button.grid(row=row_number, column=1, sticky=tk.E, padx=(10, 0), pady=(10, 0))

    # Label to display the status
    row_number += 1
    status_label = ttk.Label(frame, text="Ready, click 'Run' to start.")
    status_label.grid(row=row_number, column=0, columnspan=2, pady=10)

    # Create the survivor summary labels
    row_number += 1
    create_survivor_summary(survivors_frame, row_number, 0, 0, [''], "")
    create_survivor_summary(survivors_frame, row_number, 1, 0, [''], "")
    create_survivor_summary(survivors_frame, row_number, 2, 0,  [''], "")


    
    # Bind the Escape key to cancel the process
    root.bind('<Escape>', cancel_process)
    
    # Initialize the loop
    root.mainloop()

def main():
    ui()

if __name__ == "__main__":
    main()