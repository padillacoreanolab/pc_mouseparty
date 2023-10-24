import os
import glob
import numpy as np
import pandas as pd
import spikeinterface.extractors as se
import spikeinterface.preprocessing as sp

OUTPUT_DIR = r"./proc/"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CHANNEL_MAPPING_DF = pd.read_excel("../../data/channel_mapping.xlsx")
TONE_TIMESTAMP_DF = pd.read_excel("../../data/rce_tone_timestamp.xlsx", index_col=0)

#hyper params
EPHYS_SAMPLING_RATE = 20000
LFP_SAMPLING_RATE = 1000
TRIAL_DURATION = 10
FRAME_RATE = 22
ECU_STREAM_ID = "ECU"
TRODES_STREAM_ID = "trodes"
LFP_FREQ_MIN = 0.5
LFP_FREQ_MAX = 300
ELECTRIC_NOISE_FREQ = 60
RECORDING_EXTENTION = "*.rec"

#searches for all .rec files in the data folder
ALL_SESSION_DIR = glob.glob("/scratch/back_up/reward_competition_extention/data/omission/*/*.rec")

def compute_sorted_index(group, value_column='Value', index_column='SortedIndex'):
    """
    Computes the index of each row's value within its sorted group.

    Parameters:
    - group (pd.DataFrame): A group of data.
    - value_column (str): Name of the column containing the values to be sorted.
    - index_column (str): Name of the new column that will contain the indices.

    Returns:
    - pd.DataFrame: The group with an additional column containing the indices.
    """
    #transform a column of categorical data into numerical indices based on the order of appearance in the sorted unique values
    #encoding categorical data in machine learning
    sorted_values = sorted(list(set(group[value_column].tolist())))
    group[index_column] = group[value_column].apply(lambda x: sorted_values.index(x))
    return group

#reformatting
def reformat_df():
    all_trials_df = TONE_TIMESTAMP_DF.dropna(subset="condition").reset_index(drop=True)
    sorted(all_trials_df["recording_dir"].unique())

    all_trials_df["video_frame"] = all_trials_df["video_frame"].astype(int)
    all_trials_df["video_name"]  = all_trials_df["video_file"].apply(lambda x: x.strip(".videoTimeStamps.cameraHWSync"))

    # using different id extractions for different file formats
    # id file name --> look megan code
    all_trials_df["all_subjects"] = all_trials_df["recording_dir"].apply(lambda x: x if "2023" in x else "subj" + "_".join(x.split("_")[-5:]))
    all_trials_df["all_subjects"] = all_trials_df["all_subjects"].apply(lambda x: tuple(sorted([num.strip("_").replace("_",".") for num in x.replace("-", "_").split("subj")[-1].strip("_").split("and")])))
    all_trials_df["all_subjects"].unique()

    all_trials_df["current_subject"] = all_trials_df["subject_info"].apply(lambda x: ".".join(x.replace("-","_").split("_")[:2])).astype(str)
    all_trials_df["current_subject"].unique()

    #converting trial label to win or los based on which subject won trial
    all_trials_df["trial_outcome"] = all_trials_df.apply(
        lambda x: "win" if str(x["condition"]).strip() == str(x["current_subject"])
                 else ("lose" if str(x["condition"]) in x["all_subjects"]
                       else x["condition"]), axis=1)
    all_trials_df["trial_outcome"].unique()
    #TODO: what is competition closeness?
    competition_closeness_map = {k: "non_comp" if "only" in str(k).lower() else "comp" if type(k) is str else np.nan for k in all_trials_df["competition_closeness"].unique()}
    all_trials_df["competition_closeness"] = all_trials_df["competition_closeness"].map(competition_closeness_map)
    all_trials_df["competition_closeness"] = all_trials_df.apply(lambda x: "_".join([str(x["trial_outcome"]), str(x["competition_closeness"])]).strip("nan").strip("_"), axis=1)
    all_trials_df["competition_closeness"].unique()

    all_trials_df["lfp_index"] = (all_trials_df["time_stamp_index"] // (EPHYS_SAMPLING_RATE/LFP_SAMPLING_RATE)).astype(int)

    all_trials_df["time"] = all_trials_df["time"].astype(int)
    all_trials_df["time_stamp_index"] = all_trials_df["time_stamp_index"].astype(int)

    all_trials_df = all_trials_df.drop(columns=["state", "din", "condition", "Unnamed: 13"], errors="ignore")

    #handleing time stamps
    #TODO: timestamp or frame ranges relative to LFP, ephys, and video frames.
    all_trials_df["baseline_lfp_timestamp_range"] = all_trials_df["lfp_index"].apply(
        lambda x: (x - TRIAL_DURATION * LFP_SAMPLING_RATE, x))
    all_trials_df["trial_lfp_timestamp_range"] = all_trials_df["lfp_index"].apply(
        lambda x: (x, x + TRIAL_DURATION * LFP_SAMPLING_RATE))
    all_trials_df["baseline_ephys_timestamp_range"] = all_trials_df["time_stamp_index"].apply(
        lambda x: (x - TRIAL_DURATION * EPHYS_SAMPLING_RATE, x))
    all_trials_df["trial_ephys_timestamp_range"] = all_trials_df["time_stamp_index"].apply(
        lambda x: (x, x + TRIAL_DURATION * EPHYS_SAMPLING_RATE))
    all_trials_df["baseline_videoframe_range"] = all_trials_df["video_frame"].apply(
        lambda x: (x - TRIAL_DURATION * FRAME_RATE, x))
    all_trials_df["trial_videoframe_range"] = all_trials_df["video_frame"].apply(
        lambda x: (x, x + TRIAL_DURATION * FRAME_RATE))
    return all_trials_df

all_trials_df = reformat_df()

def extract_lfp():
    # Going through all the recording sessions
    recording_name_to_all_ch_lfp = {}
    for session_dir in ALL_SESSION_DIR:
        # Going through all the recordings in each session
        for recording_path in glob.glob(os.path.join(session_dir, RECORDING_EXTENTION)):
            #assumes subject name in file name
            try:
                recording_basename = os.path.splitext(os.path.basename(recording_path))[0]
                # checking to see if the recording has an ECU component
                # if it doesn't, then the next one be extracted
                current_recording = se.read_spikegadgets(recording_path, stream_id=ECU_STREAM_ID)
                current_recording = se.read_spikegadgets(recording_path, stream_id=TRODES_STREAM_ID)
                print(recording_basename)
                # Preprocessing the LFP
                # higher than 300 is action potential and lower than 0.5 is noise
                current_recording = sp.bandpass_filter(current_recording, freq_min=LFP_FREQ_MIN, freq_max=LFP_FREQ_MAX)
                current_recording = sp.notch_filter(current_recording, freq=ELECTRIC_NOISE_FREQ)
                current_recording = sp.resample(current_recording, resample_rate=LFP_SAMPLING_RATE)
                current_recording = sp.zscore(current_recording) # zscore single because avg across animals is in same scale
                recording_name_to_all_ch_lfp[recording_basename] = current_recording
            except Exception as error:
                # handle the exception
                print("An exception occurred:", error)  # An exception occurred: division by zero
    return recording_name_to_all_ch_lfp

recording_name_to_all_ch_lfp = extract_lfp()

all_trials_df = all_trials_df[all_trials_df["recording_file"].isin(recording_name_to_all_ch_lfp.keys())].reset_index(drop=True)
all_trials_df = all_trials_df.groupby('recording_file').apply(lambda g: compute_sorted_index(g, value_column='time', index_column='trial_number')).reset_index(drop=True)
all_trials_df["trial_number"] = all_trials_df["trial_number"] + 1

#adding the LFP trace information
CHANNEL_MAPPING_DF["Subject"] = CHANNEL_MAPPING_DF["Subject"].astype(str)
channel_map_and_all_trials_df = all_trials_df.merge(CHANNEL_MAPPING_DF, left_on="current_subject", right_on="Subject", how="left")
channel_map_and_all_trials_df = channel_map_and_all_trials_df.drop(columns=[col for col in channel_map_and_all_trials_df.columns if "eib" in col], errors="ignore")
channel_map_and_all_trials_df = channel_map_and_all_trials_df.drop(columns=["Subject"], errors="ignore")
channel_map_and_all_trials_df.to_csv("./proc/trial_metadata.csv")
channel_map_and_all_trials_df.to_pickle("./proc/trial_metadata.pkl")

#link lfp to trials
channel_map_and_all_trials_df["all_ch_lfp"] = channel_map_and_all_trials_df["recording_file"].map(recording_name_to_all_ch_lfp)
#new row for brain region
brain_region_col = [col for col in CHANNEL_MAPPING_DF if "spike_interface" in col]
id_cols = [col for col in channel_map_and_all_trials_df.columns if col not in brain_region_col]
for col in brain_region_col:
    channel_map_and_all_trials_df[col] = channel_map_and_all_trials_df[col].astype(int).astype(str)
    channel_map_and_all_trials_df["{}_baseline_lfp_trace".format(col.strip("spike_interface").strip("_"))] = channel_map_and_all_trials_df.apply(lambda row: row["all_ch_lfp"].get_traces(channel_ids=[row[col]], start_frame=row["baseline_lfp_timestamp_range"][0], end_frame=row["baseline_lfp_timestamp_range"][1]).T[0], axis=1)
    channel_map_and_all_trials_df["{}_trial_lfp_trace".format(col.strip("spike_interface").strip("_"))] = channel_map_and_all_trials_df.apply(lambda row: row["all_ch_lfp"].get_traces(channel_ids=[row[col]], start_frame=row["trial_lfp_timestamp_range"][0], end_frame=row["trial_lfp_timestamp_range"][1]).T[0], axis=1)
channel_map_and_all_trials_df = channel_map_and_all_trials_df.drop(columns=["all_ch_lfp"], errors="ignore")
channel_map_and_all_trials_df.to_pickle("./proc/full_baseline_and_trial_lfp_traces.pkl")


# spectogram -- power over time and freq --heatmap -- spectral_connectivity
    # sliding window
# pow correlation -- power on windows -- two brain regions -- correlation (up or down power together)
    # pow in 1 sec windows across tone times
    # pow across interactions  -- scatter plot
    # window size = 1 - 2 seconds
    # really small window size -- gamma (more time res on gamma)

# power -- amplitude across freq -- spectral_connectivity
# coherence -- phase consistency of two regions
    # phase = hill vs trough
    # "how much they line up over time"
    # func tells how much of signal is predictive of other signal
    # coherence = 1 -- signals are perfectly lined up
    # coherence = 0.5 -- signals are not lined up at all
    # coherence = 0 -- signals are perfectly out of phase
    # coherence = 1 - 0.5 or 0.5 - 0 -- signals are in phase
    # time lag -- how much time is between signals

