import os
import pandas as pd
import matplotlib.pyplot as plt
import re
from collections import defaultdict
from elorating import calculation

# Suppress all warnings
import warnings

warnings.filterwarnings("ignore")


def _reward_competition(df, output_dir, plot_flag=True):
    """
    This private function takes in a dataframe and processes the elo score for reward
    competition protocol
    Unedited used the reward_competition jupyter notebook
    Args (3 total, 2 required):
        df (pandas dataframe): dataframe to be processed
        output_dir (str): path to output directory
        plot_flag (bool): flag to plot data, default True

    Return(None):
        None
    """

    for col in df.columns.tolist():
        formatted_col_name = "_".join(str(col).lower().strip().split(" "))
        df.rename(columns={col: formatted_col_name}, inplace=True)

    # removing columns from given list of strings
    to_remove = ["wins", "ties", "time"]
    cols_to_keep = [col for col in df.columns if all(word not in col for word
                                                     in to_remove)]
    df = df[cols_to_keep]
    df["animal_ids"] = df["match"].apply(
        lambda x: tuple(sorted([all_ids.strip() for all_ids in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", x)])))
    df["cohort"] = "TODO"
    cage_to_strain = {}
    df["strain"] = df["cage"].astype(str).map(cage_to_strain)
    all_cages = "_".join([str(cage) for cage in sorted(df["cage"].unique())])
    df["index"] = df.index
    reward_competition_df = df.reset_index(drop=True)

    melted_reward_competition_df = reward_competition_df.melt(
        id_vars=["index", "date", "cage", "box", "match", "animal_ids"],
        var_name="trial",
        value_name="winner")

    melted_reward_competition_df = melted_reward_competition_df.dropna(
        subset="winner")
    melted_reward_competition_df["keep_row"] = \
        melted_reward_competition_df["winner"].apply(
            lambda x: True if "tie" in str(x).lower() or
                              re.match(r'^-?\d+(?:\.\d+)$', str(x)) else False
        )

    melted_reward_competition_df = \
        melted_reward_competition_df[melted_reward_competition_df["keep_row"]]

    melted_reward_competition_df["winner"] = \
        melted_reward_competition_df["winner"].astype(str).apply(
            lambda x: x.lower().strip()
        )

    melted_reward_competition_df["match_is_tie"] = \
        melted_reward_competition_df["winner"].apply(
            lambda x: True if "tie" in x.lower().strip() else False
        )

    melted_reward_competition_df["winner"] = \
        melted_reward_competition_df.apply(
            lambda x: x["animal_ids"][0] if x["match_is_tie"] else x["winner"],
            axis=1
        )

    melted_reward_competition_df[melted_reward_competition_df["match_is_tie"]]

    melted_reward_competition_df = melted_reward_competition_df[
        melted_reward_competition_df["trial"].str.contains('trial')]

    melted_reward_competition_df["trial_number"] = \
        melted_reward_competition_df["trial"].apply(
            lambda x: int(x.lower().strip("trial").strip("winner").strip("_"))
        )

    melted_reward_competition_df = \
        melted_reward_competition_df.sort_values(
            ["index", "trial_number"]).reset_index(drop=True)

    melted_reward_competition_df["loser"] = melted_reward_competition_df.apply(
        lambda x: (list(set(x["animal_ids"]) - set([x["winner"]]))[0]), axis=1)

    melted_reward_competition_df["session_number_difference"] = \
        melted_reward_competition_df["date"].astype(
            'category').cat.codes.diff()

    cage_to_elo_rating_dict = defaultdict(dict)

    for cage in melted_reward_competition_df["cage"].unique():
        cage_df = \
            melted_reward_competition_df[melted_reward_competition_df["cage"] == cage]
        cage_to_elo_rating_dict[cage] = \
            calculation.iterate_elo_rating_calculation_for_dataframe(
                dataframe=cage_df,
                winner_id_column="winner",
                loser_id_column="loser",
                additional_columns=melted_reward_competition_df.columns,
                tie_column="match_is_tie"
            )

    cage_to_elo_rating_dict[list(cage_to_elo_rating_dict.keys())[0]][0]

    all_cage_elo_rating_list = []

    for key in cage_to_elo_rating_dict.keys():
        cage_elo_rating_df = pd.DataFrame.from_dict(cage_to_elo_rating_dict[key], orient="index")
        cage_elo_rating_df.insert(
            0, 'total_trial_number', range(0, 0 + len(cage_elo_rating_df))
        )

        all_cage_elo_rating_list.append(cage_elo_rating_df)

    all_cage_elo_rating_df = pd.concat(all_cage_elo_rating_list)

    all_cage_elo_rating_df[all_cage_elo_rating_df["match_is_tie"]]

    if cage_to_strain:
        all_cage_elo_rating_df["strain"] = \
            all_cage_elo_rating_df["cage"].astype(str).map(cage_to_strain)

    all_cage_elo_rating_df["experiment_type"] = "Reward Competition"
    all_cage_elo_rating_df["cohort"] = "TODO"
    all_cage_elo_rating_df[all_cage_elo_rating_df["win_draw_loss"] == 0.5]

    id_to_final_elo_rating_dict = defaultdict(dict)
    sorted_func = enumerate(sorted(all_cage_elo_rating_df["subject_id"].unique()))
    for index, subject_id in sorted_func:
        per_subject_df = \
            all_cage_elo_rating_df[
                all_cage_elo_rating_df["subject_id"] == subject_id
                ]
        id_to_final_elo_rating_dict[index]["subject_id"] = subject_id

        id_to_final_elo_rating_dict[index]["final_elo_rating"] = \
            per_subject_df.iloc[-1]["updated_elo_rating"]
        id_to_final_elo_rating_dict[index]["cohort"] = \
            per_subject_df.iloc[-1]["cohort"]
        id_to_final_elo_rating_dict[index]["cage"] = \
            per_subject_df.iloc[-1]["cage"]

    id_to_final_elo_rating_df = pd.DataFrame.from_dict(
        id_to_final_elo_rating_dict, orient="index"
    )
    # Adding protocol name
    id_to_final_elo_rating_df["experiment_type"] = "Reward Competition"
    # Adding rank
    id_to_final_elo_rating_df["rank"] = \
        id_to_final_elo_rating_df.groupby("cage")["final_elo_rating"].rank(
            "dense", ascending=False
        )
    # Sorting by cage and then id
    id_to_final_elo_rating_df = id_to_final_elo_rating_df.sort_values(
        by=['cage', "subject_id"], ascending=True).reset_index(drop=True)
    id_to_final_elo_rating_df["rank"] = \
        id_to_final_elo_rating_df.groupby("cage")["final_elo_rating"].rank(
            "dense", ascending=False
        )
    id_to_final_elo_rating_df = \
        id_to_final_elo_rating_df.sort_values(
            by=['cage', "subject_id"], ascending=True).reset_index(drop=True)

    if plot_flag:
        for cage in all_cage_elo_rating_df["cage"].unique():
            fig, ax = plt.subplots()
            plt.rcParams["figure.figsize"] = (18, 10)
            per_cage_df = \
                all_cage_elo_rating_df[all_cage_elo_rating_df["cage"] == cage]

            for index in per_cage_df["index"].unique():
                first_session_in_trial = \
                    per_cage_df[per_cage_df["index"] == index].iloc[0]["total_trial_number"]
                plt.vlines(x=[first_session_in_trial - 0.5],
                           ymin=700,
                           ymax=1300,
                           colors='black',
                           linestyle='dashed'
                           )

            # Drawing a line for each subject
            for subject in sorted(per_cage_df["subject_id"].unique()):
                # Getting all the rows with the current subject
                subject_df = per_cage_df[per_cage_df["subject_id"] == subject]
                # Making the dates into days after the first session by
                # subtracting all the dates by the first date
                plt.plot(subject_df["total_trial_number"],
                         subject_df["updated_elo_rating"],
                         '-o',
                         label=subject
                         )

            # Labeling the X/Y Axis and the title
            ax.set_xlabel("Trial Number")
            ax.set_ylabel("Elo Score")
            ax.set_title(
                "{} Elo Rating for {} {}".format("Rewards Competition", "TODO", str(cage)))
            # To show the legend
            ax.legend(loc="upper left")
            plt.xticks(rotation=90)
            plt.ylim(700, 1300)

            # Checking if out dir exists
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            plt.savefig(
                os.path.join(output_dir,
                             "reward_competition_cage" + str(cage) + ".png"))

    path = os.path.join(
        output_dir, "reward_competition_cage" + all_cages + ".csv")

    id_to_final_elo_rating_df.to_csv(path, index=False)

    return None

def general_processing(file_info, output_dir, plot_flag=True):
    """
        This function takes in a dataframe and processes elo score for home_cage_observation, urine_marking,
        or test_tube protocols
        Args (3 total, 3 required):
            file_info (dict): dictionary with file names as key and value as a dictionary of
            file information with the following properties:
                file_path (str): path to file
                protocol (str): protocol name
                sheet (list): list of sheet names
                cohort (str): cohort name
            output_dir (str): path to output directory
            plot_flag (bool): flag to plot data, default True

        Return(None):
            None
    """
    def process(df, protocol, cohort, output_dir, plot_flag):
        # Initializing column names

        find_col_names = df[df.apply(lambda row: 'winner' in row.values, axis=1)]

        if not find_col_names.empty:
            df.columns = find_col_names.iloc[0]
            df = df[df.index != find_col_names.index[0]]

        # check if there is a cage number col
        mode_cage_val = None
        cage_num = False
        # finding column names for winner, loser, and tie
        winner_col, tie_col, loser_col = None, None, None
        for col in df.columns.tolist():
            if "cage" in col.lower():
                # filling all cage values with mode
                mode_cage_val = df['cage #'].mode().iloc[0]
                df['cage#'] = mode_cage_val
                cage_num = True
            if "winner" in col.lower():
                winner_col = col
            if "loser" in col.lower():
                loser_col = col
            if "tie" in col.lower():
                tie_col = col

        if not winner_col or not loser_col:
            print("Winner or Loser column not found")
            return None

        if not cage_num:
            try:
                new_sheet_name = sheet.lower().replace("cage", "")
                mode_cage_val = int(new_sheet_name)
                df['cage#'] = mode_cage_val
            except:
                print("Cage# cannot be determined")
                return None

        # drop cols if winner & loss is NaN
        df = df.dropna(subset=['winner', 'loser'], how='all')

        # Autofill dates
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['date'].fillna(method='ffill', inplace=True)

        # Identify sessions based on date values
        df['session_number_difference'] = 0
        previous_date = None
        for index, row in df.iterrows():
            current_date = row['date']
            # check for session change
            if not previous_date:
                df.at[index, 'session_number_difference'] = 1
            elif previous_date is not None and current_date != previous_date:
                df.at[index, 'session_number_difference'] = 1
            previous_date = current_date
        # Elo Score from calculation.py
        if tie_col:
            df[tie_col] = df[tie_col].notna()

        elo_calc = calculation.iterate_elo_rating_calculation_for_dataframe(dataframe=df, winner_id_column=winner_col,
                                                                            loser_id_column=loser_col,
                                                                            tie_column=tie_col)
        elo_df = pd.DataFrame.from_dict(elo_calc, orient='index')
        elo_df.groupby("subject_id").count()

        cage_to_strain = {}
        if cage_to_strain:
            elo_df["subject_strain"] = elo_df["cage_num_of_subject"].map(cage_to_strain)
            elo_df["agent_strain"] = elo_df["cage_num_of_agent"].map(cage_to_strain)
        elo_df["experiment_type"] = protocol
        elo_df["cohort"] = cohort

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if plot_flag:
            max_elo_rating = elo_df["updated_elo_rating"].max()
            min_elo_rating = elo_df["updated_elo_rating"].min()

            plt.rcParams["figure.figsize"] = (13.5, 7.5)
            fig, ax = plt.subplots()

            # adjusting session number difference
            elo_df['session_number_difference'] = \
                df['session_number_difference'].repeat(2).reset_index(drop=True)

            for index, row in elo_df[elo_df['session_number_difference'].astype(bool)].iterrows():
                # Offsetting by 0.5 to avoid drawing the line on the dot
                # Drawing the lines a little above the max and a little below the minimum
                plt.vlines(x=[row["total_match_number"] - 0.5], ymin=min_elo_rating - 50, ymax=max_elo_rating + 50,
                           colors='black', linestyle='dashed')
            for subject in sorted(elo_df["subject_id"].unique()):
                # Getting all the rows with the current subject
                subject_dataframe = elo_df[elo_df["subject_id"] == subject]
                # Making the current match number the X-Axis
                plt.plot(subject_dataframe["total_match_number"], subject_dataframe["updated_elo_rating"], '-o',
                         label=subject)
                # plt.show()
            ax.set_xlabel("Trial Number")
            ax.set_ylabel("Elo rating")

            ax.set_title(
                "{} Elo Rating for {} {}".format(protocol, cohort, "Cage #" + str(mode_cage_val)))
            ax.legend(loc="upper left")
            plt.ylim(min_elo_rating - 50, max_elo_rating + 50)
            fig.savefig(os.path.join(output_dir, protocol + "_cage" + str(mode_cage_val) + ".png"))

        # Saving df csv to output dir
        elo_df.to_csv(os.path.join(output_dir, protocol + "_cage" + str(mode_cage_val) + ".csv"), index=False)

    for file_name, file_data in file_info.items():
        file_path = file_data["file_path"]
        protocol = file_data["protocol"]
        sheets = file_data["sheet"]
        cohort = file_data["cohort"]
        xls = pd.ExcelFile(file_path)
        for sheet in sheets:
            data = pd.read_excel(xls, sheet_name=sheet)
            if protocol == "reward_competition":
                _reward_competition(df=data, output_dir=output_dir, plot_flag=plot_flag)
            else:
                process(df=data, protocol=protocol, cohort=cohort, output_dir=output_dir, plot_flag=plot_flag)
