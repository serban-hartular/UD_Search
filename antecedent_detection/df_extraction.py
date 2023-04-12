import math
from collections import defaultdict
from typing import List, Dict

import pandas as pd

import antecedent_detection as ad
import tree_path
from tree_path import ParsedSentence, ParsedDoc, Search
from antecedent_detection import ComplexPredicate



def filtered_dict_to_df(fd : List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(fd)
    if df.empty or 'y' not in df.columns:
        return df
    # sanity check 
    licensers = set(df['licenser_id'])
    for licenser in licensers:
        # count candidates
        good_row = df[(df['y'] == 1) & (df['licenser_id'] == licenser)]
        if good_row.empty:
            print('Error: licenser %s has no correct value' % licenser)
        if len(good_row) != 1:
            print('Error: licenser %s has %d correct values' % (licenser, len(good_row)))
    return df

def balance_data_df(df : pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    licensers = set(df['licenser_id'])
    df['duplicate'] = 0
    for licenser in licensers:
        # count candidates
        candidate_count = len(df[df['licenser_id'] == licenser])
        good_row = df[(df['y']==1) & (df['licenser_id']==licenser)]
        # df = df.append([good_row]*(candidate_count-2), ignore_index=True)
        extra_df = pd.concat([good_row]*(candidate_count-2), ignore_index=True)
        extra_df['duplicate'] = 1
        extra_df.columns = df.columns
        df = pd.concat([df, extra_df], ignore_index=True)
    return df

def extract_X_y(df : pd.DataFrame, X_labels : List[str], y_label : str = 'y') -> (pd.DataFrame, pd.DataFrame):
    y = df[y_label]
    X = df[X_labels]
    return X, y

def split_by_licenser_id(df : pd.DataFrame, split_count : int = 4) -> (pd.DataFrame, pd.DataFrame):
    licensers = set(df['licenser_id'])
    train_licensers = []
    test_licensers = []
    for i, licenser in enumerate(licensers):
        if i % split_count == 0:
            test_licensers.append(licenser)
        else:
            train_licensers.append(licenser)
    return df[df['licenser_id'].isin(train_licensers)], df[df['licenser_id'].isin(test_licensers)]
