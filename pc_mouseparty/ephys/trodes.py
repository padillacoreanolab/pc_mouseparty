#!/usr/bin/env python3
"""
"""
import os
from collections import defaultdict
import pathlib


def parse_fields(field_str):
    """
    Parses a string of fields into a numpy data type object.

    The input string should be formatted as '<fieldname num*type>' or 
    '<fieldname type>'. This function parses the string, extracts the field 
    names and data types, and creates a numpy data type object which can be 
    used to read data from a binary file.

    Args:
        field_str (str): The string specifying the fields.

    Returns:
        np.dtype: A numpy data type object that describes the structure of 
                  the data.

    Raises:
        SystemExit: If the provided field type is not a valid numpy data type.
    """
    
    # Clean up the string and split it into components
    components = re.split('\s', re.sub(r"\>\<|\>|\<", ' ', field_str).strip())
    
    dtype_spec = []  # Will hold tuples to specify the numpy data type
    
    # Iterate over pairs of components (field name and type)
    for i in range(0, len(components), 2):
        field_name = components[i]
        
        # Default values
        repeat_count = 1
        field_type_str = 'uint32'
        
        # If the field type string contains a '*', it indicates a repeat count
        if '*' in components[i+1]:
            split_types = re.split('\*', components[i+1])
            # Handle both 'num*type' and 'type*num'
            field_type_str = split_types[split_types[0].isdigit()]
            repeat_count = int(split_types[split_types[1].isdigit()])
        else:
            field_type_str = components[i+1]
        
        # Convert the field type string to an actual numpy data type
        try:
            field_type = getattr(np, field_type_str)
        except AttributeError:
            print(f"{field_type_str} is not a valid field type.")
            exit(1)
        else:
            dtype_spec.append((str(field_name), field_type, repeat_count))
    
    return np.dtype(dtype_spec)


def read_trodes_extracted_data_file(filename):
    """
    Reads the content of a Trodes extracted data file.

    This function opens a Trodes file, reads the settings, parses them into a dictionary, 
    and then reads the remaining data in the file as a numpy array according to the 
    data types specified in the settings. If the settings block does not start correctly,
    it raises an Exception.

    Args:
        filename (str): The path to the Trodes file to be read.

    Returns:
        dict: A dictionary where keys are settings field names and values are the 
              corresponding setting values. The actual data from the file is stored 
              under the 'data' key as a numpy array.

    Raises:
        Exception: If the settings block in the file does not start with '<Start settings>'.
    """
    with open(filename, 'rb') as f:
        # The first line of the file should start the settings block
        if f.readline().decode('ascii').strip() != '<Start settings>':
            raise Exception("Settings format not supported")
        
        # Flag indicating we're reading the settings block
        fields = True
        # Dictionary to hold the settings fields and values
        fields_text = {}
        
        # Iterate over the lines in the file
        for line in f:
            # If we're still reading the settings block
            if fields:
                line = line.decode('ascii').strip()
                # If we've not reached the end of the settings block, continue reading fields
                if line != '<End settings>':
                    key, value = line.split(': ')
                    fields_text.update({key.lower(): value})
                # If we've reached the end of the settings block, stop reading fields
                else:
                    fields = False
                    # Parse the 'fields' setting to get the data type
                    dt = parse_fields(fields_text['fields'])
                    fields_text['data'] = np.zeros([1], dtype = dt)
                    break
        
        # Read the remaining data from the file using the parsed data type
        dt = parse_fields(fields_text['fields'])
        data = np.fromfile(f, dt)
        fields_text.update({'data': data})
        return fields_text
    

def organize_single_trodes_export(dir_path, skip_raw_group0=True):
    """
    Organizes Trodes data files in a given directory. The data is stored in a dictionary. 
    The key is the penultimate (second to last) part of the file name (i.e., the part before the last dot in the file name). 
    The values in the dictionary are the parsed data from the Trodes files.

    Args:
        dir_path (str): The path to the directory containing the Trodes files.
        skip_raw_group0(bool): To skip the "raw_group0" file which contains the raw signal which uses a lot of memory
    Returns:
        dict: A dictionary with organized Trodes file data.
    """
    # Initialize dictionary to store results
    result = {}
    
    # Iterate over all files in the directory
    for file_name in os.listdir(dir_path):

        if skip_raw_group0 and "raw_group0" in file_name:
            continue
        # Attempt to parse each file and store the data in the dictionary
        try:
            # Extract second to last part of the file name
            sub_dir_name = file_name.rsplit('.', 2)[-2]
            # Parse Trodes file and store the data
            result[sub_dir_name] = read_trodes_extracted_data_file(os.path.join(dir_path, file_name))

        # Skip files that cause errors during parsing
        except Exception as e:
            print(f"Skipping file {file_name} due to error: {e}")
            continue

    return result


def organize_all_trodes_export(dir_path):
    """
    Organize Trodes files in subdirectories based on prefix and suffix of the subdirectory.
    The function creates a dictionary with subdirectory prefix and suffix as keys,
    and the output of `organize_trodes_files_by_suffix` as values.

    Args:
        dir_path (str): Path of the directory to process.

    Returns:
        dict: Nested dictionary with keys as subdirectory prefix and suffix and values 
        containing data obtained from the `organize_trodes_files_by_suffix` function.
    """
    result = defaultdict(dict)
    
    for sub_dir_name in os.listdir(dir_path):
        # Construct the full path to the subdirectory
        sub_dir_path = os.path.join(dir_path, sub_dir_name)
        # Process only if it's a directory
        if os.path.isdir(sub_dir_path):
            try:
                # Split the subdirectory name by dots to extract prefix and suffix
                sub_dir_name_parts = sub_dir_name.split('.')
                sub_dir_name_prefix = sub_dir_name_parts[0]
                sub_dir_name_suffix = sub_dir_name_parts[-1]
                # Organize the Trodes files in the subdirectory and store the results
                result[sub_dir_name_prefix][sub_dir_name_suffix] = organize_single_trodes_export(sub_dir_path)
            except Exception as e:
                print(f"Error processing subdirectory {sub_dir_path}: {e}")
                continue

    return result