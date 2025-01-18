State of Decay 2 Auto-Reroll Mod for Optimal Character Selection

This mod automates the reroll process in State of Decay 2 to help you find powerful survivors based on specific traits and skills preferences.

---

Quick Start Instructions

1. Extract the Files:
   - Unzip all files from the mod ZIP package and place them together in one folder.

2. Set Up the Game:
   - Make sure that the game is set to English.
   - Switch to windowed mode and set the resolution to a 4:3 or 16:9 aspect ratio.

3. Run the Mod:
   - Start a new community, skip the tutorial, and run so2_autoroll.exe.
   - Press the "Run" button when you are ready. If the game is open, the window will be automatically selected.
   
4. Wait for Completion:
   - Start playing with your selected survivors, or click on "Run" to re-roll again if you want different results.

---

Known Issues

There is a minor issue: when you select text in the input fields, such as skill power, the selected skills are deselected. This is related to the feature that moves the selected skills to the top when you click on them. I am still working on a solution for this.

---

Details and Advanced Configuration

The mod prioritizes survivors based on the relative power of their traits, calculated from each trait's base benefits and hero bonuses. If you set preferred skills in config.txt, the mod will try to prioritize those skills, though it cannot guarantee specific skills will appear. You can configure the preference for the skill by configuring the SKILL_POWER in config.txt. For rare skills like lichenology, it may need to run up to 15 minutes to find them due to their rarity.

The mod works best without any preferred skills, as it then focuses solely on traits, maximizing the overall power of selected survivors. In about 10 minutes, the mod can often find characters with highly favorable traits.

Files in the ZIP

- so2_autoroll.exe - Main executable.
- README.txt - This instruction file.

Configuring

The mod is already optimized to find powerful characters in a certain amount of time. Most changes in the configuration will have diminishing returns, but feel free to experiment. If you find a configuration particularly useful, you can save it in the config.txt file to use as default for future re-rolls.

Adjust settings in the UI to customize the mod:
- POWER_THRESHOLD: Each trait adds some value to the total power of the character (some traits are negative). When all the characters have this level and the RUN_DURATION is not reached, the process is interrupted.
- RUN_DURATION: Total run time in minutes (default: 2). Increase this if you're looking for rare skills or have a high POWER_THRESHOLD.
- PREFERRED_SKILLS: List of preferred skills (e.g., lichenology, hygiene, empty). Note: adding skills may reduce overall trait power as the mod prioritizes those skills.
- SKILL_POWER: A character with a preferred skill is considered more powerful before deciding the re-roll. This value is how much power is temporarily added to the character with one of the PREFERRED_SKILLS. Only non-blocked characters are considered. If there are two or more non-blocked characters with the same preferred skill, only the most powerful receives the bonus. This value is not present in the final results; it is just temporarily added to consider re-rolling a character or not.
- BLOCKED_POSITIONS: Prevent re-rolling the character in these positions.
- REROLL_WAIT_TIME: Increase this number if you are using an old computer. This will reduce the speed of each re-roll.

Note about config.txt
The config.txt file is optional since the release of the UI and removed from the build. Use it if you want to store default values. Setting up all the properties is not needed; you only need to set values you want to keep. Lines starting with or empty lines are ignored.

Example of optional config.txt:


# Comment sample line being ignored
POWER_THRESHOLD = 30
RUN_DURATION = 10
# empty is also an available skill
PREFERRED_SKILLS = lichenology, hygiene, computers, empty
SKILL_POWER = 10
# Blocked positions start at 0 and end at 2 (0, 1, 2)
BLOCKED_POSITIONS = 0, 2
REROLL_WAIT_TIME = 0.01


Debug Console Mode
Run the so2_autoroll.exe with the parameter --enable-debug-console. This console will display additional logs, showing details about the traits and skills selected. This mode is useful for troubleshooting or understanding the trait selection process. Note that this mode is always slower than the default mode.