# State of Decay 2 Auto-Reroll Mod for Optimal Character Selection

This mod automates the reroll process in **State of Decay 2** to help you find powerful survivors based on specific traits and skills preferences.

---

## Quick Start Instructions

1. **Extract the Files**:
   - Unzip all files from the mod ZIP package and place them together in one folder.

2. **Install Tesseract OCR**:
   - [Download it here](https://github.com/UB-Mannheim/tesseract/wiki).
   - Make sure Tesseract is installed at `C:\Program Files\Tesseract-OCR\tesseract.exe` or added to your system PATH.

3. **Set Up the Game**:
   - Switch to **windowed mode** and set the resolution to **1400x1050**.

4. **Run the Mod**:
   - Start a new community, skip the tutorial, and **run `so2_autoroll.exe`**.
   - You have **2 seconds** to select the game window before the program starts.

5. **Wait for Completion**:
   - The console will close automatically when the program finishes.
   - Start playing with your selected survivors, or run the program again if you want a different result.

---

## Details and Advanced Configuration

The mod prioritizes survivors based on the **relative power of their traits**, calculated from each trait's base benefits and hero bonuses. If you set **preferred skills** in `config.txt`, the mod will try to prioritize those skills, though it cannot guarantee specific skills will appear. For rare skills like `lichenology`, it may need to run up to 15 minutes to find them due to their rarity.

The mod works best without any preferred skills, as it then focuses solely on traits, maximizing the overall power of selected survivors. In about 10 minutes, the mod can often find characters with highly favorable traits.

### Files in the ZIP

- `so2_autoroll.exe` - Main executable.
- `config.txt` - Configuration file for custom settings.
- `Traits_Power_Scores.csv` - Trait power scoring data.
- `README.md` - This instruction file.

### Configuring `config.txt`

Adjust settings in `config.txt` to customize the mod:

- `RUN_DURATION`: Total run time in minutes (default: 5). Increase this if you're looking for rare skills.
- `PREFERRED_SKILLS`: List of preferred skills (e.g., `lichenology, hygiene, empty`). Note: adding skills may reduce overall trait power as the mod prioritizes those skills.
- `DEBUG`: Set to `true` to keep the console open after the program completes and display detailed logs.

Example `config.txt`:

```plaintext
RUN_DURATION = 10
REROLL_WAIT_TIME = 0.05
SIMILARITY_THRESHOLD = 0.85
POWER_THRESHOLD = 50
DEBUG = true
PREFERRED_SKILLS = lichenology, hygiene, computers, empty
```

### Debug Mode

Set `DEBUG = true` in `config.txt` to keep the console open at the end of the run. This will display additional logs, showing details about the traits and skills selected. This mode is useful for troubleshooting or understanding the trait selection process.
