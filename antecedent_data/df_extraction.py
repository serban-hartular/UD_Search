import math
from collections import defaultdict
from typing import List, Dict

import pandas as pd

import antecedent_data as ad
import tree_path
from tree_path import ParsedSentence, ParsedDoc, Search
from antecedent_data import ComplexPredicate

def extract_possible_pairs(doc : ParsedDoc) -> (List[Dict], List[ComplexPredicate]):
    groups = []
    for sentence in doc:
        groups.extend(ad.group_statements(sentence))
    rel_dict = defaultdict(str, ad.get_syntactic_rels(groups))
    candidate_list = []
    for m in doc.search('.//[misc.Ellipsis=VPE misc.Antecedent=Present,External]'):
        licenser = m.node
        target_id = licenser.sdata('misc.TargetID')
        if not target_id:
            continue
        target, sent = doc.get_node_by_uid(target_id)
        if not target:
            raise Exception('Could not find antecedent ' + target_id)
        e_group = [g for g in groups if licenser in g][0]
        a_group = [g for g in groups if target in g]
        if not a_group:
            print('Error: antecedent %s not in candidates' % target_id)
            continue
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
                                  'y':int(node == target) }
                candidate_list.append(candidate_dict)
            prev_group = g
    return candidate_list, groups

def add_distance_data(d : Dict, doc : ParsedDoc, groups : List[ComplexPredicate]):
    tok_dist = doc.get_token_distance(d['candidate'], d['licenser'])
    cataphoric = int(tok_dist < 0)
    tok_dist = abs(tok_dist)
    syn_dist = abs(doc.get_syntactic_distance(d['candidate'], d['licenser']))
    group_dist = abs(groups.index(d['candidate_group']) - groups.index(d['licenser_group']))
    d.update({'cataphoric':cataphoric, 'tok_dist':tok_dist, 'syn_dist':syn_dist, 'group_dist':group_dist})

import word_modality as wm

def add_modality_data(d : Dict):
    licenser = d['licenser']
    candidate = d['candidate']
    d.update(wm.get_modality_record(licenser, candidate))
    d['subjunctive'] = int(bool(Search('/[upos=PART lemma=să]').find(candidate)))

def post_process(d : Dict):
    for label in ('tok_dist', 'syn_dist', 'group_dist'):
        d['ln2_'+label] = math.log2(d[label]) if d[label] >= 1 else -1

def filter_objects(d : Dict) -> Dict:
    fd = {k:v for k,v in d.items() if isinstance(v, str) or isinstance(v, int) or isinstance(v, float)}
    for label in ('candidate_licenser_rel', 'candidate_precedent_rel'):
        fd[label] = int(bool(fd[label]))
    return fd

def filtered_dict_to_df(fd : List[Dict], balance_flag : bool = True) -> pd.DataFrame:
    df = pd.DataFrame(fd)
    if not balance_flag:
        return df
    licensers = set(df['licenser_id'])
    for licenser in licensers:
        # count candidates
        candidate_count = len(df[df['licenser_id'] == licenser])
        good_row = df[(df['y']==1) & (df['licenser_id']==licenser)]
        if good_row.empty:
            print('Error: licenser %s has no correct value' % licenser)
            continue
        df = df.append([good_row]*(candidate_count-2), ignore_index=True)
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
