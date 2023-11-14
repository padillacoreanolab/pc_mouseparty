import os
import glob
import numpy as np
import pandas as pd
import spikeinterface.extractors as se
import spikeinterface.preprocessing as sp

class LFPrecordingCollection:
    def __init__(self,
                 path,
                 tone_timestamp_df,
                 channel_mapping_df,
                 all_sessions_path,
                 ephys_sampling_rate,
                 lfp_sampling_rate,
                 trial_duration,
                 frame_rate=22,
                 pickle_path="./proc/full_baseline_and_trial_lfp_traces.pkl",
                 recording_extention="*.rec",
                 lfp_freq_min=0.5,
                 lfp_freq_max=300,
                 electric_noise_freq=60,
                 ecu_stream_id="ECU",
                 trodes_stream_id = "trodes"):

        self.ephys_sampling_rate = ephys_sampling_rate
        self.lfp_sampling_rate = lfp_sampling_rate
        self.frame_rate = frame_rate
        self.trial_duration = trial_duration
        self.recording_extention = recording_extention
        self.path = path
        self.lfp_freq_min = lfp_freq_min
        self.lfp_freq_max = lfp_freq_max
        self.electric_noise_freq = electric_noise_freq
        self.ecu_stream_id = ecu_stream_id
        self.trodes_stream_id = trodes_stream_id

        self.tone_timestamp_df = pd.read_excel(tone_timestamp_df, index_col=0)
        self.channel_mapping_df = pd.read_excel(channel_mapping_df)

        self.all_trials_df = self.reformat_df()

        self.recording_name_to_all_ch_lfp = self.extract_lfp()
        self.all_sessions_dir = glob.glob(all_sessions_path)

        self.channel_map_and_all_trials_df = self.add_lfp_trace()

        self.pickle = self.channel_map_and_all_trials_df.to_pickle(pickle_path)

    def reformat_df(self):
        all_trials_df = self.tone_timestamp_df.dropna(subset="condition").reset_index(drop=True)
        sorted(all_trials_df["recording_dir"].unique())

        all_trials_df["video_frame"] = all_trials_df["video_frame"].astype(int)
        all_trials_df["video_name"] = all_trials_df["video_file"].apply(
            lambda x: x.strip(".videoTimeStamps.cameraHWSync"))

        # using different id extractions for different file formats
        # id file name --> look megan code
        all_trials_df["all_subjects"] = all_trials_df["recording_dir"].apply(
            lambda x: x if "2023" in x else "subj" + "_".join(x.split("_")[-5:]))
        all_trials_df["all_subjects"] = all_trials_df["all_subjects"].apply(lambda x: tuple(sorted(
            [num.strip("_").replace("_", ".") for num in
             x.replace("-", "_").split("subj")[-1].strip("_").split("and")])))
        all_trials_df["all_subjects"].unique()

        all_trials_df["current_subject"] = all_trials_df["subject_info"].apply(
            lambda x: ".".join(x.replace("-", "_").split("_")[:2])).astype(str)
        all_trials_df["current_subject"].unique()

        # converting trial label to win or los based on which subject won trial
        all_trials_df["trial_outcome"] = all_trials_df.apply(
            lambda x: "win" if str(x["condition"]).strip() == str(x["current_subject"])
            else ("lose" if str(x["condition"]) in x["all_subjects"]
                  else x["condition"]), axis=1)
        all_trials_df["trial_outcome"].unique()
        # TODO: what is competition closeness?
        competition_closeness_map = {k: "non_comp" if "only" in str(k).lower() else "comp" if type(k) is str else np.nan
                                     for k in all_trials_df["competition_closeness"].unique()}
        all_trials_df["competition_closeness"] = all_trials_df["competition_closeness"].map(competition_closeness_map)
        all_trials_df["competition_closeness"] = all_trials_df.apply(
            lambda x: "_".join([str(x["trial_outcome"]), str(x["competition_closeness"])]).strip("nan").strip("_"),
            axis=1)
        all_trials_df["competition_closeness"].unique()

        # STANDARDIZED STARTS HERE
        all_trials_df["lfp_index"] = (
                    all_trials_df["time_stamp_index"] // (self.ephys_sampling_rate / self.lfp_sampling_rate)).astype(int)

        all_trials_df["time"] = all_trials_df["time"].astype(int)
        all_trials_df["time_stamp_index"] = all_trials_df["time_stamp_index"].astype(int)

        # ECU SPECIFIC does not need to happen
        all_trials_df = all_trials_df.drop(columns=["state", "din", "condition", "Unnamed: 13"], errors="ignore")

        # handleing time stamps
        # TODO: timestamp or frame ranges relative to LFP, ephys, and video frames.
        all_trials_df["baseline_lfp_timestamp_range"] = all_trials_df["lfp_index"].apply(
            lambda x: (x - self.trial_duration * self.lfp_sampling_rate, x))
        all_trials_df["trial_lfp_timestamp_range"] = all_trials_df["lfp_index"].apply(
            lambda x: (x, x + self.trial_duration * self.lfp_sampling_rate))
        all_trials_df["baseline_ephys_timestamp_range"] = all_trials_df["time_stamp_index"].apply(
            lambda x: (x - self.trial_duration * self.ephys_sampling_rate, x))
        all_trials_df["trial_ephys_timestamp_range"] = all_trials_df["time_stamp_index"].apply(
            lambda x: (x, x + self.trial_duration * self.ephys_sampling_rate))
        all_trials_df["baseline_videoframe_range"] = all_trials_df["video_frame"].apply(
            lambda x: (x - self.trial_duration * self.frame_rate, x))
        all_trials_df["trial_videoframe_range"] = all_trials_df["video_frame"].apply(
            lambda x: (x, x + self.trial_duration * self.frame_rate))
        return all_trials_df

    def extract_lfp(self):
        # Going through all the recording sessions
        recording_name_to_all_ch_lfp = {}
        for session_dir in self.all_sessions_dir:
            # Going through all the recordings in each session
            for recording_path in glob.glob(os.path.join(session_dir, self.recording_extention)):
                # assumes subject name in file name
                try:
                    recording_basename = os.path.splitext(os.path.basename(recording_path))[0]
                    # checking to see if the recording has an ECU component
                    # if it doesn't, then the next one be extracted
                    current_recording = se.read_spikegadgets(recording_path, stream_id=self.ecu_stream_id)
                    current_recording = se.read_spikegadgets(recording_path, stream_id=self.trodes_stream_id)
                    print(recording_basename)
                    # Preprocessing the LFP
                    # higher than 300 is action potential and lower than 0.5 is noise
                    current_recording = sp.bandpass_filter(current_recording, freq_min=self.lfp_freq_min,
                                                           freq_max=self.lfp_freq_max)
                    current_recording = sp.notch_filter(current_recording, freq=self.electric_noise_freq)
                    current_recording = sp.resample(current_recording, resample_rate=self.lfp_sampling_rate)
                    # Z-scoring the LFP
                    current_recording = sp.zscore(
                        current_recording)  # zscore single because avg across animals is in same scale
                    recording_name_to_all_ch_lfp[recording_basename] = current_recording
                except Exception as error:
                    # handle the exception
                    print("An exception occurred:", error)  # An exception occurred: division by zero
        return recording_name_to_all_ch_lfp

    def add_lfp_trace(self):
        self.channel_mapping_df["Subject"] = self.channel_mapping_df["Subject"].astype(str)
        channel_map_and_all_trials_df = all_trials_df.merge(self.channel_mapping_df, left_on="current_subject",
                                                            right_on="Subject", how="left")
        channel_map_and_all_trials_df = channel_map_and_all_trials_df.drop(
            columns=[col for col in channel_map_and_all_trials_df.columns if "eib" in col], errors="ignore")
        channel_map_and_all_trials_df = channel_map_and_all_trials_df.drop(columns=["Subject"], errors="ignore")
        channel_map_and_all_trials_df.to_csv("./proc/trial_metadata.csv")
        channel_map_and_all_trials_df.to_pickle("./proc/trial_metadata.pkl")

        # subsampling and channel mapping would be functions of ephys coillection
        # link lfp to trials
        channel_map_and_all_trials_df["all_ch_lfp"] = channel_map_and_all_trials_df["recording_file"].map(
            recording_name_to_all_ch_lfp)
        # new row for brain region
        brain_region_col = [col for col in self.channel_mapping_df if "spike_interface" in col]
        id_cols = [col for col in channel_map_and_all_trials_df.columns if col not in brain_region_col]
        for col in brain_region_col:
            # object stuff for ecu specific
            channel_map_and_all_trials_df[col] = channel_map_and_all_trials_df[col].astype(int).astype(str)
            channel_map_and_all_trials_df["{}_baseline_lfp_trace".format(
                col.strip("spike_interface").strip("_"))] = channel_map_and_all_trials_df.apply(lambda row: row[
                "all_ch_lfp"].get_traces(channel_ids=[row[col]], start_frame=row["baseline_lfp_timestamp_range"][0],
                                         end_frame=row["baseline_lfp_timestamp_range"][1]).T[0], axis=1)
            channel_map_and_all_trials_df["{}_trial_lfp_trace".format(
                col.strip("spike_interface").strip("_"))] = channel_map_and_all_trials_df.apply(lambda row: row[
                "all_ch_lfp"].get_traces(channel_ids=[row[col]], start_frame=row["trial_lfp_timestamp_range"][0],
                                         end_frame=row["trial_lfp_timestamp_range"][1]).T[0], axis=1)
        channel_map_and_all_trials_df = channel_map_and_all_trials_df.drop(columns=["all_ch_lfp"], errors="ignore")
        return channel_map_and_all_trials_df

