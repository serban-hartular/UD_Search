from __future__ import annotations

from collections import defaultdict
from io import StringIO
from typing import List, Dict

import pandas as pd

import valences


def vdf_datum_to_list(value) -> List[str]:
    if pd.isna(value):
        return []
    value = value.split(',')
    value = [v.strip() for v in value]
    return value

def create_present_absent_deprels(valence_row : dict) -> (List[str], List[str]):
    elided = valence_row['Ellided'].strip()
    absent = vdf_datum_to_list(valence_row['Absent'])
    default_absent = vdf_datum_to_list(valence_row['Default Absent'])
    present = vdf_datum_to_list(valence_row['Prezent'])
    other_absent = vdf_datum_to_list(valence_row['Prophylactic Absent'])
    absent.append(elided)
    absent.extend([d for d in default_absent if d not in present])
    absent.extend(other_absent)
    return present, absent

import tree_path as tp
from tree_path import Search, Tree


def vdf_string_to_search(src : str) -> Search:
    if '|' in src:
        src = src.split('|')
        src = [s.strip() for s in src]
        src = ['deprel='+s for s in src]
        src = '|'.join(src)
        return Search('/[%s]' % src)
    if '?' in src: # like obl?despre, expl:pv?dat
        [deprel, arg] = src.split('?')
        if deprel == 'obl': 
            return Search('/[deprel=%s /[lemma=%s] ]' % (deprel, arg))
        elif deprel=='expl:pv':
            #dative or accusiative?
            if arg not in ('dat', 'acc'): raise Exception('Unkown %s case %s' % (deprel, arg))
            case = arg[0].upper() + arg[1:]
            return Search('/[deprel=%s feats.Case=%s]' % (deprel, arg))
        elif deprel == 'xcomp':
            #xcomp?verb if verbal, xcomp?nonverb
            if arg not in ('verb', 'nonverb'): raise Exception('Unknown %s type %s' % (deprel, arg))
            if arg == 'verb': return Search('/[deprel=xcomp (upos=VERB & !misc.Mood=Part | /[deprel=cop,aux:pass] ) ]')
            else: return Search('/[deprel=xcomp !(upos=VERB & !misc.Mood=Part | /[deprel=cop,aux:pass] ) ]')
        else:
            raise Exception('Unknown thing ' + src)
    return Search('/[deprel=%s]' % src)

class DeprelValence:
    def __init__(self, present_deprels : List[str], absent_deprels : List[str], ellide : str = ''):
        self.present_deprels = [vdf_string_to_search(s) for s in present_deprels]
        self.absent_deprels = [vdf_string_to_search(s) for s in absent_deprels]
        self.present_repr = present_deprels
        self.absent_repr = absent_deprels
        self._test_dict = {True:self.present_deprels, False:self.absent_deprels}
        self.ellide = ellide
    def matches(self, node : Tree) -> bool:
        # if node is an infinitive complement of _putea_, we need to add _putea_'s complements to it
        # ie "îi pot da ceva" -- îi is the iobj of _da_, but is parsed as depending on _pot_
        node = DeprelValence.modal_verb_pass_complements(node)
        # now test if it matches conditions
        for value, test_list in self._test_dict.items():
            for test in test_list:
                if bool(test.find(node)) != value:
                    return False
        return True
    @staticmethod
    def modal_verb_pass_complements(node : Tree) -> Tree:
        if not Search('.[misc.Mood=Inf deprel=ccomp ../[lemma=putea,trebui] ]').find(node):
            return node # is not complement of modal verb
        # modal's children
        modals_deprels = ['nsubj', 'csubj', 'iobj', 'obl:pmod',
                          'expl:pv', 'expl:impers', 'expl:pass',
                          'obl']
        modal_children = [child for child in node.parent.children()
                          if child != node and child.data('deprel') in modals_deprels ]
        dummy_node = Tree(dict(node.data()), node.parent, node.children() + modal_children)
        return dummy_node
        
    def __str__(self):
        return str({True:self.present_repr, False:self.absent_repr, 'ellide':self.ellide})
    def __repr__(self):
        return str(self)
    @staticmethod
    def from_valence_df_dict(valence_row : dict) -> DeprelValence:
        present, absent = create_present_absent_deprels(valence_row)
        return DeprelValence(present, absent, valence_row['Ellided'])
            
# read _data files, init tables
import pkgutil
data = pkgutil.get_data(__package__, 'elliptic_valences.txt')
data = StringIO(data.decode('utf-8'))
ev_df = pd.read_csv(data, sep='\t') 

# ev_df = pd.read_csv('elliptic_valences.txt', sep='\t')
ev_dict = ev_df.to_dict(orient='index')
lemma_valence_dict = defaultdict(list)
for k,v in ev_dict.items():
    lemma_valence_dict[v['Lemma']].append(DeprelValence.from_valence_df_dict(v))

lemma_valence_dict : Dict[str, List[DeprelValence]] = dict(lemma_valence_dict)

def get_matching_valences(node : Tree) -> List[DeprelValence]:
    full_lemma = str(valences.get_verb_lemma(node))
    if full_lemma not in lemma_valence_dict:
        return []
    vals = [dep_val for dep_val in lemma_valence_dict[full_lemma] if dep_val.matches(node)]
    return vals
