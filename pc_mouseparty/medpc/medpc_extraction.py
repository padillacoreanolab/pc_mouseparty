import re
import pandas as pd


def medpc_txt2df(text_file_path):
    """
    This function reads a medpc text data file into a pandas dataframe.

    Args (1 total, 1 required):
        text_file_path : str, a path to a medpc text file as a string.

    Return (1):
        df : pandas dataframe, a dataframe with the medpc data.
    """
    # Open the medpc text file
    # with open(text_file_path, "r") as file: # use this for package
    with open(text_file_path.name) as file:  # use this for gradio app
        medpc_txt_file = file.read()

    # split the file with each new line an element in a list
    medpc_txt_file_lst = medpc_txt_file.split('\n')

    # remove all empty elements in the list
    medpc_txt_file_lst = list(filter(None, medpc_txt_file_lst))

    # add medpc output vectors to lists
    result = []
    temp = []
    for item in medpc_txt_file_lst:
        # add values taht comeafter ":" to a list as floats
        if re.search(r'^\s*\d+:\s+', item):
            temp.append(item)
        else:
            if temp:
                floats = [float(x) for x in re.findall(r'\d+\.\d+',
                                                       ''.join(temp))]
                result.append(floats)
                temp = []
            result.append(item)
    if temp:
        floats = [float(x) for x in re.findall(r'\d+\.\d+',
                                               ''.join(temp))]
        result.append(floats)

    # convert the list of lists and strings to
    # a dictionary with everything before ":"
    # as a key and everything after as the value
    result_dict = {}
    for item in result:
        if ':' in item:
            index = item.index(':')
            key = item[:index]
            value = item[index+1:].strip()
            if not value:
                value = result[result.index(item)+1]
            result_dict[key] = value
        elif type(item) == str:
            result_dict[item] = []

    # convert the dictionary to a dataframe
    # values are of unequal length
    # convert all values to lists
    pd_series_lst = []
    for i, j in result_dict.items():
        if type(j) != list:
            result_dict[i] = [j]
        else:
            result_dict[i] = j
        pd_series_lst.append(pd.Series(j))

    # add list to dataframe
    df = pd.concat(pd_series_lst, axis=1)
    df.columns = result_dict.keys()

    return (df)


def cut_zeros(df):
    """
    This function removes all trailing zeros of the medpc dataframe.

    Args (2 total, 1 required):
        df: pandas dataframe, a dataframe with the medpc data.

    Return (1):
        df : pandas dataframe, a dataframe with the medpc data
        with trailing zeros removed.
    """
    # find index of last row that does not only ahve 0 and Nan
    last_idx = df[df.sum(axis=1).ne(0)].index[-1]
    df = df[:last_idx+1]

    return (df)