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

def get_first_key_from_dictionary(input_dictionary):
    """
    Gets the first key from a dictionary.
    Usually used to get the dataframe from the nested dictionary
    created by medpc2excel.medpc_read.

    Args:
        input_dictionary: dict
            - A dictionary that you want to get the first key from

    Returns:
        str (usually)
            - First key to the inputted dictionary
    """
    # Turns the dictionary keys into a list and gets the first item
    return list(input_dictionary.keys())[0]


def get_medpc_dataframe_from_medpc_read_output(medpc_read_dictionary_output):
    """
    Gets the dataframe from the output from medpc2excel.medpc_read,
    that extracts data from a MED-PC file.
    This is done by getting the values of the nested dictionaries.

    Args:
        medpc_read_dictionary_output: Nested defaultdict
            - The output from medpc2excel.medpc_read.
            This contains the dataframe extracted from MED-PC file

    Returns:
        str(usually), str(usually), Pandas DataFrame
            - The data key to the medpc2excel.medpc_read output
            - The subject key to the medpc2excel.medpc_read
            - The dataframe extracted from the MED-PC file
    """
    date = get_first_key_from_dictionary(
        input_dictionary=medpc_read_dictionary_output
        )
    subject = get_first_key_from_dictionary(
        input_dictionary=medpc_read_dictionary_output[date]
        )
    # Dataframe must use both the date and subject key
    # with the inputted dictionary
    return date, subject, medpc_read_dictionary_output[date][subject]


def get_medpc_dataframe_from_list_of_files(medpc_files, stop_with_error=False):
    """
    Gets the dataframe from the output from medpc2excel.
    medpc_read that extracts data from a MED-PC file.
    This is done with multiple files from a list.
    And the date and the subject of the recording session is extracted as well.
    The data and subject metadata are added to the dataframe.
    And then all the dataframes for all the files are combined.

    Args:
        medpc_files: list
            - List of MED-PC recording files. Can be either relative
            or absolute paths.
        stop_with_error: bool
            - Flag to terminate the program when an error is raised.
            - Sometimes MED-PC files have incorrect formatting,
            so can be skipped over.
    Returns:
        Pandas DataFrame
            - Combined MED-PC DataFrame for all the files
            with the corresponding date and subject.
    """
    # List to combine all the Data Frames at the end
    all_medpc_df = []
    for file_path in medpc_files:
        try:
            # Reading in the MED-PC log file
            ts_df, medpc_log = medpc_read(
                file=file_path,
                override=True,
                replace=False
                )
            # Extracting the corresponding MED-PC Dataframe,
            # date, and subject ID
            date, subject, medpc_df = get_medpc_dataframe_from_medpc_read_output(
                medpc_read_dictionary_output=ts_df
                )
            medpc_df["date"] = date
            medpc_df["subject"] = subject
            medpc_df["file_path"] = file_path
            all_medpc_df.append(medpc_df)
        except Exception:
            # Printing out error messages and the corresponding traceback
            print(traceback.format_exc())
            if stop_with_error:
                # Stopping the program all together
                raise ValueError("Invalid Formatting for file: {}".format(file_path))
            else:
                # Continuing with execution
                print("Invalid Formatting for file: {}".format(file_path))
    return pd.concat(all_medpc_df)


def get_med_pc_meta_data(
    file_path,
    meta_data_headers=None,
    file_path_to_meta_data=None
):
    """
    Parses out the metadata from output of a MED-PC data file.
    The output file looks something like:
        Start Date: 05/04/22
        End Date: 05/04/22
        Subject: 4.4 (4)
        Experiment: Pilot of Pilot
        Group: Cage 4
        Box: 1
        Start Time: 13:06:15
        End Time: 14:10:05
        MSN: levelNP_CS_reward_laserepochON1st_noshock
    The metadata will be saved into a nested default dictionary.
    With the file path as the key, and the meta data headers as the values.
    And then the meta data headers are the nested keys,
    and the meta data as the values.

    The dictionary would look something like:
    defaultdict(dict,
            {'./data/2022-05-04_13h06m_Subject 4.4 (4).txt':
                {'File': 'C:\\MED-PC\\Data\\2022-05-04_13h06m_Subject4.4.txt',
              'Start Date': '05/04/22',
              'End Date': '05/04/22',
              'Subject': '4.4 (4)',
              'Experiment': 'Pilot of Pilot',
              'Group': 'Cage 4',
              'Box': '1',
              'Start Time': '13:06:15',
              'End Time': '14:10:05',
              'MSN': 'levelNP_CS_reward_laserepochON1st_noshock'}})

    Args:
        file_path: str
            - The path to the MED-PC data file
        meta_data_headers: list
            - List of the types of metadata to be parsed out for
            - Default metadata includes: "File", "Start Date",
            "End Date", "Subject", "Experiment", "Group",
            "Box", "Start Time", "End Time", "MSN"
        file_path_to_meta_data: Nested Default Dictionary
            - Any dictionary that has already been produced by this function
            that more metadata is chosen to be added to.
            The dictionary will have the file path as the key,
            and the meta data headers as the values.
            And then the meta data headers are the nested keys,
            and the meta data as the values.

    Returns:
        Nested Default Dictionary:
            - With the file path as the key,
            and the meta data headers as the values.
            And then the meta data headers are the nested keys,
            and the meta data as the values.
    """
    # The default metadata found in MED-PC files
    if meta_data_headers is None:
        meta_data_headers = [
            "File",
            "Start Date",
            "End Date",
            "Subject",
            "Experiment",
            "Group",
            "Box",
            "Start Time",
            "End Time",
            "MSN"
            ]
    # Creating a new dictionary if none is inputted
    if file_path_to_meta_data is None:
        file_path_to_meta_data = defaultdict(dict)

    # List of all the headers that we've gone through
    used_headers = []
    # Going through each line of the MED-PC data file
    with open(file_path, 'r') as file:
        for line in file.readlines():
            # Checking to see if we've gone through all the headers or not
            if set(meta_data_headers) == set(used_headers):
                break
            # Going through each header to see which line
            # starts with the header
            for header in meta_data_headers:
                if line.strip().startswith(header):
                    # Removing all unnecessary characters
                    file_path_to_meta_data[file_path][header] = line.strip().replace(header, '').strip(":").strip()
                    used_headers.append(header)
                    # Move onto next line if header is found
                    break
    return file_path_to_meta_data


def get_all_med_pc_meta_data_from_files(
    list_of_files,
    meta_data_headers=None,
    file_path_to_meta_data=None
):
    """
    Iterates through a list of MED-PC files to extract
    all the metadata from those files

    Args:
        list_of_files: list
            - A list of file paths
            (not names, must be relative or absolute path)
            of MED-PC output files
            - We recommend using glob.glob("./path_to_files/*txt")
            to get list of files
        meta_data_headers: list
            - List of the types of metadata to be parsed out for
            - Default metadata includes: "File", "Start Date", "End Date",
            "Subject", "Experiment", "Group", "Box",
            "Start Time", "End Time", "MSN"
        file_path_to_meta_data: Nested Default Dictionary
            - Any dictionary that has already been produced by
            this function that more metadata is chosen to be added to.
            The dictionary will have the file path as the key,
            and the meta data headers as the values.
            And then the meta data headers are the nested keys,
            and the meta data as the values.

    Returns:
        Nested Default Dictionary:
            - With the file path as the key,
            and the meta data headers as the values.
            And then the meta data headers are the nested keys,
            and the meta data as the values.
    """
    # Creating a new dictionary if none is inputted
    if file_path_to_meta_data is None:
        file_path_to_meta_data = defaultdict(dict)

    for file_path in list_of_files:
        # Parsing out the metadata from MED-PC files
        try:
            file_path_to_meta_data = get_med_pc_meta_data(
                file_path=file_path,
                meta_data_headers=meta_data_headers,
                file_path_to_meta_data=file_path_to_meta_data
                )
        # Except in case file can not be read or is missing
        except Exception:
            print("Please review contents of {}".format(file_path))
    return file_path_to_meta_data


def get_all_port_entry_increments(port_entry_scaled, port_exit_scaled):
    """
    Gets all the numbers that are in the duration
    of the port entry and port exit times.
    i.e. If the port entry was 7136 and port exit was 7142, we'd get:
    [7136, 7137, 7138, 7139, 7140, 7141, 7142]
    This is done for all port entry and port exit times
    pairs between two Pandas Series

    Args:
        port_entry_scaled: Pandas Series
            - A column from a MED-PC Dataframe that has all
            the port entry times scaled
            (usually with the scale_time_to_whole_number function)
        port_exit_scaled: Pandas Series
            - A column from a MED-PC Dataframe that has all
            the port exit times scaled
            (usually with the scale_time_to_whole_number function)
    Returns:
        Numpy array:
            - 1D Numpy Array of all the numbers that are in the
            duration of all the port entry and port exit times
    """
    all_port_entry_ranges = [
        np.arange(port_entry, port_exit+1) for port_entry, port_exit in zip(port_entry_scaled, port_exit_scaled)
        ]
    return np.concatenate(all_port_entry_ranges)


def get_inside_port_mask(inside_port_numbers, max_time):
    """
    Gets a mask of all the times that the subject is inside the port.
    First a range of number from 1 to the number for the max time is created.
    Then, a mask is created by seeing which numbers
    are within the inside port duration

    Args:
        max_time: int
            - The number that represents the largest number for the time.
                - Usually this will be the number for the last tone played.
            - We recommend adding 2001 if you are just
            using the number for the last tone played
                - This is because we are looking 20 seconds before and after.
                - And 20 seconds becomes 2000 when scaled with our method.
        inside_port_numbers: Numpy Array
            - All the increments of of the duration that the
            subject is within the port
    Returns:
        session_time_increments: Numpy Array
            - Range of number from 1 to max time
        inside_port_mask: Numpy Array
            - The mask of True or False if the subject is in
            the port during the time of that index
    """
    if max_time is None:
        max_time = inside_port_numbers.max()
    session_time_increments = np.arange(1, max_time+1)
    inside_port_mask = np.isin(session_time_increments, inside_port_numbers)
    return session_time_increments, inside_port_mask


def get_inside_port_probability_averages_for_all_increments(tone_times, inside_port_mask, before_tone_duration=2000, after_tone_duration=2000):
    """
    Calculates the average probability that a
    subject is in the port between sessions.
    This is calculated by seeing the ratio that a
    subject is in the port at a given time increment
    that's the same time difference to the tone with all the other sessions.
    i.e. The time increment of 10.01 seconds after the tone for all sessions.

    Args:
        tone_times: list or Pandas Series
            - An array of the times that the tone has played
        inside_port_mask: Numpy Array
            - The mask where the subject is in the port based on the
            index being the time increment
        before_tone_duration: int
            - The number of increments before the tone to be analyzed
        after_tone_duration: int
            - The number of increments after the tone to be analyzed
    Returns:
        Numpy Array
            - The averages of the probabilities that the subject
            is inside the port for all increments
    """
    result = []
    for tone_start in tone_times:
        tone_start_int = int(tone_start)
        result.append(inside_port_mask[tone_start_int - before_tone_duration: tone_start_int + after_tone_duration])
    return np.stack(result).mean(axis=0)


def get_max_tone_number(tone_pd_series):
    """
    Gets the index, and the number for valid tones in MED-PC's outputted data.
    The recorded tones produce numbers that are divisible by 1000 after the
    recorded data.
    You can use the index to remove these unnecessary numbers by indexing
    until that number.

    Args:
        tone_pd_series: Pandas Series
            - A column from the dataframe that contains the data from MED-PC's
            output file
            - Usually created with dataframe_variable["(S)CSpresentation"]
    Returns:
        int, float
            - The index of the max tone number. This number can be used to
            index the tone_pd_series to remove unnecessary numbers.
            - The max tone number. This number can be used to verify whether
            or not the tone_pd_series had unnecessary numbers.
    """
    for index, num in enumerate(tone_pd_series):
        if num % 1000 == 0:
            return index, num
    return index, num


def get_valid_tones(tone_pd_series, drop_1000s=True, dropna=True):
    """
    Removes all unnecessary numbers from a Pandas Series of tone times
    extracted from MED-PC's dataframe.
    The unnecessary numbers are added after recorded tone times. These numbers
    are usually divisible by 1000.
    NaNs are also added after that. So we will remove all tone times entries
    that meet either of these criterias.

    Args:
        tone_pd_series: Pandas Series
        dropna: bool
            - Whether or not you want to remove NaNs from tone_pd_series.
            - Usually a good idea because MED-PC adds NaNs to the tone time
            column.
    Returns:
        Pandas series
            - The tone times with unnecessary numbers and NaNs removed
    """
    if dropna:
        tone_pd_series = tone_pd_series.dropna()
    if drop_1000s:
        # Getting the index of the tone time that is divisible by 1000
        max_tone_index, max_tone_number = get_max_tone_number(tone_pd_series=tone_pd_series)
        tone_pd_series = tone_pd_series[:max_tone_index]
    # Removing all numbers that are after the max tone
    return tone_pd_series


def get_first_port_entries_after_tone(
    tone_pd_series,
    port_entries_pd_series,
    port_exits_pd_series
):
    """
    From an array of times of tones being played and subject's entries to a
    port,
    finds the first entry immediately after every tone.
    Makes a dataframe of tone times to first port entry times

    Args:
        tone_pd_series: Pandas Series
            - All the times the tone is being played
        port_entries_pd_series: Pandas Series
            - All the times that the port is being entered
    Returns:
        Pandas DataFrame
            - A dataframe of tone times to first port entry times
    """
    # Creating a dictionary of index(current row number we're on) to
    # current/next tone time and first port entry
    first_port_entry_dict = defaultdict(dict)
    for index, current_tone_time in tone_pd_series.items():
        # Using a counter so that we don't go through all the rows that
        # include NaNs
        try:
            first_port_entry_dict[index]["current_tone_time"] = current_tone_time
            # Getting all the port entries that happened after the tone started
            # And then getting the first one of those port entries
            first_port_entry_after_tone = port_entries_pd_series[port_entries_pd_series >= current_tone_time].min()
            first_port_entry_dict[index]["first_port_entry_after_tone"] = first_port_entry_after_tone
            # Getting all the port exits that happened after the entery
            # And then getting the first one of those port exits
            port_exit_after_first_port_entry_after_tone = port_exits_pd_series[port_exits_pd_series > first_port_entry_after_tone].min()
            first_port_entry_dict[index]["port_exit_after_first_port_entry_after_tone"] = port_exit_after_first_port_entry_after_tone
        except Exception:
            print("Look over value {} at index {}".format(current_tone_time, index))
    return pd.DataFrame.from_dict(first_port_entry_dict, orient="index")


def get_last_port_entries_before_tone(tone_pd_series, port_entries_pd_series, port_exits_pd_series):
    """
    From an array of times of tones being played and subject's entries to a port,
    finds the first entry immediately after every tone.
    Makes a dataframe of tone times to first port entry times

    Args:
        tone_pd_series: Pandas Series
            - All the times the tone is being played
        port_entries_pd_series: Pandas Series
            - All the times that the port is being entered
    Returns:
        Pandas DataFrame
            - A dataframe of tone times to first port entry times
    """
    # Creating a dictionary of index(current row number we're on) to current/next tone time and first port entry
    last_port_entry_dict = defaultdict(dict)
    for index, current_tone_time in tone_pd_series.items():
        # Using a counter so that we don't go through all the rows that include NaNs
        try:
            last_port_entry_dict[index]["current_tone_time"] = current_tone_time
            # Getting all the port entries that happened after the tone started
            # And then getting the first one of those port entries
            last_port_entry_before_tone = port_entries_pd_series[port_entries_pd_series <= current_tone_time].max()
            last_port_entry_dict[index]["last_port_entry_before_tone"] = last_port_entry_before_tone
            # Getting all the port exits that happened after the entery
            # And then getting the first one of those port exits
            port_exit_after_last_port_entry_before_tone = port_exits_pd_series[port_exits_pd_series > last_port_entry_before_tone].min()
            last_port_entry_dict[index]["port_exit_after_last_port_entry_before_tone"] = port_exit_after_last_port_entry_before_tone
        except Exception:
            print("Look over value {} at index {}".format(current_tone_time, index))
    return pd.DataFrame.from_dict(last_port_entry_dict, orient="index")


def get_concatted_first_porty_entry_after_tone_dataframe(
    concatted_medpc_df,
    tone_time_column="(S)CSpresentation",
    port_entry_column="(P)Portentry",
    port_exit_column="(N)Portexit",
    subject_column="subject",
    date_column="date",
    stop_with_error=False
):
    """
    Creates dataframes of the time of the tone, and the first port entry after
    that tone.
    Along with the corresponding metadata of the path of the file, the date,
    and the subject.
    This is created from a dataframe that contains tone times, port entry
    times, and associated metadata.
    Which is usually from the extract.dataframe.
    get_medpc_dataframe_from_list_of_files function

    Args:
        concatted_medpc_df: Pandas Dataframe
            - Output of
            extract.dataframe.get_medpc_dataframe_from_list_of_files
            - Includes tone playing time, port entry time, subject,
            and date for each recording session
        tone_time_column: str
            - Name of the column of concatted_medpc_df that has the array port
            entry times
        port_entry_column: str
            - Name of the column of concatted_medpc_df that has the array port
            entry times
        subject_column: str
            - Name of the column of concatted_medpc_df that has the subject's
            ID
        date_column: str
            - Name of the column of concatted_medpc_df that has the date of
            the recording
        stop_with_error: bool
            - Flag to terminate the program when an error is raised.
            - Sometimes recordings can be for testing and don't include any
            valid tone times

    Returns:
        Pandas Dataframe
            -
    """
    # List to combine all the Data Frames at the end
    all_first_port_entry_df = []
    for file_path in concatted_medpc_df["file_path"].unique():
        current_file_df = concatted_medpc_df[concatted_medpc_df["file_path"] == file_path]
        valid_tones = get_valid_tones(
            tone_pd_series=current_file_df[tone_time_column]
            )
        # Sometimes the valid tones do not exist because it was a
        # test recording
        if not valid_tones.empty:
            # All the first port entries for each tone
            first_port_entry_df = get_first_port_entries_after_tone(
                tone_pd_series=valid_tones,
                port_entries_pd_series=current_file_df[port_entry_column],
                port_exits_pd_series=current_file_df[port_exit_column]
                )
            # Adding the metadata as columns
            first_port_entry_df["file_path"] = file_path
            # Making sure that there is only one date and
            # subject for all the rows
            if len(current_file_df[date_column].unique()) == 1 and len(current_file_df[subject_column].unique()) == 1:
                # This assumes that all the date and subject keys are the same for the file
                first_port_entry_df[date_column] = current_file_df[date_column].unique()[0]
                first_port_entry_df[subject_column] = current_file_df[subject_column].unique()[0]
            elif stop_with_error:
                raise ValueError("More then one date or subject in {}".format(file_path))
            else:
                print("More then one date or subject in {}".format(file_path))
            all_first_port_entry_df.append(first_port_entry_df)
        elif valid_tones.empty and stop_with_error:
            raise ValueError("No valid tones for {}".format(file_path))
        else:
            print("No valid tones for {}".format(file_path))
    # Index repeats itself because it is concatenated with multiple dataframes
    return pd.concat(all_first_port_entry_df).reset_index(drop="True")


def get_concatted_last_porty_entry_before_tone_dataframe(
    concatted_medpc_df,
    tone_time_column="(S)CSpresentation",
    port_entry_column="(P)Portentry",
    port_exit_column="(N)Portexit",
    subject_column="subject",
    date_column="date",
    stop_with_error=False
):
    """
    Creates dataframes of the time of the tone, and the first port entry after
    that tone.
    Along with the corresponding metadata of the path of the file, the date,
    and the subject.
    This is created from a dataframe that contains tone times,
    port entry times,
    and associated metadata.
    Which is usually from the
    extract.dataframe.get_medpc_dataframe_from_list_of_files function

    Args:
        concatted_medpc_df: Pandas Dataframe
            - Output of
            extract.dataframe.get_medpc_dataframe_from_list_of_files
            - Includes tone playing time, port entry time, subject,
            and date for each recording session
        tone_time_column: str
            - Name of the column of concatted_medpc_df that has the array port
            entry times
        port_entry_column: str
            - Name of the column of concatted_medpc_df that has the array port
            entry times
        subject_column: str
            - Name of the column of concatted_medpc_df that has the subject's
            ID
        date_column: str
            - Name of the column of concatted_medpc_df that has the date of
            the recording
        stop_with_error: bool
            - Flag to terminate the program when an error is raised.
            - Sometimes recordings can be for testing and don't include any
            valid tone times

    Returns:
        Pandas Dataframe
            -
    """
    # List to combine all the Data Frames at the end
    all_last_port_entry_df = []
    for file_path in concatted_medpc_df["file_path"].unique():
        current_file_df = concatted_medpc_df[concatted_medpc_df["file_path"] == file_path]
        valid_tones = get_valid_tones(
            tone_pd_series=current_file_df[tone_time_column]
            )
        # Sometimes the valid tones do not exist because it was a
        # test recording
        if not valid_tones.empty:
            # All the first port entries for each tone
            last_port_entry_df = get_last_port_entries_before_tone(
                tone_pd_series=valid_tones,
                port_entries_pd_series=current_file_df[port_entry_column],
                port_exits_pd_series=current_file_df[port_exit_column]
                )
            # Adding the metadata as columns
            last_port_entry_df["file_path"] = file_path
            # Making sure that there is only one date and subject
            # for all the rows
            if len(current_file_df[date_column].unique()) == 1 and len(current_file_df[subject_column].unique()) == 1:
                # This assumes that all the date and subject keys are the same for the file
                last_port_entry_df[date_column] = current_file_df[date_column].unique()[0]
                last_port_entry_df[subject_column] = current_file_df[subject_column].unique()[0]
            elif stop_with_error:
                raise ValueError("More then one date or subject in {}".format(file_path))
            else:
                print("More then one date or subject in {}".format(file_path))
            all_last_port_entry_df.append(last_port_entry_df)
        elif valid_tones.empty and stop_with_error:
            raise ValueError("No valid tones for {}".format(file_path))
        else:
            print("No valid tones for {}".format(file_path))
    # Index repeats itself because it is concatenated with multiple dataframes
    return pd.concat(all_last_port_entry_df).reset_index(drop="True")


def get_info(filename):
    with h5py.File(filename, "r") as f:
        dset_names = list(f.keys())
        locations = f["tracks"][:].T
        node_names = [n.decode() for n in f["node_names"][:]]
        track_names = [n.decode() for n in f["track_names"][:]]
    return dset_names, locations, node_names, track_names


