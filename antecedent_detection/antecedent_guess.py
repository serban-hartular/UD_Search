from __future__ import annotations

from collections import defaultdict
from typing import List, Tuple, Dict

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

def guess_antecedents(doc : tp.ParsedDoc, licensers : List[tp.Tree], model : Model,
                     labels : List[str], correct_antecedent_ids_typestr : List[Tuple[str, str]] = None) \
        -> List[Tuple[str, float]]:
    antecedent_guesses = []
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
        df = antecedent_detection.df_extraction.filtered_dict_to_df(candidate_list, False)
        X = df[labels]
        y_prob = [v[1] for v in model.predict_proba(X)]
        df['y_prob'] = y_prob
        max_rows = df[df['y_prob'] == df['y_prob'].max()]
        target_id = max_rows.iloc[0]['candidate_id']
        antecedent_guesses.append((target_id, df['y_prob'].max()))
    return antecedent_guesses


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
    guesses = guess_antecedents(doc, licensers, model, labels, [z for z in zip(antecedent_ids, antecedent_types)])
    guessed_ids = [g[0] for g in guesses]
    guessed_probs = [g[1] for g in guesses]
    # for z in zip(licenser_ids, antecedent_ids, guessed_ids, guessed_probs):
    #     print('\t'.join([str(n) for n in z]))
    return [z for z in zip(licenser_ids, antecedent_ids, guessed_ids, guessed_probs)]
