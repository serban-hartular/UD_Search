from collections import defaultdict
from typing import List

import antecedent_data as ad
import antecedent_data.df_extraction
import tree_path as tp


def generate_candidate_dict():
    pass


class Model:
    def fit(self, X, y):
        pass
    def predict_proba(self, X) -> List[List[float]]:
        pass

def guess_antecedents(doc : tp.ParsedDoc, licensers : List[tp.Tree], model : Model,
                     labels : List[str]) -> List[str]:
    antecedent_ids = []
    groups = ad.group_doc_statements(doc)
    rel_dict = defaultdict(str, ad.get_syntactic_rels(groups))
    for licenser in licensers:
        candidate_list = []
        e_group = [g for g in groups if licenser in g]
        if not e_group:
            print('Error: licenser %s not in a group' % doc.uid(licenser))
            continue
        e_group = e_group[0]
        prev_group = None
        for g in groups:
            for node in g:
                if node == licenser:
                    continue
                candidate_dict = {'licenser':licenser, 'candidate':node,
                                  'licenser_id':doc.uid(licenser), 'candidate_id':doc.uid(node),
                                  'licenser_group':e_group, 'candidate_group':g,
                                  'candidate_licenser_rel':rel_dict[(g, e_group)],
                                  'candidate_precedent_rel':rel_dict[(prev_group, g)],
                                  } #'y':int(node == target) }
                antecedent_data.df_extraction.add_distance_data(candidate_dict, doc, groups)
                antecedent_data.df_extraction.add_modality_data(candidate_dict)
                antecedent_data.df_extraction.post_process(candidate_dict)
                candidate_dict = antecedent_data.df_extraction.filter_objects(candidate_dict)
                candidate_list.append(candidate_dict)
            prev_group = g
        # we have the candidates
        df = antecedent_data.df_extraction.filtered_dict_to_df(candidate_list, False)
        X = df[labels]
        y_prob = [v[1] for v in model.predict_proba(X)]
        df['y_prob'] = y_prob
        max_rows = df[df['y_prob'] == df['y_prob'].max()]
        target_id = max_rows.iloc[0]['candidate_id']
        antecedent_ids.append(target_id)
    return antecedent_ids

columns = ['candidate_licenser_rel', 'candidate_precedent_rel', 'cataphoric', 'same_lemma', 'same_modality', 'same_mod_class', 'epist_e', 'aprecia_e', 'aspect_e', 'deont_e', 'dicendi_e', 'epist_a', 'aprecia_a', 'aspect_a', 'deont_a', 'dicendi_a', 'subjunctive', ]
group_dist = ['group_dist']

def test_guess_antecedent(doc : tp.ParsedDoc, model : Model, labels : List[str] = None):
    """Assumes doc is annotated"""
    if not labels:
        labels = columns + group_dist 
    licensers = [m.node for m in doc.search('.//[misc.Ellipsis=VPE misc.Antecedent=Present,External]')]
    licenser_ids = [doc.uid(l) for l in licensers]
    antecedents = [n.sdata('misc.TargetID') for n in licensers]
    guesses = guess_antecedents(doc, licensers, model, labels)
    # print('\t'.join(['licenser', 'antecedent', 'guess']))
    for z in zip(licenser_ids, antecedents, guesses):
        print('\t'.join(z))
