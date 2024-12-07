import csv
import re
import math

def read_csv(file_path):
    """Read the CSV file and return the data as a list of dictionaries."""
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        data = [row for row in reader]
    return data

def write_csv(file_path, data, fieldnames):
    """Write the data to a CSV file."""
    with open(file_path, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def evaluate_traits(data, modes):
    """Evaluate traits based on the specified modes and assign power values."""
    for row in data:
        for mode in modes:
            row[f'Power Score [{mode}]'] = evaluate_mode(row, mode)
    return data

def evaluate_mode(row, mode):
    """Evaluate the power score based on the specified mode."""
    power_score = 0

    # Define the priorities for each mode
    mode_priorities = {
        'default': [
            'Plague Infection',
            'Injury Chance',
            'Max Stamina',
            'Max Health',
            'Standing Rewards',
            'Meds Per Day',
            'Morale (Community)'
        ],
        # Add other modes here with their respective priorities
    }

    # Get the priorities for the specified mode
    priorities = mode_priorities.get(mode, [])

    # Positive Effects
    positive_effects = row['Positive Effect(s)']
    power_score += evaluate_effects(positive_effects, priorities, positive=True)

    # Provided Hero Bonus
    hero_bonus = row['Provided Hero Bonus']
    power_score += evaluate_effects(hero_bonus, priorities, positive=True)

    # Negative Effects
    negative_effects = row['Negative Effect(s)']
    power_score += evaluate_effects(negative_effects, priorities, positive=False)

    return math.floor(power_score)

def evaluate_effects(effects, priorities, positive=True):
    """Evaluate the effects and return a power score based on the modifiers."""
    power_score = 0
    if not effects:
        return power_score

    # Define patterns for different ways modifiers can be written
    patterns = {
        'Plague Infection': [r'Plague Infection', r'Infection Resistance'],
        'Injury Chance': [r'Injury Chance', r'Injury Resistance'],
        'Max Stamina': [r'Max Stamina'],
        'Max Health': [r'Max Health'],
        'Standing Rewards': [r'Standing Rewards'],
        'Meds Per Day': [r'Meds Per Day'],
        'Morale (Community)': [r'Morale \(Community\)']
    }

    # Define default power values for traits without explicit numbers
    default_values = {
        'Morale bonus': 2,  # Assign a power value of 2 for "Morale bonus ..." in default mode
        # Add more default values as needed
    }

    # Evaluate each effect
    for effect in effects.split('\n'):
        for priority in priorities:
            for pattern in patterns.get(priority, []):
                match = re.search(r'([+-]?\d+\.?\d*)\s*%?\s*' + pattern, effect)
                if match:
                    value = float(match.group(1))
                    if '%' in effect:
                        value = value / 100  # Convert percentage to a fraction
                    # Calculate the power score based on the priority index
                    priority_index = priorities.index(priority)
                    power_score += (len(priorities) - priority_index) * value if positive else -(len(priorities) - priority_index) * value

        # Check for default values if no explicit number is found
        for key, value in default_values.items():
            if key in effect:
                power_score += value if positive else -value

    return power_score

def main():
    input_file = 'Original_Traits_Power_Scores.csv'
    output_file = 'Processed_Traits_Power_Scores.csv'
    modes = ['default']  # Add other modes as needed

    data = read_csv(input_file)
    # Filter data to only include relevant columns
    filtered_data = [{key: row[key] for key in ['Name', 'Positive Effect(s)', 'Negative Effect(s)', 'Provided Hero Bonus']} for row in data]
    evaluated_data = evaluate_traits(filtered_data, modes)
    # Include only relevant fields in fieldnames
    fieldnames = ['Name', 'Positive Effect(s)', 'Negative Effect(s)', 'Provided Hero Bonus'] + [f'Power Score [{mode}]' for mode in modes]
    write_csv(output_file, evaluated_data, fieldnames)

if __name__ == '__main__':
    main()