from __future__ import annotations

from typing import List, Dict

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import AdaBoostClassifier, BaggingClassifier, ExtraTreesClassifier, GradientBoostingClassifier, \
    RandomForestClassifier
from sklearn.naive_bayes import ComplementNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.semi_supervised import LabelPropagation, LabelSpreading

from tree_path import parsed_doc
import training_data
import pandas as pd

def generate_training_data(conllu_in : str) -> pd.DataFrame:
    df = pd.DataFrame()
    for pdoc in parsed_doc.iter_docs_from_conll(conllu_in):
        # for pair in generate_clause_pairs(pdoc):
        #     print(pair)
        df = pd.concat([df, training_data.generate_clause_pair_df(training_data.generate_clause_pairs(pdoc), pdoc)], ignore_index=True)
    return df


from sklearn.tree import DecisionTreeClassifier, ExtraTreeClassifier

predictor_classes = [AdaBoostClassifier, BaggingClassifier, ComplementNB, DecisionTreeClassifier, ExtraTreeClassifier, ExtraTreesClassifier,
                     GradientBoostingClassifier, KNeighborsClassifier,
                     LabelPropagation, LabelSpreading, LinearDiscriminantAnalysis,
                     MultinomialNB, RandomForestClassifier]

def join_str(sep:str, items:List):
    return sep.join([str(i) for i in items])


modality_variables = ['deont_e', 'deont_a', 'aspect_e', 'aspect_a', 'epist_e', 'epist_a',
                 'aprecia_e', 'aprecia_a', 'dicendi_e', 'dicendi_a', 'same_lemma', 'same_modality']

def df_to_X_y(df : pd.DataFrame, features : List[str]) -> (pd.DataFrame, pd.DataFrame):
    X = df[features]
    y = df['result']
    return X, y

def get_probabilities(predictor, data_df : pd.DataFrame, variable_names : List[str]) -> pd.DataFrame:
    X = data_df[variable_names]
    y_pred = predictor.predict_proba(X)
    y_pred_df = pd.DataFrame(y_pred, columns=['prob0', 'prob1'])
    return y_pred_df.set_index(X.index)

def most_probable_antecedent(predictor, e_uid : str, data_df : pd.DataFrame) -> (str, float):
    """Returns the uid and the probability of the most probable antecedent"""
    # filter for e_uid
    df = data_df[data_df['e_uid']==e_uid] # filter for e_uid
    y_pred_df = get_probabilities(predictor, df)
    pred_df = pd.concat([df, y_pred_df], axis=1)
    scores = [z for z in zip(pred_df['a_uid'], pred_df['prob1'])]
    scores.sort(key=lambda t: -t[1])
    return scores[0]

def correct_antecedent(e_uid : str, data_df : pd.DataFrame, predictor = None) -> (str, float):
    """Returns a_uid where result is 1. If predictor is not None, calculates
    probability and returns that as well (otherwise probability -1)
    """
    df = data_df[data_df['e_uid'] == e_uid]  # filter for e_uid
    df = df[df['result']==1]
    if df.empty: return '',-1
    if len(df.index) > 1: raise Exception('More than one correct antecedent for e_uid ' + e_uid)
    row = df.iloc[0].to_dict()
    a_uid = row['a_uid']
    if predictor is not None:
        y_pred_df = get_probabilities(predictor, df)
        prob1 = y_pred_df.iloc[0]['prob1']
    else:
        prob1 = -1
    return a_uid, prob1

# def evaluate_predictor(predictor, ellipsis_ids : Iterable[str], df_to_test : pd.DataFrame) -> (float, float, int): 
#     good, count, same = 0, 0, 0
#     for e_uid in ellipsis_ids:
#         good_antecedent, good_prob = correct_antecedent(e_uid, df_to_test, predictor)
#         guessed_antecedent, guessed_prob = most_probable_antecedent(predictor, e_uid, df_to_test)
#         if good_antecedent == guessed_antecedent:
#             good += 1
#             # print('1', end='\t')
#         elif good_prob == guessed_prob:
#             same += 1
#             # print('0.5', end='\t')
#         else:
#             pass
#             # print('0', end='\t')
#         # print(df_to_test[df_to_test['a_uid']==good_antecedent].iloc[0]['syntactic_distance_log'])
#         count += 1
#     return good/count, same/count, count

class EllipsisGuessDict(Dict[str, List]):
    def __init__(self, e_uid : str, d : Dict[str, List]):
        super().__init__(d)
        self.e_uid = e_uid
    def get_good(self) -> str:
        for a_uid, params in self.items():
            if 'GOOD' in params:
                return a_uid
        return None
    def get_guess(self) -> str|None:
        guesses = [a_uid for a_uid, params in self.items() if 'GUESS' in params]
        if not guesses: return None
        return guesses[0]
    def get_eval(self) -> bool:
        return self.get_good() and self.get_guess() == self.get_good()
        # if self.get_good() in self.get_guess():
        #     return 'GOOD' if len(self.get_guess()) == 1 else 'TIE'
        # return 'BAD'

def get_ellipses_dict(df_data : pd.DataFrame, df_probs : pd.DataFrame, 
                      variables:List[str], float_variables:List[str]) \
        -> Dict[str, EllipsisGuessDict]:
    df_all = pd.concat([df_data, df_probs], axis=1)
    ellipsis_ids = set(df_all['e_uid'])
    all_ell_dict = {}
    for e_uid in ellipsis_ids:
        df = df_all[df_all['e_uid']==e_uid]
        df_dict_list = df.to_dict('index')
        ell_dict = {}
        # determine guess
        max_prob = df['prob1'].max()
        max_rows = df[df['prob1']==max_prob]
        if len(max_rows)>1:
            # print('Using DIST_LN')
            max_rows = max_rows[max_rows['DIST_LN']==max_rows['DIST_LN'].min()]
        if len(max_rows)>1:
            # print('Using CATA')
            max_rows = max_rows[max_rows['CATA'] == 0]
        if max_rows.empty: raise Exception('No guess determined for ' + e_uid)
        guess_uid = max_rows.iloc[0]['a_uid']
        for row in df_dict_list.values():
            a_uid = row['a_uid']
            antec_list = [row[k] for k in ['prob1']+float_variables]
            antec_list += [k for k in variables if row[k] and k not in float_variables]
            if row['result'] == 1: antec_list.append('GOOD')
            if row['a_uid'] == guess_uid: antec_list.append('GUESS')
            ell_dict[a_uid] = antec_list
        all_ell_dict[e_uid] = EllipsisGuessDict(e_uid, ell_dict)
    return all_ell_dict

def uid_dicts_from_ellipses_dict(ellipses_dict: Dict[str, Dict[str, List]]) -> Dict[str, Dict[str, str]]:
    """For use with parsed_doc.display_uids_from_file"""
    e_uid_dict = {}
    for e_uid, e_rec in ellipses_dict.items():
        e_uid_dict[e_uid] = {}
        e_params = set()
        for a_uid, params in e_rec.items():
            a_string = ''
            for param in params:
                if isinstance(param, str) and param.endswith('_e'):
                    e_params.add(param)
                elif isinstance(param, float): # number
                    a_string += ('%.2f' % param + ' ')
                else:
                    a_string += (str(param) + ' ')
            e_uid_dict[e_uid][a_uid] = '('+a_string.strip()+')'
        e_params = ['ELL'] + list(e_params)
        e_uid_dict[e_uid][e_uid] = '('+' '.join(e_params)+')'
    return e_uid_dict

import itertools

def get_modality_score(row_dict : Dict) -> int:
    mod_classes = [{'deont', 'aprecia', 'aspect'}, {'epist', 'dicendi'}]
    mod_labels = set(itertools.chain.from_iterable(mod_classes))
    e_params = {k.strip('_e') for k,v in row_dict.items() if k.endswith('_e') and v and k.strip('_e') in mod_labels}
    a_params = {k.strip('_a') for k, v in row_dict.items() if k.endswith('_a') and v and k.strip('_a') in mod_labels}
    modality_score = 0
    if row_dict['same_lemma']:
        modality_score = 4
    elif row_dict['same_modality']:
        modality_score = 3
    elif e_params.intersection(a_params):
        modality_score = 1 + len(e_params.intersection(a_params)) # typically 2
    else:
        for mod_class in mod_classes:
            if e_params.intersection(mod_class) and a_params.intersection(mod_class):
                modality_score = 1
                break
    return modality_score

def add_new_params(df_data : pd.DataFrame) -> pd.DataFrame:
    
    ellipsis_ids = set(df_data['e_uid'])
    mod_score_dict = {}
    for e_uid in ellipsis_ids:
        df = df_data[df_data['e_uid']==e_uid]
        antec_uids = set(df['a_uid'])
        for a_uid in antec_uids:
            row_dict = df[df['a_uid']==a_uid].iloc[0].to_dict()
            index = df[df['a_uid']==a_uid].index[0]
            modality_score = get_modality_score(row_dict)
            mod_score_dict[index] = [modality_score]
    mod_score_df = pd.DataFrame.from_dict(mod_score_dict, orient='index', columns=['MODSCOR'])
    return pd.concat([df_data, mod_score_df], axis=1)

df_train = pd.read_pickle('cancan_annot/cancan21-train-df.p')
df_test = pd.read_pickle('cancan_annot/cancan21-test-df.p')

test_conllu = './cancan21-test-annot-vpe.1.conllu'
train_conllu = './cancan21-train-vpeonly.0.conllu'

# df_train = generate_training_data(train_conllu)
# df_test = generate_training_data(test_conllu)
# df_train.to_pickle('./cancan21-train-df.p')
# df_test.to_pickle('./cancan21-test-df.p')

model_variables = [f for f in df_train.columns if f not in ['result', 'a_uid', 'e_uid']]

# CATA,
model_variables = """CCOM, rel_e, POLCNTRST, SDIST_LN, DIST_LN,
CCONTRST_e, CCONTRST_a, cauza-efect_e,
cauza-efect_a
""".replace(' ', '').replace('\n','').split(',') + ['MODSCOR'] #modality_variables

df_train = add_new_params(df_train)
df_test = add_new_params(df_test)

X_train, y_train = df_to_X_y(df_train, model_variables)
X_test, y_test = df_to_X_y(df_test, model_variables)


def evaluate_predictor(predictor, df_data : pd.DataFrame, features : List[str]) -> (float, List[str]):
    no_good = []
    good, count = 0.0, 0.0
    df_probs = get_probabilities(predictor, df_data, features)
    ellipsis_dicts = get_ellipses_dict(df_data, df_probs, features,
                                       ['SDIST', 'SDIST_LN', 'DIST', 'DIST_LN'])
    for e_uid, guess_dict in ellipsis_dicts.items():
        if not guess_dict.get_good():
            no_good.append(e_uid)
        else:
            if guess_dict.get_eval():
                good += 1
            count += 1
    return good/count, no_good        

# e_uid_dicts = uid_dicts_from_ellipses_dict(ellipsis_dicts)
# print('\t'.join(['e_uid', 'good', 'guess', 'eval']))

# predictor_classes = [DecisionTreeClassifier, KNeighborsClassifier, BaggingClassifier, LabelPropagation]

print('predictor\ttrain\ttest')
# for predictor in predictor_classes:
predictor = LinearDiscriminantAnalysis()
for var_skip in [''] + model_variables:
    features = [f for f in model_variables if f != var_skip]
    X_train, y_train = df_to_X_y(df_train, features)
    predictor = predictor.fit(X_train, y_train)
    p_train, _ =   evaluate_predictor(predictor, df_train, features)
    p_test, no_good = evaluate_predictor(predictor, df_test, features)
    print(join_str('\t', [var_skip, p_train, p_test]))

X_train, y_train = df_to_X_y(df_train, model_variables)
predictor = LinearDiscriminantAnalysis().fit(X_train, y_train)
df_probs = get_probabilities(predictor, df_test, model_variables)
ell_dict = get_ellipses_dict(df_test, df_probs, model_variables, ['SDIST_LN', 'DIST_LN', 'MODSCOR'])
ell_bad = {k:v for k,v in ell_dict.items() if not v.get_eval()}
