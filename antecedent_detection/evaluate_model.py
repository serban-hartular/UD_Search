from collections import defaultdict
from typing import List, Dict

import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import AdaBoostClassifier, BaggingClassifier, ExtraTreesClassifier, GradientBoostingClassifier, \
    RandomForestClassifier
from sklearn.naive_bayes import ComplementNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.semi_supervised import LabelPropagation, LabelSpreading
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegressionCV, LinearRegression

from antecedent_detection.df_extraction import extract_X_y, split_by_licenser_id

columns = ['candidate_licenser_rel', 'candidate_precedent_rel', 'cataphoric', 'same_lemma', 'same_modality', 'same_mod_class', 'epist_e', 'aprecia_e', 'aspect_e', 'deont_e', 'dicendi_e', 'epist_a', 'aprecia_a', 'aspect_a', 'deont_a', 'dicendi_a', 'subjunctive', ]
group_dist = ['group_dist']
tok_dist = ['tok_dist', 'syn_dist']
tok_dist_ln = ['ln2_tok_dist', 'ln2_syn_dist']

_args = defaultdict(dict, {MLPClassifier: {'max_iter':500}, LabelPropagation: {'max_iter':2000}, LogisticRegressionCV:{'max_iter':250}})


def create_model(data_df : pd.DataFrame, X_labels : List[str], model_class = LogisticRegressionCV) -> (LogisticRegressionCV, float, float):
    df_train, df_test = split_by_licenser_id(data_df)
    X_train, y_train = extract_X_y(df_train, X_labels)
    X_test, y_test = extract_X_y(df_test, X_labels)
    model = model_class(**_args[model_class]).fit(X_train, y_train)
    return model, model.score(X_train, y_train), model.score(X_test, y_test)

def evaluate_model(model : LogisticRegressionCV, data_df : pd.DataFrame, X_labels : List[str]) -> (pd.DataFrame, Dict):
    X, y = extract_X_y(data_df, X_labels)
    y_pred = model.predict(X)
    y_prob = [v[1] for v in model.predict_proba(X)]
    data_df['y_pred'] = y_pred
    data_df['y_prob'] = y_prob
    licensers = set(data_df['licenser_id'])
    result_dict = {}
    for licenser in licensers:
        lic_df = data_df[data_df['licenser_id'] == licenser]
        rows = lic_df.to_dict('records')
        rows.sort(key=lambda d : d['y'])
        good = [d for d in rows if d['y'] == 1]
        good_index = rows.index(good[0])
        rows = rows[:good_index+1] # eliminate duplicates
        good = rows[-1]
        rows.sort(key=lambda d : -d['y_prob'])
        good_rank = rows.index(good)
        false_positives = [d for d in rows if d['y'] == 0 and d['y_pred'] == 1]
        false_negatives = [d for d in rows if d['y'] == 1 and d['y_pred'] == 0]
        result_dict[licenser] = (good_rank, len(false_positives), len(false_negatives))
    return data_df, result_dict
