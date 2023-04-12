from collections import defaultdict
from typing import List, Dict

import pandas as pd
from sklearn.tree import DecisionTreeClassifier

import tree_path as tp
import annotations as an
import word_modality as wm

# df = an.doclist_to_csv_table(dl, '.[upos=*]', 'df.csv')
# an.annot_table.apply_annotation_df_to_doclist(dl, './df.csv')
import antecedent_detection as ad
from antecedent_detection import ComplexPredicate
from antecedent_detection.antecedent_guess import Model
from antecedent_detection.df_extraction import split_by_licenser_id, extract_X_y
from antecedent_detection.evaluate_model import evaluate_model
from tree_path import Tree, ParsedSentence, ParsedDoc

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import AdaBoostClassifier, BaggingClassifier, ExtraTreesClassifier, GradientBoostingClassifier, \
    RandomForestClassifier
from sklearn.naive_bayes import ComplementNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.semi_supervised import LabelPropagation, LabelSpreading
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegressionCV, LinearRegression

def annotated_doc_to_data_dicts(doc : ParsedDoc, licenser_search : str = None) -> (List[Dict], List[ComplexPredicate]):
    if not licenser_search:
        licenser_search = './/[misc.Ellipsis=VPE misc.Antecedent=Present,External,Elided]'
    candidate_list = []
    groups = ad.group_doc_statements(doc)
    rel_dict = defaultdict(str, ad.get_syntactic_rels(groups))
    for m in doc.search(licenser_search):
        licenser = m.node
        target_id = licenser.sdata('misc.TargetID')
        if not target_id:
            continue
        target = doc.get_node_by_uid(target_id)
        if not target:
            raise Exception('Could not find antecedent ' + target_id)
        target_type = 'Elided' if licenser.sdata('misc.Antecedent') == 'Elided' else 'Present'
        e_group = [g for g in groups if licenser in g][0]
        a_group = [g for g in groups if target in g]
        if not a_group:
            print('Error: antecedent %s not in candidates' % target_id)
            continue
        licenser_candidates = ad.data_generation.generate_candidates_for_licenser(doc, licenser, groups, rel_dict, None,
                                                                                  (target, target_type))
        candidate_list.extend(licenser_candidates)
    return candidate_list

def annotated_doc_to_data_df(doc : ParsedDoc, licenser_search : str = None, **kwargs) -> pd.DataFrame:
    data_list = annotated_doc_to_data_dicts(doc, licenser_search)
    df = ad.df_extraction.filtered_dict_to_df(data_list)
    if kwargs.get('balance') == True:
        df = ad.df_extraction.balance_data_df(df)
    return df

def annotated_doclist_to_data_df(dl : tp.DocList, licenser_search : str = None, **kwargs) -> pd.DataFrame:
    df_all = None
    for doc in dl:
        df_current = annotated_doc_to_data_df(doc, licenser_search, balance=kwargs.get('balance'))
        if df_current.empty:
            continue
        if df_all is None:
            df_all = df_current
        else:
            df_all = pd.concat([df_all, df_current], ignore_index=True)
    return df_all


_default_model_args = defaultdict(dict, {MLPClassifier: {'max_iter':500}, LabelPropagation: {'max_iter':2000}, LogisticRegressionCV:{'max_iter':250}})


def train_model(data_df : pd.DataFrame, X_labels : List[str], model_class = Model, split : int = 4) -> (Model, float, float):
    df_train, df_test = split_by_licenser_id(data_df, split)
    X_train, y_train = extract_X_y(df_train, X_labels)
    X_test, y_test = extract_X_y(df_test, X_labels)
    model = model_class(**_default_model_args[model_class]).fit(X_train, y_train)
    return model, model.score(X_train, y_train), model.score(X_test, y_test)

# #     
# # def train_model(doc_df : pd.DataFrame, model_class, split : int = 4) -> (Model, float, float):
# #     pass
#     
# 
# # print('Extracting data from conllu')
# # dl = tp.DocList.from_conllu('./sent_id_parses/cancan21-annot-2-VPE.correct.conllu')
# # # dl = tp.DocList([doc for doc in dl if doc.search('.//[misc.Ellipsis=VPE]')])
# # filtered_dicts = []
# # for doc in dl:
# #     dicts, groups = extract_possible_pairs(doc)
# #     for d in dicts:
# #         add_distance_data(d, doc, groups)
# #         add_modality_data(d)
# #         post_process(d)
# #     filtered_dicts.extend([filter_objects(d) for d in dicts])
# # 
# # df_all = filtered_dict_to_df(filtered_dicts)
# # df_all.to_csv('./sent_id_parses/cancan21-annot-2-VPE.correct.csv', sep='\t', encoding='utf-8')
# # 
# df_all = pd.read_csv('./sent_id_parses/cancan21-annot-2-VPE.correct.csv', sep='\t', encoding='utf-8')
# 
# columns = ['candidate_licenser_rel', 'candidate_precedent_rel', 'cataphoric', 'same_lemma', 'same_modality',
#            'same_mod_class', 'epist_e', 'aprecia_e', 'aspect_e', 'deont_e', 'dicendi_e', 'epist_a', 'aprecia_a',
#            'aspect_a', 'deont_a', 'dicendi_a', 'subjunctive', ]
# group_dist = ['group_dist', ]
# tok_dist = ['tok_dist', 'syn_dist']
# tok_dist_ln = ['ln2_tok_dist', 'ln2_syn_dist']
# 
# labels = columns + group_dist
# 
# for group in ('all',):
#     model_dict = {}
#     print('Doing %s' % group, end='\t')
#     if group == 'all':
#         df = df_all
#     elif group == 'epistemic':
#         df = pd.DataFrame(df_all[df_all['epist_e'] == 1])
#     else:
#         df = pd.DataFrame(df_all[df_all['epist_e'] == 0])
# 
#     df_train, df_test = split_by_licenser_id(df)
#     print(len(set(df['licenser_id'])), len(set(df_train['licenser_id'])), len(set(df_test['licenser_id'])))
# 
#     model_classes = [LogisticRegressionCV, ExtraTreesClassifier, MLPClassifier, LinearDiscriminantAnalysis,
#                      LabelPropagation,
#                      RandomForestClassifier, LabelSpreading, KNeighborsClassifier, MultinomialNB, BaggingClassifier,
#                      GradientBoostingClassifier,
#                      DecisionTreeClassifier]
# 
#     for model_class in model_classes:
#         model, train_score, test_score = train_model(df, labels, model_class)
#         df, result_dict = evaluate_model(model, df, labels)
#         actual_score = len([v for v in result_dict.values() if v[0] == 0]) / len(result_dict)
#         print(model.__class__.__name__, train_score, test_score, actual_score)
#         model_dict[model.__class__.__name__] = model
# 
# # X_train, y_train = extract_X_y(df_train, columns + group_dist)
# # X_test, y_test = extract_X_y(df_test, columns + group_dist)
# 
# 
