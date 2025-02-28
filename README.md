# State of Decay 2 Auto-Reroll Mod for Optimal Character Selection

This mod automates the reroll process in **State of Decay 2** to find powerful survivors based on specific traits and skills preferences.

---

## Quick Start Instructions

1. **Extract the Files**:
   - Unzip all files from the mod package into a single folder.

2. **Set Up the Game**:
   - Ensure the game is in English.
   - Switch to **windowed mode** with a 4:3 or 16:9 resolution.

3. **Run the Mod**:
   - Start a new community, skip the tutorial, and launch **so2_autoroll.exe**.
   - Click "Run" when ready. The game window will be auto-selected if open.

4. **Wait for Results**:
   - Play with your selected survivors, or click "Run" again to reroll for different outcomes.

---

## Known Issues
When no skills are selected, the mod relies solely on traits for detection. Since trait variants exist with and without skills, detection may fail in some cases. This is intentional to optimize survivor rolling when no skills are chosen.

## Details and Advanced Configuration

The mod prioritizes survivors based on the **relative power of their traits**, derived from base benefits and hero bonuses. Setting **preferred skills** in **config.txt** shifts focus to those skills, though they’re not guaranteed. Adjust **SKILL_POWER** in config.txt to tweak skill preference. Rare skills like **lichenology** may take up to 15 minutes to find due to their scarcity.

Without preferred skills, the mod maximizes trait power alone, often finding strong survivors in about 10 minutes.

### Files in the ZIP

- **so2_autoroll.exe**: Main executable.
- **README.txt**: This instruction file.

### Configuring

The mod scores traits based on your play style, stopping when the time limit is hit or all survivors exceed the power threshold.

Adjust settings in the UI:
- **POWER_THRESHOLD**: Minimum power per survivor (some traits reduce it). Stops early if all hit this before time’s up.
- **RUN_DURATION**: Total runtime in minutes (default: 2). Increase for rare skills or high thresholds.
- **PREFERRED_SKILLS**: List of desired skills (e.g., **lichenology, computers**). May lower trait power.
- **SKILL_POWER**: Temporary power boost for characters with preferred skills during reroll decisions (not in final results).
- **BLOCKED_POSITIONS**: Positions to skip during rerolls.
- **BLOCKED_TRAITS**: Traits that lock a survivor from rerolling.
- **REROLL_WAIT_TIME**: Increase for older PCs to slow reroll speed.
- **PLAY_STYLE**: Power calculation mode (e.g., **strategist, beginner**).

#### Note about config.txt
Since the UI release, **config.txt** is optional and not included in the build. Use it for default values. Only set what you need; lines starting with \# or blank are ignored.

Example **config.txt**:

```plaintext
# Sample comment ignored
POWER_THRESHOLD = 30
RUN_DURATION = 10
PREFERRED_SKILLS = lichenology, hygiene, computers, empty
SKILL_POWER = 10
BLOCKED_POSITIONS = 0, 2
BLOCKED_TRAITS = blood plague survivor, incredible immune system, germophobe
REROLL_WAIT_TIME = 0.01
PLAY_STYLE = resourceful
```

### Debug Console Mode
Run **so2_autoroll.exe --enable-debug-console** for detailed logs on traits and skills. Useful for troubleshooting or analyzing selections, but slower than default mode.