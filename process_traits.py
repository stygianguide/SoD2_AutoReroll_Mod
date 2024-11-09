import csv

def process_traits_power_scores(input_file, output_file):
    scores = {}

    # Read the CSV file and process the data
    with open(input_file, mode='r', newline='') as infile:
        reader = csv.reader(infile)
        next(reader)  # Skip the first row if it contains headers
        
        for row in reader:
            name, power = row
            # Remove the final letter and space if it exists
            base_name = name[:-2] if name[-2] == ' ' and name[-1] in 'ABCDE' else name
            try:
                power = int(power)
            except ValueError:
                continue  # Skip rows with invalid values
            # Update the score if it is lower than the previous one
            if base_name not in scores or power < scores[base_name]:
                scores[base_name] = power

    # Write the results to a new CSV file
    with open(output_file, mode='w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(['Name', 'Power'])  # Write headers
        for name, power in scores.items():
            writer.writerow([name, power])

# Use the function with the input and output files
input_file = 'Original_Traits_Power_Scores.csv'
output_file = 'Processed_Traits_Power_Scores.csv'
process_traits_power_scores(input_file, output_file)