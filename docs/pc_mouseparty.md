
# pc_mouseparty module

::: pc_mouseparty.pc_mouseparty

:::pc_mouseparty.pc_mouseparty.vid_behavior.boris_extraction

function: threshold_bouts(start_stop_array, min_iti, min_bout):
    """
    thresholds behavior bouts
    by combining behavior bouts with interbout intervals of < min_iti
    and then removing remaining bouts of < min_bout

    Args (3 total):
        start_stop_array: numpy array of dim (# of bouts, 2)
        min_iti: float, min interbout interval in seconds
        min_bout: float, min bout length in seconds

    Returns (1):
        start_stop_array: numpy array (ndim=(n bouts, 2))
            of start&stop times (ms)
    """

function get_behavior_bouts(boris_df, subject, behavior, min_iti=0, min_bout=0):
    """
    extracts behavior bout start and stop times from a boris df
    thresholds individually by subject and behavior
    returns start_stop_array ordered by start values

    Args (5 total, 3 required):
        boris_df: pandas dataframe of a boris file (aggregated event table)
        subject: list of strings, desired subject(s) (as written in boris_df)
        behavior: list of strings, desired behavior(s) (as written in boris_df)
        min_iti: float, default=0, bouts w/ itis(s) < min_iti will be combined
        min_bout: float, default=0, bouts < min_bout(s) will be deleted

    Returns (1):
        numpy array (ndim=(n bouts, 2)) of start&stop times (ms)

function save_behavior_bouts(directory, boris_df, subject, behavior, min_bout=0,
                        min_iti=0, filename=None):
    """
    saves a numpy array of start&stop times (ms)
    as filename: subject_behavior_bouts.npy

    Args (7 total, 4 required):
        directory: path to folder where filename.npy will be saved
            path format: './folder/folder/'
        boris_df: pandas dataframe of a boris file (aggregated event table)
        subject: list of strings, desired subjects (as written in boris_df)
        behavior: list of strings, desired behaviors (as written in boris_df)
        min_iti: float, default=0, bouts w/ itis(s) < min_iti will be combined
        min_bout: float, default=0, bouts < min_bouts(s) will be deleted
        filename: string, default=None, must end in .npy

    Returns:
        none
    """