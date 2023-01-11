from __future__ import annotations

from io import StringIO
from typing import Dict, Set, List, Tuple
from tree_path import Tree, Match, Search
import pandas as pd

# read _data files, init tables
import pkgutil

from tree_path.conllu import get_full_lemma

data = pkgutil.get_data(__package__, 'modalizers.txt')
data = StringIO(data.decode('utf-8'))
mod_df = pd.read_csv(data, sep='\t') 

data = pkgutil.get_data(__package__, 'modality_classes.txt')
data = StringIO(data.decode('utf-8'))
mod_class_df = pd.read_csv(data, sep='\t') 

mod_class_dict = {z[0]:z[1] for z in zip(mod_class_df['modalities'], mod_class_df['class'])}
class_set = set(mod_class_dict.values())
polarities = ('POS', 'POS_CONST', 'NEG', 'NEG_CONST')

def get_modality(lemma : str, deprel : str = '', particle : str = '') -> List[Tuple[str, str, str]]:
    rows = mod_df[(mod_df['regent']==lemma)]
    if deprel:
        rows = rows[rows['deprel']==deprel]
    if particle:
        rows = rows[rows['particle']==particle]
    if rows.empty: return []
    rows = rows.to_dict('records') # list of dicts {'column1':'valueX', 'column2':'valueY', etc }
    # for now we just select the first
    row = rows[0]
    row = {k:v for k,v in row.items() if v and pd.notna(v)}
    # make a list of modality tuples
    mod_tuples = []
    for mod, pol in zip(['modality1', 'modality2'], ['polarity1', 'polarity2']):
        if mod not in row: continue
        mod_tuples.append((lemma, row[mod], row[pol] if pol in row and row[pol] in polarities else polarities[0])) # default is POS
    return mod_tuples

def get_node_modality(node : Tree, licenser_flag : bool) -> (List[Tuple[str, str]], List[str]):
    neg_search = Search('/[_lemma=nu upos=PART]')
    mod_tuples = []
    deprel = ''
    if not licenser_flag:
        deprel = node._data['deprel']
        node = node.parent # look at antecedent's parent
        if deprel in ['conj', 'parataxis']: # move one up
            deprel = node._data['deprel']
            node = node.parent
    if not node: return [],[]
    regent = get_full_lemma(node)
    # we'll do the sconj later
    mod_tuples = get_modality(regent, deprel)
    neg_flag = neg_search.find(node)
    for i,t in enumerate(mod_tuples):
        if t[2].endswith('_CONST'):
            pol = t[2][0:-len('_CONST')] # chop off _CONST
        elif neg_flag:
            pol = 'POS' if t[1] == 'NEG' else 'NEG'
        else:
            pol = t[2]
        mod_tuples[i] = (t[0], t[1], pol)
    class_list = [mod_class_dict[t[1]] for t in mod_tuples]
    return mod_tuples, class_list

def get_modality_record(ellipsis : Tree, antecedent : Tree):
    ellipsis_mod, ellipsis_class = get_node_modality(ellipsis, True)
    antecedent_mod, antecedent_class = get_node_modality(antecedent, False)
    same_lemma, same_modality, same_mod_class = 0, 0, 0
    if ellipsis_mod and antecedent_mod:
        same_lemma = int(ellipsis_mod[0][0] == antecedent_mod[0][0])
        for emt in ellipsis_mod:
            for amt in antecedent_mod:
                if emt[1] == amt[1]:
                    same_modality = 1
                    break
        same_mod_class = int(bool([cl for cl in antecedent_class if cl in ellipsis_class]))
    pair_mod_dict = {'same_lemma':same_lemma, 'same_modality':same_modality, 'same_mod_class':same_mod_class}
    for suffix, class_list in zip(['_e', '_a'], [ellipsis_class, antecedent_class]):
        for cl in class_set:
            pair_mod_dict[cl + suffix] = int(cl in class_list)
    return pair_mod_dict
