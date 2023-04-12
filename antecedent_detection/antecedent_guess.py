from __future__ import annotations

import dataclasses
from collections import defaultdict
from typing import List, Tuple, Dict

import pandas as pd

import antecedent_detection as ad
import antecedent_detection.df_extraction
import tree_path as tp
from antecedent_detection.labels import columns, group_dist


class Model:
    def __init__(self, **kwargs):
        pass
    def fit(self, X, y):
        pass
    def predict_proba(self, X) -> List[List[float]]:
        pass
    def score(self, X, y) -> float:
        pass

def antecedent_proba_to_df(df : pd.DataFrame, model : Model, labels : List[str], y_prob_column : str = 'y_prob'):
    X = df[labels]
    y_prob = [v[1] for v in model.predict_proba(X)]
    df[y_prob_column] = y_prob
    return df

@dataclasses.dataclass
class AntecedentData:
    id : str
    type : str
    prob : float
    def matches(self, other : AntecedentData) -> bool:
        return self.id == other.id and self.type == other.type
    

def extract_proba_antecedents_from_df(df : pd.DataFrame) -> Dict[str, AntecedentData]:
    if df.empty:
        return {}
    antec_dict : Dict[str, AntecedentData]= {}
    if 'y_prob' not in df.columns:
        raise Exception('Column y_prob not present!')
    
    licensers = set(df['licenser_id'])
    for licenser_id in licensers:
        df_lic = df[df['licenser_id']==licenser_id]
        max_prob = df_lic['y_prob'].max()
        max_rows = df_lic[df_lic['y_prob'] == max_prob]
        target_id = max_rows.iloc[0]['candidate_id']
        antec_type = max_rows.iloc[0]['antecedent_type']
        antec_dict[licenser_id] = AntecedentData(target_id, antec_type, max_prob)
    return antec_dict

def extract_correct_antecedents_from_df(df : pd.DataFrame) -> Dict[str, AntecedentData]:
    if 'y' not in df.columns:
        raise Exception('Column "y" not present!')
    antec_dict : Dict[str, AntecedentData]= {}
    licensers = set(df['licenser_id'])
    for licenser_id in licensers:
        good_row = df[(df['licenser_id']==licenser_id) & (df['y']==1)]
        if len(good_row) != 1:
            raise Exception("Licenser %s has %d good antecedents!" % (licenser_id, len(good_row)))
        good_row = good_row.iloc[0]
        antec_dict[licenser_id] = AntecedentData(good_row['candidate_id'], good_row['antecedent_type'], good_row['y'])
    return antec_dict

def guess_antecedents(doc : tp.ParsedDoc, licensers : List[tp.Tree], model : Model,
                     labels : List[str], correct_antecedent_ids_typestr : List[Tuple[str, str]] = None) \
        -> (List[Tuple[str, float, str]], pd.DataFrame):
    antecedent_guesses : List[Tuple[str, float, str]] = []
    data_df = pd.DataFrame()
    groups = ad.group_doc_statements(doc)
    rel_dict = defaultdict(str, ad.get_syntactic_rels(groups))
    for i, licenser in enumerate(licensers):
        candidate_list = ad.data_generation.generate_candidates_for_licenser(doc, licenser, groups, rel_dict)
        # let's make sure the correct antecedent is in the list
        go_ahead = True
        if correct_antecedent_ids_typestr:
            lic_id = doc.uid(licenser)
            (ant_id, ant_type) = correct_antecedent_ids_typestr[i]
            q = [d for d in candidate_list if d['licenser_id'] == lic_id and d['candidate_id'] == ant_id
                 and d['antecedent_type']==ant_type ]
            if not q:
                print('Error! For licenser %s, correct antecedent %s (%s) not generated.' %
                          (lic_id, ant_id, ant_type))
                go_ahead = False
        # done with making make sure these are among the candidates
        if not go_ahead:
            continue
        df = antecedent_detection.df_extraction.filtered_dict_to_df(candidate_list)
        # X = df[labels]
        # y_prob = [v[1] for v in model.predict_proba(X)]
        # df['y_prob'] = y_prob
        df = antecedent_proba_to_df(df, model, labels)
        max_rows = df[df['y_prob'] == df['y_prob'].max()]
        target_id = max_rows.iloc[0]['candidate_id']
        antec_type = max_rows.iloc[0]['antecedent_type']
        antecedent_guesses.append((target_id, df['y_prob'].max(), antec_type))
        data_df = pd.concat([data_df, df], ignore_index=True)
    return antecedent_guesses, data_df


def test_guess_antecedent(doc : tp.ParsedDoc, model : Model, labels : List[str] = None) -> List[Tuple]:
    """ Assumes doc is annotated.
        Returns list of tuple for each antecedent:
            (licenser_id, correct_antecedent_id, guessed_antecedent_id, guess_probability) """
    if not labels:
        labels = columns + group_dist 
    licensers = [m.node for m in doc.search('.//[misc.Ellipsis=VPE misc.Antecedent=Present,External,Elided]')]
    licenser_ids = [doc.uid(l) for l in licensers]
    antecedent_ids = [n.sdata('misc.TargetID') for n in licensers]
    antecedent_types = [l.sdata('misc.Antecedent') for l in licensers]
    antecedent_types = ['Present' if at == 'External' else at for at in antecedent_types]
    guesses, df = guess_antecedents(doc, licensers, model, labels, [z for z in zip(antecedent_ids, antecedent_types)])
    guessed_ids = [g[0] for g in guesses]
    guessed_probs = [g[1] for g in guesses]
    # for z in zip(licenser_ids, antecedent_ids, guessed_ids, guessed_probs):
    #     print('\t'.join([str(n) for n in z]))
    return [z for z in zip(licenser_ids, antecedent_ids, guessed_ids, guessed_probs)]
