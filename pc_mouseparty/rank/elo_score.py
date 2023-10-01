import os
import pandas as pd
import matplotlib.pyplot as plt
import re
from collections import defaultdict
from elorating import calculation

import warnings

# Suppress all warnings
warnings.filterwarnings("ignore")


def __reward_competition(df, cohort, output_dir, plot_flag=True):
    """
    This private function takes in a dataframe and processes the elo score
    for reward competition protocol
    Unedited used the reward_competition jupyter notebook
    Args (4 total, 3 required):
        df (pandas dataframe): dataframe to be processed
        cohort (str): cohort name
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
    cols_to_keep = \
        [col for col in df.columns if all(word not in col
                                          for word in to_remove)]
    df = df[cols_to_keep]
    df["animal_ids"] = df["match"].apply(
        lambda x: tuple(sorted([all_ids.strip()
                                for all_ids in
                                re.findall(r"[-+]?(?:\d*\.\d+|\d+)", x)])))
    df["cohort"] = "TODO"
    cage_to_strain = {}
    df["strain"] = df["cage"].astype(str).map(cage_to_strain)
    all_cages = "_".join([str(cage)
                          for cage in sorted(df["cage"].unique())])
    df["index"] = df.index
    reward_competition_df = df.reset_index(drop=True)

    melted_rc_df = reward_competition_df.melt(
        id_vars=["index", "date", "cage", "box", "match", "animal_ids"],
        var_name="trial",
        value_name="winner")

    melted_rc_df = melted_rc_df.dropna(subset="winner")
    melted_rc_df["keep_row"] = melted_rc_df["winner"].apply(
        lambda x: True if "tie" in str(x).lower() or
                          re.match(r'^-?\d+(?:\.\d+)$', str(x)) else False
    )

    melted_rc_df = melted_rc_df[melted_rc_df["keep_row"]]

    melted_rc_df["winner"] = melted_rc_df["winner"].astype(str).apply(
        lambda x: x.lower().strip()
    )

    melted_rc_df["match_is_tie"] = melted_rc_df["winner"].apply(
        lambda x: True if "tie" in x.lower().strip() else False
    )

    melted_rc_df["winner"] = \
        melted_rc_df.apply(
            lambda x: x["animal_ids"][0] if x["match_is_tie"]
            else x["winner"], axis=1
        )

    melted_rc_df[melted_rc_df["match_is_tie"]]

    melted_rc_df = \
        melted_rc_df[melted_rc_df["trial"].str.contains('trial')]

    melted_rc_df["trial_number"] = melted_rc_df["trial"].apply(
        lambda x:
        int(x.lower().strip("trial").strip("winner").strip("_"))
    )

    melted_rc_df = melted_rc_df.sort_values(
        ["index", "trial_number"]).reset_index(drop=True)

    melted_rc_df["loser"] = melted_rc_df.apply(
        lambda x:
        (list(set(x["animal_ids"]) - set([x["winner"]]))[0]), axis=1
    )

    melted_rc_df["session_number_difference"] = \
        melted_rc_df["date"].astype('category').cat.codes.diff()

    cage_to_elo_rating_dict = defaultdict(dict)

    for cage in melted_rc_df["cage"].unique():
        cage_df = melted_rc_df[melted_rc_df["cage"] == cage]
        cage_to_elo_rating_dict[cage] = \
            calculation.iterate_elo_rating_calculation_for_dataframe(
                dataframe=cage_df,
                winner_id_column="winner",
                loser_id_column="loser",
                additional_columns=melted_rc_df.columns,
                tie_column="match_is_tie"
            )

    cage_to_elo_rating_dict[list(cage_to_elo_rating_dict.keys())[0]][0]

    all_cage_elo_rating_list = []

    for key in cage_to_elo_rating_dict.keys():
        cage_elo_rating_df = \
            pd.DataFrame.from_dict(
                cage_to_elo_rating_dict[key], orient="index")
        cage_elo_rating_df.insert(
            0, 'total_trial_number', range(0, 0 + len(cage_elo_rating_df))
        )

        all_cage_elo_rating_list.append(cage_elo_rating_df)

    all_elo_df = pd.concat(all_cage_elo_rating_list)

    all_elo_df[all_elo_df["match_is_tie"]]

    if cage_to_strain:
        all_elo_df["strain"] = \
            all_elo_df["cage"].astype(str).map(cage_to_strain)

    all_elo_df["experiment_type"] = "Reward Competition"
    all_elo_df["cohort"] = "TODO"
    all_elo_df[all_elo_df["win_draw_loss"] == 0.5]

    id_to_elo_dict = defaultdict(dict)
    sorted_func = enumerate(sorted(all_elo_df["subject_id"].unique()))
    for index, subject_id in sorted_func:
        per_subject_df = all_elo_df[all_elo_df["subject_id"] == subject_id]
        id_to_elo_dict[index]["subject_id"] = subject_id

        id_to_elo_dict[index]["final_elo_rating"] = \
            per_subject_df.iloc[-1]["updated_elo_rating"]
        id_to_elo_dict[index]["cohort"] = per_subject_df.iloc[-1]["cohort"]
        id_to_elo_dict[index]["cage"] = per_subject_df.iloc[-1]["cage"]

    id_to_elo_df = pd.DataFrame.from_dict(
        id_to_elo_dict, orient="index"
    )
    # Adding protocol name
    id_to_elo_df["experiment_type"] = "Reward Competition"
    # Adding rank
    id_to_elo_df["rank"] = \
        id_to_elo_df.groupby("cage")["final_elo_rating"].rank(
            "dense", ascending=False
        )
    # Sorting by cage and then id
    id_to_elo_df = id_to_elo_df.sort_values(
        by=['cage', "subject_id"], ascending=True).reset_index(drop=True)
    id_to_elo_df["rank"] = \
        id_to_elo_df.groupby("cage")["final_elo_rating"].rank(
            "dense", ascending=False
        )
    id_to_elo_df = id_to_elo_df.sort_values(
        by=['cage', "subject_id"], ascending=True).reset_index(drop=True)

    if plot_flag:
        for cage in all_elo_df["cage"].unique():
            fig, ax = plt.subplots()
            plt.rcParams["figure.figsize"] = (18, 10)
            per_cage_df = \
                all_elo_df[all_elo_df["cage"] == cage]

            for index in per_cage_df["index"].unique():
                col = "total_trial_number"
                first_session_in_trial = \
                    per_cage_df[per_cage_df["index"] == index].iloc[0][col]
                plt.vlines(x=[first_session_in_trial - 0.5],
                           ymin=700,
                           ymax=1300,
                           colors='black',
                           linestyle='dashed'
                           )

            # Drawing a line for each subject
            for subject in sorted(per_cage_df["subject_id"].unique()):
                # Getting all the rows with the current subject
                col = "subject_id"
                subject_df = per_cage_df[per_cage_df[col] == subject]
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
                "{} Elo Rating for {} {}".format(
                    "Rewards Competition", cohort, str(cage))
            )
            # To show the legend
            ax.legend(loc="upper left")
            plt.xticks(rotation=90)
            plt.ylim(700, 1300)

            # Checking if out dir exists
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            file_name = "reward_competition_cage" + str(cage) + ".png"
            plt.savefig(os.path.join(output_dir, file_name))

    file_name = "reward_competition_cage" + all_cages + ".csv"
    path = os.path.join(output_dir, file_name)

    id_to_elo_df.to_csv(path, index=False)

    return None

def __process(df, protocol, cohort, sheet, output_dir, plot_flag=True):
        """
        This private function takes in a dataframe and processes the elo score
        for home_cage_observation, urine_marking, or test_tube protocols
        Args (6 total, 5 required):
            df (pandas dataframe): dataframe to be processed
            protocol (str): protocol name
            cohort (str): cohort name
            sheet (str): sheet name
            output_dir (str): path to output directory
            plot_flag (bool): flag to plot data, default True
        Return(None):
            None
        """
        # Initializing column names

        find_col_names = df[df.apply(
            lambda row: 'winner' in row.values, axis=1)]

        if not find_col_names.empty:
            df.columns = find_col_names.iloc[0]
            df = df[df.index != find_col_names.index[0]]

        # check if there is a cage number col
        mode_cage = None
        cage_num = False
        # finding column names for winner, loser, and tie
        winner_col, tie_col, loser_col = None, None, None
        for col in df.columns.tolist():
            if "cage" in col.lower():
                # filling all cage values with mode
                mode_cage = df['cage #'].mode().iloc[0]
                df['cage#'] = mode_cage
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
                mode_cage = int(new_sheet_name)
                df['cage#'] = mode_cage
            except ValueError:
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

        elo_calc = calculation.iterate_elo_rating_calculation_for_dataframe(
            dataframe=df, winner_id_column=winner_col,
            loser_id_column=loser_col,
            tie_column=tie_col
        )
        elo_df = pd.DataFrame.from_dict(elo_calc, orient='index')
        elo_df.groupby("subject_id").count()

        cage_to_strain = {}
        if cage_to_strain:
            elo_df["subject_strain"] = \
                elo_df["cage_num_of_subject"].map(cage_to_strain)
            elo_df["agent_strain"] = \
                elo_df["cage_num_of_agent"].map(cage_to_strain)
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
            col = "session_number_difference"
            elo_df[col] = df[col].repeat(2).reset_index(drop=True)

            for index, row in elo_df[elo_df[col].astype(bool)].iterrows():
                # Offsetting by 0.5 to avoid drawing the line on the dot
                # Drawing the lines above the max and below the minimum
                plt.vlines(x=[row["total_match_number"] - 0.5],
                           ymin=min_elo_rating - 50,
                           ymax=max_elo_rating + 50,
                           colors='black',
                           linestyle='dashed')
            for subject in sorted(elo_df["subject_id"].unique()):
                # Getting all the rows with the current subject
                subject_dataframe = elo_df[elo_df["subject_id"] == subject]
                # Making the current match number the X-Axis
                plt.plot(subject_dataframe["total_match_number"],
                         subject_dataframe["updated_elo_rating"],
                         '-o',
                         label=subject)
                # plt.show()
            ax.set_xlabel("Trial Number")
            ax.set_ylabel("Elo rating")

            tite = "{} Elo Rating for {} {}".format(protocol,
                                                    cohort,
                                                    "Cage #" + str(mode_cage))
            ax.set_title(tite)
            ax.legend(loc="upper left")
            plt.ylim(min_elo_rating - 50, max_elo_rating + 50)
            file_name = protocol + "_cage" + str(mode_cage) + ".png"
            fig.savefig(os.path.join(output_dir, file_name))

        # Saving df csv to output dir
        file_name = protocol + "_cage" + str(mode_cage) + ".csv"
        elo_df.to_csv(os.path.join(output_dir, file_name), index=False)

def generate_elo_scores(file_info, output_dir, plot_flag=True):
    """
        This function takes in a dataframe and processes elo score for
        home_cage_observation, urine_marking, or test_tube protocols
        Args (3 total, 3 required):
            file_info (dict):
                dictionary with file names as key and value as a dictionary of
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

    for file_name, file_data in file_info.items():
        file_path = file_data["file_path"]
        protocol = file_data["protocol"]
        sheets = file_data["sheet"]
        cohort = file_data["cohort"]
        xls = pd.ExcelFile(file_path)
        for sheet in sheets:
            data = pd.read_excel(xls, sheet_name=sheet)
            if protocol == "reward_competition":
                __reward_competition(df=data,
                                     cohort=cohort,
                                     output_dir=output_dir,
                                     plot_flag=plot_flag)
            else:
                __process(df=data,
                          protocol=protocol,
                          cohort=cohort,
                          sheet=sheet,
                          output_dir=output_dir,
                          plot_flag=plot_flag)
