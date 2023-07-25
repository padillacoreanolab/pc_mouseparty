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


def calculate_elo_rating(
    subject_elo_rating,
    agent_elo_rating,
    k_factor=20,
    score=1,
    number_of_decimals=1
):
    """
    Calculates the Elo rating of a given subject given it's original score,
    it's opponent, the K-Factor, and whether or not it has won or not.
    The calculation is based on: https://www.omnicalculator.com/sports/elo

    Args:
        subject_elo_rating(float): The original Elo rating for the subject
        agent_elo_rating(float): The original Elo rating for the agent
        k_factor(int): k-factor, or development coefficient.
            - It usually takes values between 10 and 40,
            depending on player's strength
        score(int): the actual outcome of the game.
            - In chess, a win counts as 1 point, a draw is equal to 0.5,
            and a lose gives 0.
        number_of_decimals(int): Number of decimals to round to

    Returns:
        int: Updated Elo rating of the subject
    """
    # Calculating the Elo rating
    rating_difference = agent_elo_rating - subject_elo_rating
    expected_score = 1 / (1 + 10 ** (rating_difference / 400))
    new_elo_rating = subject_elo_rating + k_factor * (score - expected_score)
    # Rounding to `number_of_decimals`
    return round(new_elo_rating, number_of_decimals)


def update_elo_rating(
    winner_id,
    loser_id,
    id_to_elo_rating=None,
    default_elo_rating=1000,
    winner_score=1,
    loser_score=0,
    **calculate_elo_rating_params
):
    """
    Updates the Elo rating in a dictionary that contains the ID of the subject
    as keys, and the Elo rating as the values.
    You can also adjust how the Elo rating is calculated with
    'calculate_elo_rating_params'.

    Args:
        - winner_id(str): ID of the winner
        - loser_id(str): ID of the loser
        - id_to_elo_rating(dict): Dict that has the ID of the subjects
        as keys to the Elo Score as values.
        - default_elo_rating(int): The default Elo rating to be used if
        there is no elo score for the specified ID.
        - **calculate_elo_rating_params(kwargs): Other params for the
        calculate_elo_rating to change how the Elo rating is calculated

    Returns:
        - Dict: Dictionary that has the ID of the subjects as keys
        to the Elo Score as values.
    """
    if id_to_elo_rating is None:
        id_to_elo_rating = defaultdict(lambda: default_elo_rating)

    # Getting the current Elo Score
    current_winner_rating = id_to_elo_rating[winner_id]
    current_loser_rating = id_to_elo_rating[loser_id]

    # Calculating Elo rating
    id_to_elo_rating[winner_id] = calculate_elo_rating(
        subject_elo_rating=current_winner_rating,
        agent_elo_rating=current_loser_rating,
        score=winner_score,
        **calculate_elo_rating_params
        )
    id_to_elo_rating[loser_id] = calculate_elo_rating(
        subject_elo_rating=current_loser_rating,
        agent_elo_rating=current_winner_rating,
        score=loser_score,
        **calculate_elo_rating_params
        )

    return id_to_elo_rating


def get_ranking_from_elo_rating_dictionary(input_dict, subject_id):
    """
    Orders a dictionary of subject ID keys to ELO score values by ELO score.
    And then gets the rank of the subject with the inputted ID.
    Lower ranks like 1 would represent those subjects with higher
    ELO scores and vice versa.

    Args:
        input_dict(dict):
            Dictionary of subject ID keys to ELO score values
        subject_id(str, int, or any value that's a key in input dict):
            The ID of the subject that you want the ranking of

    Returns:
        int:
            Ranking of the subject with the ID inputted
    """
    # Sorting the subject ID's by ELO score
    sorted_subject_to_elo_rating = sorted(
        input_dict.items(),
        key=operator.itemgetter(1),
        reverse=True
        )
    # Getting the rank of the subject based on ELO score
    return [
        subject_tuple[0] for subject_tuple in sorted_subject_to_elo_rating
        ].index(subject_id) + 1


def iterate_elo_rating_calculation_for_dataframe(
    dataframe,
    winner_id_column,
    loser_id_column,
    tie_column=None,
    additional_columns=None
):
    """
    Iterates through a dataframe that has the ID of winners and losers
    for a given event.
    A dictionary will be created that contains the information of the event,
    which can then be turned into a dataframe.
    Each key is either from winner or loser's perspective.

    Args:
        - dataframe(Pandas DataFrame):
        - winner_id_column(str): The name of the column that has
        the winner's ID
        - loser_id_column(str): The name of the column that has the loser's ID
        - additional_columns(list): Additional columns to take from
        the dataframe.

    Returns:
        - Dict: With a key value pair for each event either from the
        winner or loser's perspective.
        This can be turned into a dataframe with each
        key value pair being a row.
    """
    if additional_columns is None:
        additional_columns = []

    # Dictionary that keeps track of the current Elo rating of the subject
    id_to_elo_rating = defaultdict(lambda: 1000)
    # Dictionary that will be converted to a DataFrame
    index_to_elo_rating_and_meta_data = defaultdict(dict)

    # Indexes that will identify which row the dictionary key
    # value pair will be
    # The number of the index has no significance other than being
    # the number of the row
    all_indexes = iter(range(0, 99999))

    # Keeping track of the number of matches
    total_match_number = 1

    # Making a copy in case there is an error with
    # changing the type of the tie column
    copied_dataframe = dataframe.copy()
    # Changing the tie column type to bool
    # So that we can filter out for booleans including False and 0
    try:
        copied_dataframe[tie_column] = copied_dataframe[
            tie_column
            ].astype(bool)
    except Exception:
        copied_dataframe = dataframe.copy()

    for i, row in copied_dataframe.dropna(subset=winner_id_column).iterrows():
        # Getting the ID of the winner subject
        winner_id = row[winner_id_column]
        # Getting the ID of the loser subject
        loser_id = row[loser_id_column]

        # Getting the current Elo Score
        current_winner_rating = id_to_elo_rating[winner_id]
        current_loser_rating = id_to_elo_rating[loser_id]

        if tie_column:
            # When there is nothing in the tie column
            # Or when there is a false value indicating that it is not a tie
            if pd.isna(copied_dataframe[tie_column][i]) or not (copied_dataframe[tie_column][i]).any():

                winner_score = 1
                loser_score = 0
            # When there is value in the tie column
            else:
                winner_score = 0.5
                loser_score = 0.5
        # When there is no tie column
        else:
            winner_score = 1
            loser_score = 0

        # Updating the dictionary with ID keys and Elo Score values
        update_elo_rating(
            winner_id=winner_id,
            loser_id=loser_id,
            id_to_elo_rating=id_to_elo_rating,
            winner_score=winner_score,
            loser_score=loser_score
            )

        # Saving all the data for the winner
        winner_index = next(all_indexes)
        index_to_elo_rating_and_meta_data[winner_index]["total_match_number"] = total_match_number
        index_to_elo_rating_and_meta_data[winner_index]["subject_id"] = winner_id
        index_to_elo_rating_and_meta_data[winner_index]["agent_id"] = loser_id
        index_to_elo_rating_and_meta_data[winner_index]["original_elo_rating"] = current_winner_rating
        index_to_elo_rating_and_meta_data[winner_index]["updated_elo_rating"] = id_to_elo_rating[winner_id]
        index_to_elo_rating_and_meta_data[winner_index]["win_draw_loss"] = winner_score
        index_to_elo_rating_and_meta_data[winner_index]["subject_ranking"] = get_ranking_from_elo_rating_dictionary(id_to_elo_rating, winner_id)
        index_to_elo_rating_and_meta_data[winner_index]["agent_ranking"] = get_ranking_from_elo_rating_dictionary(id_to_elo_rating, loser_id)
        index_to_elo_rating_and_meta_data[winner_index]["pairing_index"] = 0
        for column in additional_columns:
            index_to_elo_rating_and_meta_data[winner_index][column] = row[column]  

        # Saving all the data for the loser
        loser_index = next(all_indexes)
        index_to_elo_rating_and_meta_data[loser_index]["total_match_number"] = total_match_number
        index_to_elo_rating_and_meta_data[loser_index]["subject_id"] = loser_id
        index_to_elo_rating_and_meta_data[loser_index]["agent_id"] = winner_id
        index_to_elo_rating_and_meta_data[loser_index]["original_elo_rating"] = current_loser_rating
        index_to_elo_rating_and_meta_data[loser_index]["updated_elo_rating"] = id_to_elo_rating[loser_id]
        index_to_elo_rating_and_meta_data[loser_index]["win_draw_loss"] = loser_score
        index_to_elo_rating_and_meta_data[loser_index]["subject_ranking"] = get_ranking_from_elo_rating_dictionary(id_to_elo_rating, loser_id)
        index_to_elo_rating_and_meta_data[loser_index]["agent_ranking"] = get_ranking_from_elo_rating_dictionary(id_to_elo_rating, winner_id)
        index_to_elo_rating_and_meta_data[loser_index]["pairing_index"] = 1
        for column in additional_columns:
            index_to_elo_rating_and_meta_data[loser_index][column] = row[column]  

        # Updating the match number
        total_match_number += 1

    return index_to_elo_rating_and_meta_data


def calculate_elo_score(
    subject_elo_score,
    agent_elo_score,
    k_factor=20,
    score=1,
    number_of_decimals=1
):
    """
    Calculates the Elo score of a given subject
    given it's original score, it's opponent,
    the K-Factor, and whether or not it has won or not.
    The calculation is based on: https://www.omnicalculator.com/sports/elo

    Args:
        subject_elo_score(float): The original Elo score for the subject
        agent_elo_score(float): The original Elo score for the agent
        k_factor(int): k-factor, or development coefficient.
            - It usually takes values between 10 and 40,
            depending on player's strength
        score(int): the actual outcome of the game.
            - In chess, a win counts as 1 point, a draw is equal to 0.5,
            and a lose gives 0.
        number_of_decimals(int): Number of decimals to round to

    Returns:
        int: Updated Elo score of the subject
    """
    # Calculating the Elo score
    rating_difference = agent_elo_score - subject_elo_score
    expected_score = 1 / (1 + 10 ** (rating_difference / 400))
    new_elo_score = subject_elo_score + k_factor * (score - expected_score)
    # Rounding to `number_of_decimals`
    return round(new_elo_score, number_of_decimals)


def update_elo_score(
    winner_id,
    loser_id,
    id_to_elo_score=None,
    default_elo_score=1000,
    winner_score=1,
    loser_score=0,
    **calculate_elo_score_params
):
    """
    Updates the Elo score in a dictionary that contains the
    ID of the subject as keys,
    and the Elo score as the values.
    You can also adjust how the Elo score is calculated with
    'calculate_elo_score_params'.

    Args:
        winner_id(str): ID of the winner
        loser_id(str): ID of the loser
        id_to_elo_score(dict): Dict that has the ID of the subjects as
        keys to the Elo Score as values
        default_elo_score(int): The default Elo score to be used if
        there is not elo score for the specified ID
        **calculate_elo_score_params(kwargs): Other params for the
        calculate_elo_score to change how the Elo score is calculated

    Returns:
        Dict: Dict that has the ID of the subjects as
        keys to the Elo Score as values
    """
    if id_to_elo_score is None:
        id_to_elo_score = defaultdict(lambda: default_elo_score)

    # Getting the current Elo Score
    current_winner_rating = id_to_elo_score[winner_id]
    current_loser_rating = id_to_elo_score[loser_id]

    # Calculating Elo score
    id_to_elo_score[winner_id] = calculate_elo_score(
        subject_elo_score=current_winner_rating,
        agent_elo_score=current_loser_rating,
        score=winner_score,
        **calculate_elo_score_params
        )
    id_to_elo_score[loser_id] = calculate_elo_score(
        subject_elo_score=current_loser_rating,
        agent_elo_score=current_winner_rating,
        score=loser_score,
        **calculate_elo_score_params
        )

    return id_to_elo_score


def get_ranking_from_elo_score_dictionary(input_dict, subject_id):
    """
    Orders a dictionary of subject ID keys to ELO score values by ELO score.
    And then gets the rank of the subject with the inputted ID.
    Lower ranks like 1 would represent those subjects with higher
    ELO scores and vice versa.

    Args:
        input_dict(dict):
            Dictionary of subject ID keys to ELO score values
        subject_id(str, int, or any value that's a key in input dict):
            The ID of the subject that you want the ranking of

    Returns:
        int:
            Ranking of the subject with the ID inputted
    """
    # Sorting the subject ID's by ELO score
    sorted_subject_to_elo_score = sorted(
        input_dict.items(),
        key=operator.itemgetter(1),
        reverse=True
        )
    # Getting the rank of the subject based on ELO score
    return [
        subject_tuple[0] for subject_tuple in sorted_subject_to_elo_score
        ].index(subject_id) + 1


def iterate_elo_score_calculation_for_dataframe(
    dataframe,
    winner_column,
    loser_column,
    tie_column=None,
    additional_columns=None
):
    """
    Iterates through a dataframe that has the ID of
    winners and losers for a given event.
    A dictionary will be created that
    contains the information of the event,
    which can then be turned into a dataframe.
    Each key is either from winner or loser's perspective.

    Args:
        dataframe(Pandas DataFrame):
        winner_column(str): The name of the column that has the winner's ID
        loser_column(str): The name of the column that has the loser's ID
        additional_columns(list): Additional columns to take from the

    Returns:
        Dict: With a key value pair for each event either
        from the winner or loser's perspective.
        This can be turned into a dataframe with
        each key value pair being a row.
    """
    if additional_columns is None:
        additional_columns = []

    # Dictionary that keeps track of the current Elo score of the subject
    id_to_elo_score = defaultdict(lambda: 1000)
    # Dictionary that will be converted to a DataFrame
    index_to_elo_score_and_meta_data = defaultdict(dict)

    # Indexes that will identify which row the dictionary
    # key value pair will be
    # The number of the index has no significance other than
    # being the number of the row
    all_indexes = iter(range(0, 99999))

    # Keeping track of the number of matches
    total_match_number = 1

    for index, row in dataframe.dropna(subset=winner_column).iterrows():
        # Getting the ID of the winner subject
        winner_id = row[winner_column]
        # Getting the ID of the loser subject
        loser_id = row[loser_column]

        # Getting the current Elo Score
        current_winner_rating = id_to_elo_score[winner_id]
        current_loser_rating = id_to_elo_score[loser_id]

        if tie_column:
            # When there is nothing in the tie column
            if pd.isna(dataframe[tie_column][index]):
                winner_score = 1
                loser_score = 0
            # When there is value in the tie column
            else:
                winner_score = 0.5
                loser_score = 0.5
        # When there is no tie column
        else:
            winner_score = 1
            loser_score = 0

        # Updating the dictionary with ID keys and Elo Score values
        update_elo_score(
            winner_id=winner_id,
            loser_id=loser_id,
            id_to_elo_score=id_to_elo_score,
            winner_score=winner_score,
            loser_score=loser_score
            )

        # Saving all the data for the winner
        winner_index = next(all_indexes)
        index_to_elo_score_and_meta_data[winner_index]["total_match_number"] = total_match_number
        index_to_elo_score_and_meta_data[winner_index]["subject_id"] = winner_id
        index_to_elo_score_and_meta_data[winner_index]["agent_id"] = loser_id
        index_to_elo_score_and_meta_data[winner_index]["original_elo_score"] = current_winner_rating
        index_to_elo_score_and_meta_data[winner_index]["updated_elo_score"] = id_to_elo_score[winner_id]
        index_to_elo_score_and_meta_data[winner_index]["win_draw_loss"] = winner_score
        index_to_elo_score_and_meta_data[winner_index]["subject_ranking"] = get_ranking_from_elo_score_dictionary(id_to_elo_score, winner_id)
        index_to_elo_score_and_meta_data[winner_index]["agent_ranking"] = get_ranking_from_elo_score_dictionary(id_to_elo_score, loser_id)

        for column in additional_columns:
            index_to_elo_score_and_meta_data[winner_index][column] = row[column]  

        # Saving all the data for the loser
        loser_index = next(all_indexes)
        index_to_elo_score_and_meta_data[loser_index]["total_match_number"] = total_match_number
        index_to_elo_score_and_meta_data[loser_index]["subject_id"] = loser_id
        index_to_elo_score_and_meta_data[loser_index]["agent_id"] = winner_id
        index_to_elo_score_and_meta_data[loser_index]["original_elo_score"] = current_loser_rating
        index_to_elo_score_and_meta_data[loser_index]["updated_elo_score"] = id_to_elo_score[loser_id]
        index_to_elo_score_and_meta_data[loser_index]["win_draw_loss"] = loser_score
        index_to_elo_score_and_meta_data[loser_index]["subject_ranking"] = get_ranking_from_elo_score_dictionary(id_to_elo_score, loser_id)
        index_to_elo_score_and_meta_data[loser_index]["agent_ranking"] = get_ranking_from_elo_score_dictionary(id_to_elo_score, winner_id)
        for column in additional_columns:
            index_to_elo_score_and_meta_data[loser_index][column] = row[column]

        # Updating the match number
        total_match_number += 1

    return index_to_elo_score_and_meta_data


