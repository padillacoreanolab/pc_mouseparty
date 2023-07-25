import os
import re
import operator
import traceback
import warnings
import pathlib
import h5py
import math
import numpy as np
import pandas as pd
import moviepy.editor as mpy
from moviepy.editor import *
from medpc2excel.medpc_read import medpc_read
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
from collections import defaultdict


def update_trodes_file_to_data(file_path, file_to_data=None):
    """
    Get the data/metadata froma a Trodes recording file.
    Save it to a dictionary with the file name as the key.
    And the name of the data/metadata(sub-key)
    and the data/metadata point(sub-value) as a subdictionary for the value.

    Args:
        file_path(str): Path of the Trodes recording file.
        Can be relative or absolute path.
        file_to_data(dict): Dictionary that had the
        trodes file name as the key and the data/metadata as the value.

    Returns:
        Dictionary that has file name keys with a subdictionary of
        all the different data/metadata from the Trodes recording file.
    """
    # Creating a new dictionary if none is inputted
    if file_to_data is None:
        file_to_data = defaultdict(dict)
    # Getting just the file name to use as the key
    file_name = os.path.basename(file_path)
    # Getting the absolute file path as metadata
    absolute_file_path = os.path.abspath(file_path)
    try:
        # Reading in the Trodes recording file with the function
        trodes_recording = parse_exported_file(absolute_file_path)

        file_prefix = get_all_file_suffixes(file_name)
        print("file prefix: {}".format(file_prefix))
        file_to_data[file_prefix] = trodes_recording
        file_to_data[file_prefix]["absolute_file_path"] = absolute_file_path
        return file_to_data
    except Exception:
        # TODO: Fix format so that file path is included in warning
        warnings.warn("Can not process {}".format(absolute_file_path))
        return None
    

def get_all_trodes_data_from_directory(parent_directory_path="."):
    """
    Goes through all the files in a directory created by Trodes.
    Each file is organized into a dictionary that is directory name to
    the file name to associated data/metadata of the file.
    The structure would look something like:
    result[current_directory_name][file_name][data_type]

    Args:
        parent_directory_path(str): Path of the directory that contains the
        Trodes recording files. Can be relative or absolute path.

    Returns:
        Dictionary that has the Trodes directory name as the key
        and a subdictionary as the values.
        This subdictionary has all the files as keys with the corresponding
        data/metadata from the Trodes recording file as values.
    """
    directory_to_file_to_data = defaultdict(dict)
    # Going through each directory
    for item in os.listdir(parent_directory_path):
        item_path = os.path.join(parent_directory_path, item)
        # Getting the directory name to save as the key
        if os.path.isdir(item_path):
            current_directory_name = os.path.basename(item_path)
        # If the item is a file instead of a directory
        else:
            current_directory_name = "."
        directory_prefix = get_all_file_suffixes(current_directory_name)

        current_directory_path = os.path.join(
            parent_directory_path,
            current_directory_name
            )
        # Going through each file in the directory
        for file_name in os.listdir(current_directory_path):
            file_path = os.path.join(current_directory_path, file_name)
            if os.path.isfile(file_path):
                # Creating a sub dictionary that has file keys and a sub-sub dictionary of data type to data value 
                current_directory_to_file_to_data = update_trodes_file_to_data(file_path=file_path, file_to_data=directory_to_file_to_data[current_directory_name])
                # None will be returned if the file can not be processed
                if current_directory_to_file_to_data is not None:
                    print("directory prefix: {}".format(directory_prefix))
                    directory_to_file_to_data[directory_prefix] = current_directory_to_file_to_data
    return directory_to_file_to_data

