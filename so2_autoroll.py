# =======================================
# Section 1: Imports
# Organized all imports here for clarity
# Standard library imports
import os
import sys
import time
import ctypes
import copy

# Third-party imports
import pyautogui
import pytesseract
import pygetwindow as gw
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
import keyboard
import tkinter as tk
from tkinter import ttk
from play_style_configs import play_style_configs
from compiled_traits import compiled_traits
# =======================================

# =======================================
# Section 2: Global Variables & Setup
# (Constants, config files, list definitions, etc.)
# Set the path to the local tesseract executable
pytesseract.pytesseract.tesseract_cmd = os.path.join(os.path.dirname(__file__), 'tesseract', 'tesseract.exe')

# Adjust the path to work with PyInstaller
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

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

# List of all the skills provided by traits
trait_skills = set()
for trait, info in compiled_traits.items():
    if "categories" in info and "provided_skills" in info["categories"]:
        for skill in info["categories"]["provided_skills"]:
            trait_skills.add(skill.lower())

# Merge the two lists to create the full list of skills without duplicates
ALL_SKILLS = FIFTH_SKILLS_LIST + [s for s in trait_skills if s not in FIFTH_SKILLS_LIST]


# Obtain the styles from the play_style_configs
STYLES = list(play_style_configs.keys())

# Game window title
GAME_WINDOW_TITLE = "StateOfDecay2 "

# Window selected global flag
window_selected = False

# Variable de control global para cancelar el proceso
cancel_process_flag = False
# =======================================

# =======================================
# Section 3: Configuration Class & Loading
# The Config class + the load_config() function
class Config:
    def __init__(self):
        self.RUN_DURATION = 2
        self.REROLL_WAIT_TIME = 0.01
        self.SIMILARITY_THRESHOLD = 0.8
        self.POWER_THRESHOLD = 50
        self.SKILL_POWER = 25
        self.DEBUG = False
        self.DEBUG_OCR = False
        self.PREFERRED_SKILLS = []
        self.BLOCKED_POSITIONS = []
        self.BLOCKED_TRAITS = []
        self.REQUIRE_ALL_TRAITS = False
        self.PLAY_STYLE = "strategist"

    def __str__(self):
        return str(self.__dict__)

def load_config():
    """Load and return the configuration from config.txt."""
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
                        if key in ["DEBUG", "DEBUG_OCR", "REQUIRE_ALL_TRAITS"]:
                            setattr(config, key, value.lower() == "true")
                        elif key == "PREFERRED_SKILLS":
                            skills = [skill.strip().lower() for skill in value.split(",") if skill.strip() and skill.strip().lower() != ""]
                            # Filter based on ALL_SKILLS
                            filtered_skills = [skill for skill in skills if skill in ALL_SKILLS]
                            setattr(config, key, filtered_skills)
                        elif key in ["POWER_THRESHOLD", "SKILL_POWER", "RUN_DURATION"]:
                            setattr(config, key, int(value))
                        elif key == "REROLL_WAIT_TIME" or key == "SIMILARITY_THRESHOLD":
                            setattr(config, key, float(value))
                        elif key == "BLOCKED_POSITIONS":
                            positions = [int(pos) for pos in value.split(",") if pos.strip()]
                            setattr(config, key, positions)
                        elif key == "BLOCKED_TRAITS":
                            traits = [trait.strip().lower() for trait in value.split(",") if trait.strip()]
                            setattr(config, key, traits)
                        elif key == "PLAY_STYLE":
                            if value.lower() in STYLES:
                                setattr(config, key, value.lower())
                except ValueError:
                    continue

    if config.DEBUG:
        print(f"Loaded configuration: {config}")
    return config

# Load configuration at the start
config = load_config()

# Dynamic imports based on configuration
if config.DEBUG_OCR:
    from PIL import ImageDraw

# =======================================

# =======================================
# Section 4: Main Reroll Logic & Utilities
# (Functions for window management, OCR, skill/trait analysis, etc.)
def cancel_process(event=None):
    """Set the global flag to cancel the process."""
    global cancel_process_flag
    if not cancel_process_flag:
        cancel_process_flag = True
        append_status_message("Process cancel has been requested.", True)

# Register the hotkey for cancelling the process
keyboard.add_hotkey('0', cancel_process)

def debug_message(msg):
    """Print debug messages if DEBUG is enabled."""
    if config.DEBUG:
        print(msg)

def debug_image(image, msg):
    """Save debug images if DEBUG_OCR is enabled."""
    if config.DEBUG_OCR:
        # Save the image with a timestamp
        unix_time = int(time.time())
        image.save(f"{msg}_{unix_time}.png")

def debug_image_with_boxes(image, skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height, msg):
    """Draw boxes on the image for debugging and save it."""
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
    """Return game window and geometry by title."""
    try:
        # Find the game window by title
        window = gw.getWindowsWithTitle(title)[0]  # Take the first window if there are multiple
        if config.DEBUG_OCR:
            screenshot = pyautogui.screenshot(region=(window.left, window.top, window.width, window.height))
            debug_image(screenshot, f"debug_game_window_capture_{window.width}x{window.height}")
        return window, window.left, window.top, window.width, window.height
    except IndexError:
        append_status_message("[ERROR] Game window not found.", True)
    
def get_aspect_ratio_category(width, height):
    """Determine the aspect ratio category based on width and height."""
    aspect_ratio = width / height
    debug_message(f"width:{width} height:{height}")
    if 1.5 <= aspect_ratio <= 1.85:  # Expand the range for 16:9 and similar wide ratios
        return "16:9"
    elif 1.25 <= aspect_ratio <= 1.4:  # Expand the range for 4:3 and similar ratios
        return "4:3"
    else:
        return "unknown"

def calculate_dynamic_positions(width, height):
    """Calculate dynamic positions for skills and traits based on window size."""
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
    """Capture a region of the screen and return it as an image."""
    x, y = position
    # Combine operations into a single call with direct calculation
    return pyautogui.screenshot(
        region=(left + x, top + y, width, height)
    ).convert('RGB')  # Convert to RGB for Pillow

def extract_text(processed_image):
    """Extract text from an image using Tesseract OCR."""
    # Strip and convert to lowercase in one chain
    text = pytesseract.image_to_string(
        processed_image, 
        config="--psm 6 -l eng -c tessedit_char_blacklist=.!@#$%^&*()[]{};:<>"
    ).strip().lower()
    
    # Check DEBUG_OCR first to avoid unnecessary empty check when debugging is disabled
    if config.DEBUG_OCR and not text:
        debug_image(processed_image, "empty_processed_image")
        debug_message("[DEBUG] Processed image text is empty, saved image as 'empty_processed_image'")
    
    return text

def calculate_similarity(a, b):
    """Calculate the similarity ratio between two strings."""
    return SequenceMatcher(None, a, b).ratio()

def get_character_power(ocr_traits):
    """Calculate the power of a character based on OCR traits."""
    detected_traits = []
    power = 0
    
    # Process each trait from OCR
    for ocr_trait in ocr_traits:
        # Skip empty traits
        if not ocr_trait.strip():
            continue
            
        # Try exact match first (faster)
        if ocr_trait in compiled_traits:
            detected_traits.append(ocr_trait)
            power += compiled_traits[ocr_trait]['styles'][config.PLAY_STYLE]
            continue
        
        # If no exact match, find the most similar trait and check threshold in one pass
        best_match = None
        highest_similarity = 0
        
        for trait in compiled_traits:
            similarity = calculate_similarity(ocr_trait, trait)
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = trait
                # Early exit on perfect match
                if similarity == 1.0:
                    break
        
        # Only add if it meets the similarity threshold
        if highest_similarity >= config.SIMILARITY_THRESHOLD:
            detected_traits.append(best_match)
            power += compiled_traits[best_match]['styles'][config.PLAY_STYLE]
            if config.DEBUG:
                debug_message(f"Approximate match: '{ocr_trait}' -> '{best_match}' (Similarity: {highest_similarity:.2f})")
        elif config.DEBUG:
            debug_message(f"No match found for '{ocr_trait}' (Similarity: {highest_similarity:.2f})")

    # Special case for minmaxer play style
    if config.PLAY_STYLE == "minmaxer" and detected_traits:
        negative_power = sum(compiled_traits[trait]['categories']['negative'] for trait in detected_traits)
        positive_power = sum(compiled_traits[trait]['categories']['positive'] for trait in detected_traits)
        power = min(positive_power, negative_power)

    # Debug logging
    if config.DEBUG_OCR:
        debug_message(f"Traits from OCR: {ocr_traits}")
    if config.DEBUG:
        debug_message(f"Detected Traits: {detected_traits}")
        
    return detected_traits, round(power, 2)

def reroll():
    """Send a keypress for rerolling the character."""
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
    if text in FIFTH_SKILLS_LIST:
        return text
    
    # Debug log when exact match fails
    if config.DEBUG:
        debug_message(f"[DEBUG] Exact match failed for skill: '{text}'")
    
    # If no exact match, look for the closest skill in FIFTH_SKILLS_LIST
    best_match = ""
    highest_similarity = 0
    
    for skill in FIFTH_SKILLS_LIST:
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

# Survivor class for storing character data
class Survivor:
    """Class to store survivor data."""
    def __init__(self, position, power, traits, skills=[]):
        self.power = power
        self.traits = traits
        self.skills = skills
        self.position = position

    #Compatible with the dictionary interface
    def __getitem__(self, key):
        """Get the value of a key."""
        print(f"Deprecates message: Survivor[{key}] is deprecated. Use Survivor.{key} instead.")
        if key == "power":
            return self.power
        elif key == "traits":
            return self.traits
        elif key == "skills":
            return self.skills
        else:
            raise KeyError(f"Invalid key: {key}")
    
    def blocked_traits(self):
        """Get a list of blocked traits present on the character."""
        return [trait for trait in self.traits if trait in config.BLOCKED_TRAITS]

    def __str__(self):
        return f"position: {self.position}, power: {self.power}, traits: {self.traits}, skills: {self.skills}"


def analyze_character(left, top, index, skill_positions, skill_width, skill_height, trait_positions, trait_width, trait_height, config):
    """Analyze skills/traits/power for a single character."""
    # Check if skill OCR is needed: only perform skill OCR if there are preferred skills configured 
    # AND at least one of those skills is not a fifth skill
    check_skills_ocr = bool(config.PREFERRED_SKILLS) and any(skill in FIFTH_SKILLS_LIST for skill in config.PREFERRED_SKILLS)
    
    # Capture image for traits - always needed
    trait_image = capture_region(left, top, trait_positions[index], trait_width, trait_height)
    
    # Only capture skill image if needed
    skill_image = None
    if check_skills_ocr:
        skill_image = capture_region(left, top, skill_positions[index], skill_width, skill_height)

    # Process images in parallel if both are needed, otherwise just process traits
    futures = []
    with ThreadPoolExecutor() as executor:
        futures.append(executor.submit(analyze_traits, trait_image, config))
        
        if check_skills_ocr:
            futures.append(executor.submit(analyze_skills, skill_image, config))
        
        results = [future.result() for future in futures]

    # Extract results
    traits, power = results[0]
    skill_text = results[1] if check_skills_ocr else ""
    
    # Build skills list
    skills = []
    if skill_text:
        skills.append(skill_text)

    # Add skills from traits
    for trait in traits:
        provided_skills = compiled_traits[trait]["categories"].get('provided_skills', [])
        for skill in provided_skills:
            if skill not in skills:
                skills.append(skill)

    result = Survivor(index, power, traits, skills)
    debug_message(f"S{index + 1}: {result}")

    return result

def move_cursor_below_traits_square(left, top, trait_position, trait_width, trait_height):
    """Move the cursor to 20 pixels below the center of the traits square."""
    x, y = trait_position
    center_x = left + x + trait_width // 2
    center_y = top + y + trait_height + 20  # Move 20 pixels below the traits square
    pyautogui.moveTo(center_x, center_y)

def start_roll():
    """Main loop for rolling characters until threshold or timeout."""
    global window_selected, cancel_process_flag
    # Get game window and its initial position
    game_window, left, top, width, height = get_game_window_position(GAME_WINDOW_TITLE)
    
    # Check if the game window is active
    if not game_window.isActive:
        append_status_message("Activating game window.", True)
        game_window.activate()
        time.sleep(.5)  # Give some time for the window to activate
        if not game_window.isActive:
            append_status_message("[ERROR] The game window could not be activated.", True)
            return
            
    append_status_message("Rolling the characters. Press '0' to cancel", True)

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
    survivors = [
        analyze_character(
            left, top, i, 
            skill_positions, skill_width, skill_height, 
            trait_positions, trait_width, trait_height, 
            config
        ) 
        for i in range(3)
    ]

    # Create the UI summary for the initial characters
    for idx, survivor in enumerate(survivors):
        update_survivor_summary(idx, survivor.power, survivor.traits, survivor.skills)
    root.update_idletasks() # Update the UI to display the summary

    # Initialize reroll history
    reroll_history = []

    # Main loop for rolling survivors
    end_time = time.time() + (config.RUN_DURATION * 60)  # Calculate end time once
    
    while time.time() < end_time:
        # Check if the process has been cancelled
        if cancel_process_flag:
            debug_message("Process cancelled.")
            break # Break the loop to stop rerolling

        # Filter out blocked positions (only recalculate when needed)
        available_positions = [i for i in range(3) if i not in config.BLOCKED_POSITIONS]

        # Filter available positions based on blocked traits
        if available_positions and config.BLOCKED_TRAITS:
            positions_to_block = []
            new_available_positions = []
            
            # Determine which positions to block or keep
            for pos in available_positions:
                blocked_traits = survivors[pos].blocked_traits()
                # Block if there are blocked traits and either all traits aren't required or all specified traits are present
                if blocked_traits and (not config.REQUIRE_ALL_TRAITS or len(blocked_traits) == len(config.BLOCKED_TRAITS)):
                    positions_to_block.append(pos)
                else:
                    new_available_positions.append(pos)
            
            # Apply blocking actions to positions marked for blocking
            for pos in positions_to_block:
                config.BLOCKED_POSITIONS.append(pos)  # Mark position as blocked
                blocked_positions_vars[pos].set(1)    # Update UI checkbox
                append_status_message(f"Position #{pos + 1} blocked due to traits: {', '.join(survivors[pos].blocked_traits())}", True)
            
            # Update the available positions list
            available_positions = new_available_positions

        # Stop if all positions are blocked
        if not available_positions:
            append_status_message(f"Stop. All characters are blocked.", True)
            break

        # Calculate temporary powers (with preferred skill bonus) in one pass
        temp_powers = [survivor.power for survivor in survivors]
        
        # Add skill power bonus more efficiently
        if available_positions and config.PREFERRED_SKILLS:
            # Group survivors by their skill sets
            skill_groups = {}
            for pos in available_positions:
                survivor = survivors[pos]
                # Convert the skills list to a tuple so it can be used as a dictionary key
                skill_set = tuple(sorted(survivor.skills))
                if skill_set not in skill_groups:
                    skill_groups[skill_set] = []
                skill_groups[skill_set].append(pos)
            
            # For each group of survivors with identical skills
            for skill_set, positions in skill_groups.items():
                # Count how many preferred skills are present in this skill set
                preferred_skills_count = sum(skill in skill_set for skill in config.PREFERRED_SKILLS)
                
                if preferred_skills_count > 0 and positions:
                    # Find the survivor with the highest base power in this group
                    best_pos = max(positions, key=lambda pos: survivors[pos].power)
                    
                    # Add bonus only to the survivor with highest base power
                    temp_powers[best_pos] += config.SKILL_POWER * preferred_skills_count
                    
                    if config.DEBUG:
                        debug_message(f"S{best_pos+1}: +{config.SKILL_POWER * preferred_skills_count} power ({preferred_skills_count} skills) → Total: {temp_powers[best_pos]}")
                        if len(positions) > 1:
                            debug_message(f"Identical skills at positions {[p+1 for p in positions]} → Bonus to S{best_pos+1} only")
        
        # Find empty survivors (power=0, traits=[], skills=[]) in available positions
        empty_survivors = [s for s in survivors if s.position in available_positions and 
                        s.power == 0 and s.traits == [] and s.skills == []]

        if empty_survivors:
            # Select the first empty survivor found
            weakest_survivor = empty_survivors[0]
            weakest_index = weakest_survivor.position
            weakest_power = 0
            debug_message(f"Empty survivor found at pos {weakest_index}")
        else:
            # Find the position with the smallest temp_powers among available positions
            weakest_index = min(available_positions, key=lambda x: temp_powers[x])
            weakest_power = temp_powers[weakest_index]

        # Stop if the lowest power survivor exceeds the threshold
        if weakest_power > config.POWER_THRESHOLD:
            append_status_message(f"Stop. All survivors have power above {config.POWER_THRESHOLD}.", True)
            break

        # Only update UI if position changes
        if current_position != weakest_index:
            reroll_history = []  # Clear reroll history when moving to a new position
            # Update the UI with the new position
            update_survivor_summary(
                current_position, 
                survivors[current_position].power, 
                survivors[current_position].traits, 
                survivors[current_position].skills
            )
            root.update_idletasks() # Update the UI to display the summary
                        
        # Move to the weakest survivor position
        move_cursor_below_traits_square(left, top, trait_positions[weakest_index], trait_width, trait_height)
        current_position = weakest_index

        # Perform reroll
        reroll()
        
        # Analyze new character and update
        rerolled_character = analyze_character(
            left, top, weakest_index, 
            skill_positions, skill_width, skill_height, 
            trait_positions, trait_width, trait_height, 
            config
        )        
        
        # Add to history and maintain max history size efficiently
        reroll_history.append(rerolled_character)
        if len(reroll_history) > 3:
            reroll_history.pop(0)

        # Update the survivor data
        survivors[weakest_index] = rerolled_character

        # Check if we're near the end of run time
        remaining_time = end_time - time.time()
        if remaining_time < 2:  # Last 2 seconds of run
            debug_message(
                f"-- Near End Explicit Lock: Evaluating Best Survivor from Last 3 Rerolls in Slot {weakest_index + 1}. "
                "No more rerolls will be done. --"
            )
            
            # Select best survivor from history
            if reroll_history:
                best_character = max(reroll_history, key=lambda x: x.power)
                best_index = reroll_history.index(best_character)
                debug_message(f"Best character from last 3 index: {best_index}, character: {best_character}")
                # Only press "r" if the best character is not the current one
                if best_index < 2:  # If best_index is 2, it's already the current character
                    for _ in range(2 - best_index):
                        pyautogui.press("r")
                        time.sleep(config.REROLL_WAIT_TIME)
                survivors[weakest_index] = best_character
            break

    # Update the UI with the final survivors
    append_status_message("Updating survivors summary.", True)
    for idx, survivor in enumerate(survivors):
        print(f"S{idx + 1}: {survivor}")
        update_survivor_summary(idx, survivor.power, survivor.traits, survivor.skills)   

# =======================================

# =======================================
# Section 5: UI Classes & Functions
# (ToolTip, SelectableListbox, UI creation, etc.)

# Create the main window
root = tk.Tk()
root.title("SO2 Auto-Reroll Mod")
# Disable resizing and maximize button
root.resizable(False, False)

# Set the icon for the window
ico_path = os.path.join(base_path, 'app_icon.ico')
root.iconbitmap(ico_path)

# Enable debug console if the argument is passed
if "--enable-debug-console" in sys.argv:
    config.DEBUG = True
    ctypes.windll.kernel32.AllocConsole()
    sys.stdout = open("CONOUT$", "w")
    sys.stderr = open("CONOUT$", "w")

# Create the main frame
frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

SURVIVOR_FRAME_ROW = 11
# Create the frame for the survivor summaries
survivors_frame = ttk.Frame(frame, padding=0, relief=tk.FLAT)
survivors_frame.grid(row=SURVIVOR_FRAME_ROW, column=0, columnspan=2, sticky=(tk.W, tk.E))
survivors_frame.grid_columnconfigure(0, weight=1)
survivors_frame.grid_columnconfigure(1, weight=1)
survivors_frame.grid_columnconfigure(2, weight=1)

# Create the survivor widgets dictionary
survivor_widgets = {}

# Create the status text widget
status_text = None

# Create the blocked positions variables
blocked_positions_vars = [tk.IntVar(value=1 if i in config.BLOCKED_POSITIONS else 0) for i in range(3)]

def append_status_message(message, also_print=False):
    """Append a message to the status text widget."""
    global status_text
    status_text.config(state=tk.NORMAL)
    status_text.insert(tk.END, message + "\n")
    status_text.config(state=tk.DISABLED)
    status_text.see(tk.END)
    root.update_idletasks() # Update the UI to show the message
    if also_print:
        print(message)

class ToolTip:
    """Display a tooltip for a given Tkinter widget."""
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

    def set_text(self, text):
        """Actualizar el texto del tooltip."""
        self.text = text
        if self.tooltip:
            for widget in self.tooltip.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.config(text=text)

class SelectableListbox:
    """Custom listbox that tracks selected items separately."""
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
        
        self.listbox = tk.Listbox(self.listbox_frame, selectmode=tk.MULTIPLE, height=6, width=20, exportselection=False)   
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
        
        # Ensure the selected items are updated in the selected_list
        self.selected_list = self.selected_items.copy()

    def get_selected_items(self):
        return self.selected_items
    
    def reset_selection(self):
        self.listbox.selection_clear(0, tk.END)
        self.selected_items.clear()
        self.original_positions.clear()
        self.selected_list = self.default_selected_list.copy()
        self.populate_listbox()
    
    def update_selection(self, new_selected_items):
        """Actualiza la selección en el listbox sin redibujarlo."""
        self.selected_list = new_selected_items
        self.listbox.selection_clear(0, tk.END)
        for idx in range(self.listbox.size()):
            item = self.listbox.get(idx)
            if item in new_selected_items:
                self.listbox.selection_set(idx)
        self.on_select(self)

def create_survivor_summary(frame, row, index, power, traits, skills):
    """Add a summary of survivor info to the UI."""
    global root, survivor_widgets

    summary_frame = ttk.LabelFrame(frame, text=f"Survivor {index + 1}")
    summary_frame.grid(row=row, column=index, padx=3, pady=5, sticky=(tk.W, tk.E))

    local_row = 0
    power_label = ttk.Label(summary_frame, text=f"Power: {power}")
    power_label.grid(row=local_row, column=0, sticky=tk.W)

    root = frame.winfo_toplevel()
    bg_color = root.cget("background")
    bg_color_rgb = root.winfo_rgb(bg_color)
    bg_color_hex = f"#{bg_color_rgb[0]//256:02x}{bg_color_rgb[1]//256:02x}{bg_color_rgb[2]//256:02x}"

    local_row += 1
    traits_label = ttk.Label(summary_frame, text="Traits:")
    traits_label.grid(row=local_row, column=0, sticky=tk.W)
    local_row += 1
    traits_text = tk.Text(summary_frame, height=4, width=15, font=("default", 8), borderwidth=0, highlightthickness=0, bg=bg_color_hex)
    traits_text.grid(row=local_row, column=0, sticky=tk.W)

    for trait in traits:
        traits_text.insert(tk.END, (trait[:15] + "\n") if len(trait) > 15 else (trait + "\n"))
    traits_text.config(state=tk.DISABLED)

    local_row += 1
    skills_label = ttk.Label(summary_frame, text="Skills:")
    skills_label.grid(row=local_row, column=0, sticky=tk.W)
    local_row += 1
    skills_text = tk.Text(summary_frame, height=3, width=15, font=("default", 8), borderwidth=0, highlightthickness=0, bg=bg_color_hex)
    skills_text.grid(row=local_row, column=0, sticky=tk.W)

    for skill in skills:
        skills_text.insert(tk.END, (skill[:15] + "\n") if len(skill) > 15 else (skill + "\n"))
    skills_text.config(state=tk.DISABLED)

    # Store widgets in a dictionary for updating later
    survivor_widgets[index] = {
        'summary_frame': summary_frame,
        'power_label': power_label,
        'skills_text': skills_text,
        'traits_text': traits_text
    }

def update_survivor_summary(index, power, traits, skills):
    """Update the summary of survivor info in the UI."""
    global survivor_widgets

    if index not in survivor_widgets:
        return

    # Update power label
    power_label = survivor_widgets[index]['power_label']
    power_str = str(power)
    power_label.config(text=f"Power: {power_str.rjust(6)}")

    skills_text = survivor_widgets[index]['skills_text']
    skills_text.config(state=tk.NORMAL)
    skills_text.delete('1.0', tk.END)
    for skill in skills:
        skills_text.insert(tk.END, (skill[:15] + "\n") if len(skill) > 15 else (skill + "\n")) 
    skills_text.config(state=tk.DISABLED)

    # Update traits text
    traits_text = survivor_widgets[index]['traits_text']
    traits_text.config(state=tk.NORMAL)
    traits_text.delete('1.0', tk.END)
    for trait in traits:
        traits_text.insert(tk.END, (trait[:15] + "\n") if len(trait) > 15 else (trait + "\n"))
    traits_text.config(state=tk.DISABLED)

def ui():
    """Initialize the main Tkinter UI."""
    global root, status_text, frame
    default_config = copy.deepcopy(config)

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
    vcmd_power = (root.register(lambda P: validate_integer(P, 1, 150)), '%P')

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
    ToolTip(power_threshold_label, "Power threshold to stop rerolling (1-150)")

    row_number += 1
    blocked_positions_label = ttk.Label(frame, text="Blocked Positions:")
    blocked_positions_label.grid(row=row_number, column=0, sticky=tk.W)
    ToolTip(blocked_positions_label, "Select the positions to block from re-rolling.")

    checkbox_frame = ttk.Frame(frame)
    checkbox_frame.grid(row=row_number, column=1, sticky=tk.W)

    blocked_positions_checkboxes = [
        ttk.Checkbutton(checkbox_frame, text=f"{i+1}", variable=blocked_positions_vars[i])
        for i in range(3)
    ]
    for i, checkbox in enumerate(blocked_positions_checkboxes):
        checkbox.grid(row=row_number, column=i, sticky=tk.W)

    traits_list = [trait for trait in compiled_traits.keys()]
    row_number += 1
    traits_tooltip = "If a blocked trait is found, the character will not be re-rolled. Leave empty to disable."
    blocked_traits_selectable = SelectableListbox (frame, row_number, "Blocked Traits:", traits_tooltip, traits_list, default_config.BLOCKED_TRAITS)            

    row_number += 1
    # Create a BooleanVar to control the Checkbutton state
    all_traits_var = tk.BooleanVar(value=config.REQUIRE_ALL_TRAITS)  # Set to True to make it checked by default
    all_traits_label = ttk.Label(frame, text="Require all traits:")
    all_traits_label.grid(row=row_number, column=0, sticky=tk.W)
    all_traits_entry = ttk.Checkbutton(frame, text="", variable=all_traits_var)
    all_traits_entry.grid(row=row_number, column=1, sticky=tk.W)
    ToolTip(all_traits_label, "All traits must be present to block the character.")

    row_number += 1
    skills_tooltip = "If a preferred skill is found, it will add SKILL_POWER to the character's power. Leave empty to disable." 
    preferred_skills_selectable = SelectableListbox (frame, row_number, "Preferred Skills:", skills_tooltip, ALL_SKILLS, default_config.PREFERRED_SKILLS)

    row_number += 1
    skill_power_label = ttk.Label(frame, text="Skill Power:")
    skill_power_label.grid(row=row_number, column=0, sticky=tk.W)
    skill_power_entry = ttk.Entry(frame, width=entry_width, validate="key", validatecommand=vcmd_power)
    skill_power_entry.insert(0, str(config.SKILL_POWER))
    skill_power_entry.grid(row=row_number, column=1, sticky=tk.W)
    ToolTip(skill_power_label, "Power added for preferred skills (1-150)")

    row_number += 1
    reroll_wait_time_label = ttk.Label(frame, text="Reroll Wait Time:")
    reroll_wait_time_label.grid(row=row_number, column=0, sticky=tk.W)
    reroll_wait_time_entry = ttk.Entry(frame, width=entry_width, validate="key", validatecommand=vcmd_reroll_wait)
    reroll_wait_time_entry.insert(0, str(config.REROLL_WAIT_TIME))
    reroll_wait_time_entry.grid(row=row_number, column=1, sticky=tk.W)
    ToolTip(reroll_wait_time_label, "Wait time between rerolls in seconds (0.01-3.0)") 

    row_number += 1
    play_style_label = ttk.Label(frame, text="Play Style:")
    play_style_label.grid(row=row_number, column=0, sticky=tk.W)
    play_style_combobox = ttk.Combobox(frame, values=STYLES, state="readonly", width=entry_width)
    default_play_style = default_config.PLAY_STYLE
    play_style_combobox.set(default_play_style)
    play_style_combobox.grid(row=row_number, column=1, sticky=tk.W)
    ToolTip(play_style_label, "Select the play style to use for power calculation.") 
    play_style_tooltip = ToolTip(play_style_combobox, play_style_configs[default_play_style]['description'])

    def update_play_style_tooltip(event):
        selected_style = play_style_combobox.get()
        description = play_style_configs[selected_style]['description']
        play_style_tooltip.set_text(description)

    play_style_combobox.bind("<<ComboboxSelected>>", update_play_style_tooltip)

    def on_run():
        """Update config and start the reroll process."""
        global cancel_process_flag
        cancel_process_flag = False  # Reset the cancel flag
        config.RUN_DURATION = int(run_duration_entry.get())
        config.REROLL_WAIT_TIME = float(reroll_wait_time_entry.get())
        config.POWER_THRESHOLD = int(power_threshold_entry.get())
        config.SKILL_POWER = int(skill_power_entry.get())
        config.PREFERRED_SKILLS = preferred_skills_selectable.get_selected_items()
        config.BLOCKED_TRAITS = blocked_traits_selectable.get_selected_items()
        config.REQUIRE_ALL_TRAITS = all_traits_var.get()
        config.BLOCKED_POSITIONS = [i for i, var in enumerate(blocked_positions_vars) if var.get() == 1]
        config.PLAY_STYLE = play_style_combobox.get()  # Capture the selected game mode
        start_roll()

    def reset_to_defaults():
        """Reset all UI fields to their default values."""
        run_duration_entry.delete(0, tk.END)
        run_duration_entry.insert(0, str(default_config.RUN_DURATION))
        
        reroll_wait_time_entry.delete(0, tk.END)
        reroll_wait_time_entry.insert(0, str(default_config.REROLL_WAIT_TIME))

        power_threshold_entry.delete(0, tk.END)
        power_threshold_entry.insert(0, str(default_config.POWER_THRESHOLD))

        skill_power_entry.delete(0, tk.END)
        skill_power_entry.insert(0, str(default_config.SKILL_POWER))

        for i, var in enumerate(blocked_positions_vars):
            var.set(1 if i in default_config.BLOCKED_POSITIONS else 0)
            
        blocked_traits_selectable.reset_selection()
        preferred_skills_selectable.reset_selection()
        play_style_combobox.set(default_play_style)  # Reset to the default game mode

    row_number += 1
    reset_button = ttk.Button(frame, text="Reset to Defaults", command=reset_to_defaults)
    reset_button.grid(row=row_number, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))

    run_button = ttk.Button(frame, text="Run", command=on_run)
    run_button.grid(row=row_number, column=1, sticky=tk.E, padx=(10, 0), pady=(10, 0))

    # Create the status text widget with a scrollbar
    row_number += 1
    status_frame = ttk.Frame(frame)
    status_frame.grid(row=row_number, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))

    status_text = tk.Text(status_frame, height=5, width=46, wrap=tk.WORD, state=tk.DISABLED, font=("default", 8))
    status_text.grid(row=0, column=0, sticky=(tk.W, tk.E))

    status_scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=status_text.yview)
    status_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

    status_text.config(yscrollcommand=status_scrollbar.set)

    append_status_message("Ready to run. Click 'Run' to start.", True)
    #row_number += 1 must be equal to SURVIVOR_FRAME_ROW
    
    for i in range(3):
        create_survivor_summary(survivors_frame, SURVIVOR_FRAME_ROW, i, 0, [''], ['']) # Initialize the UI with empty survivors

    # Initialize the loop
    root.mainloop()
# =======================================

# =======================================
# Section 6: Main Entry Point
# (Program startup / main execution)
def main():
    """Start the UI when run as the main module."""
    ui()

if __name__ == "__main__":
    main()
# =======================================