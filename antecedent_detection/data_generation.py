from __future__ import annotations

import math
from collections import defaultdict
from typing import List, Dict, Callable, Optional, Tuple

import pandas as pd

import antecedent_detection
import antecedent_detection as ad
import clause_info.clause_types
import tree_path as tp
from tree_path import Search

group_limits = (30, 10)

DATAGEN_FN = Callable[[Dict, tp.ParsedDoc, List[ad.ComplexPredicate], tp.Tree, tp.Tree, Optional[bool]], Dict]

CANDIDATE_ITERATOR = Callable[[tp.ParsedDoc, List[ad.ComplexPredicate], tp.Tree, ad.ComplexPredicate], List[Tuple[tp.Tree, ad.ComplexPredicate, str]]]
CANDIDATE_ITERATOR.__doc__ = "fn(doc, groups, licenser, licenser_group=None) -> [(candidate, group, type), ...]"
def generate_candidates_for_licenser(doc : tp.ParsedDoc, licenser : tp.Tree, 
                                     groups : List[ad.ComplexPredicate], syntactic_rels : Dict[Tuple, str], 
                                     candidate_gen_fn : CANDIDATE_ITERATOR = None,
                                     antecedent : Tuple[tp.Tree, str] = None) -> List[Dict]:
    if not candidate_gen_fn:
        candidate_gen_fn = list_candidates_with_elliptic_antecedents # list_candidates
    candidate_list = []
    e_group = [g for g in groups if licenser in g]
    if not e_group:
        print('Error: licenser %s not in a group' % doc.uid(licenser))
        return []
    e_group = e_group[0]
    # for g in groups:
    #     for node in g:
    for node, g, typestr in candidate_gen_fn(doc, groups, licenser, e_group):
        if node == licenser:
            continue
        is_good = None if antecedent is None else (antecedent[0] == node and antecedent[1] == typestr)
        candidate_dict = ad.data_generation.candidate_data(
            {}, doc, licenser, node, groups, syntactic_rels, e_group, g, typestr, is_good)
        candidate_list.append(candidate_dict)
    return candidate_list

def list_candidates(doc : tp.ParsedDoc, groups : List[ad.ComplexPredicate], licenser : tp.Tree,
                    licenser_group : ad.ComplexPredicate = None)\
        -> List[Tuple[tp.Tree, ad.ComplexPredicate, str]]:
    cl = []
    if not licenser_group:
        licenser_group = [g for g in groups if licenser in g]
        if not licenser_group:
            raise Exception('Error: licenser %s not in a group' % doc.uid(licenser))
        licenser_group = licenser_group[0]
    if group_limits:
        gi = groups.index(licenser_group)
        start = max(gi-group_limits[0], 0)
        end = min(gi+group_limits[1], len(groups))
        groups = groups[start:end+1]
        
    for g in groups:
        for node in g:
            if node == licenser: continue
            cl.append((node, g, 'Present'))
    return cl

def list_candidates_with_elliptic_antecedents(doc : tp.ParsedDoc, groups : List[ad.ComplexPredicate],
                                              licenser : tp.Tree, licenser_group : ad.ComplexPredicate = None)\
                        -> List[Tuple[tp.Tree, ad.ComplexPredicate, str]]:
    cl = list_candidates(doc, groups, licenser, licenser_group)
    to_add = []
    for node, g, typestr in cl:
        if node != g.bottom(): continue
        if wm.get_node_modality(node, True)[0]: # this is a potential licenser
            if not Search('.[ /[deprel=ccomp,csubj,ccomp:pmod,obj,obl:pmod] | /[deprel=xcomp (upos=VERB|/[deprel=cop])] ]').find(node):
                to_add.append((node, g, 'Elided'))
    return cl + to_add

def candidate_data(data : Dict, doc : tp.ParsedDoc, licenser : tp.Tree, candidate : tp.Tree,
                   groups : List[ad.ComplexPredicate], syntactic_rels : Dict[Tuple, str],
                   licenser_group : ad.ComplexPredicate, antecedent_group : ad.ComplexPredicate,
                   antecedent_type : str, is_good : bool|None = None) -> Dict:
   
    ag_index = groups.index(antecedent_group)
    prev_group = groups[ag_index-1] if ag_index > 0 else None
    data.update({
        'licenser': licenser, 'candidate': candidate,
        'licenser_id': doc.uid(licenser), 'candidate_id': doc.uid(candidate),
        'licenser_group': licenser_group, 'candidate_group': antecedent_group,
        'candidate_licenser_rel': syntactic_rels[(antecedent_group, licenser_group)],
        'is_rel_comp' : int(
            bool(syntactic_rels[(antecedent_group, licenser_group)]) and bool(clause_info.clause_types.is_relative(licenser))
        ),
        'candidate_precedent_rel': syntactic_rels[(prev_group, antecedent_group)],
        'contrast' : int(licenser_group.get_polarity() != antecedent_group.get_polarity()),
        'same_num' : int(is_same_num(licenser, candidate)),
        'same_person' : int(is_same_person(licenser, candidate, {'3'})),
        'antecedent_type':antecedent_type,
    })
    if is_good is not None:     # 'y':int(node == target) }
        data['y'] = int(is_good)
    data = add_distance_data(data, doc, groups)
    data = add_modality_data(data, antecedent_type == 'Elided')
    data = post_process(data)
    data = filter_objects(data)
    return data

def is_same_num(node1 : tp.Tree, node2 : tp.Tree) -> bool:
    return bool(node1.data('misc.Number') and node2.data('misc.Number') and \
        node1.data('misc.Number').intersection(node2.data('misc.Number')))

def is_same_person(node1 : tp.Tree, node2 : tp.Tree, exclude : set = None) -> bool:
    exclude = exclude if exclude else set()
    return bool(node1.data('misc.Person') and node2.data('misc.Person') and \
        node1.data('misc.Person').intersection(node2.data('misc.Person')).difference(exclude))


def add_distance_data(d : Dict, doc : tp.ParsedDoc, groups : List[ad.ComplexPredicate]) -> Dict:
    tok_dist = doc.get_token_distance(d['candidate'], d['licenser'])
    cataphoric = int(tok_dist < 0)
    tok_dist = abs(tok_dist)
    syn_dist = abs(doc.get_syntactic_distance(d['candidate'], d['licenser']))
    group_dist = abs(groups.index(d['candidate_group']) - groups.index(d['licenser_group']))
    d.update({'cataphoric':cataphoric, 'tok_dist':tok_dist, 'syn_dist':syn_dist, 'group_dist':group_dist})
    return d

import word_modality as wm

def add_modality_data(d : Dict, is_elided : bool = False) -> Dict:
    licenser = d['licenser']
    candidate = d['candidate']
    d.update(wm.get_modality_record(licenser, candidate, is_elided))
    d['subjunctive'] = int(bool(Search('/[upos=PART lemma=să]').find(candidate)))
    return d

def post_process(d : Dict) -> Dict:
    for label in ('tok_dist', 'syn_dist', 'group_dist'):
        d['ln2_'+label] = math.log2(d[label]) if d[label] >= 1 else -1
    return d

def filter_objects(d : Dict) -> Dict:
    fd = {k:v for k,v in d.items() if isinstance(v, str) or isinstance(v, int) or isinstance(v, float)}
    for label in ('candidate_licenser_rel', 'candidate_precedent_rel'):
        fd[label] = int(bool(fd[label]))
    return fd
