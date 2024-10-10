import json
from deepdiff import DeepDiff

def compare_json_files(file1_path, file2_path):
    # Read the contents of both JSON files
    with open(file1_path, 'r') as file1:
        data1 = json.load(file1)
    
    with open(file2_path, 'r') as file2:
        data2 = json.load(file2)
    
    # Compare the two JSON objects using DeepDiff
    diff = DeepDiff(data1, data2, ignore_order=True, verbose_level=2)
    
    # Print the differences
    if diff:
        print("Differences found between the two JSON files:")
        print(diff)
        # Save the differences to a file
        if diff:
            with open('diff_output.json', 'w') as diff_file:
                json.dump(diff, diff_file, indent=2)
            print("Differences have been saved to 'diff_output.json'")
    else:
        print("No differences found between the two JSON files.")

# Usage
compare_json_files('Hashmap.json', 'client_structure.json')
