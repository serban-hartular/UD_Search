from io import StringIO
from typing import List

from tree_path import Tree, Search
from tree_path.conllu import get_full_lemma, before

def children_before(node : Tree):
    return [c for c in node.children() if before(c, node)]

def is_rel_word(node : Tree) -> bool:
    if 'PronType' in node.data['feats'] and node.data['feats']['PronType'].intersection({'Int', 'Rel'}):
        return True
    if get_full_lemma(node) in ['orice', 'oricine', 'oricând', 'oriunde', 'oricum']:
        return True
    for child in node.children():
        if child.data['deprel'] == 'fixed' and is_rel_word(child):
            return True
    return False

def get_head(clause : Tree) -> List[Tree]:
    elems = []
    for pre in children_before(clause):
        if pre.data['deprel'] in ('cc', 'mark'):
            elems.append(pre)
        if is_rel_word(pre):
            elems.append(pre)
    return elems

def is_negative(clause : Tree) -> bool:
    return bool(Search('/[lemma=nu upos=PART feats.Polarity=Neg]').find(clause))

import pkgutil
import pandas as pd
data = pkgutil.get_data(__package__, 'clause_heads.txt')
data = StringIO(data.decode('utf-8'))
clause_heads_df = pd.read_csv(data, sep='\t') 

def get_head_types(clause : Tree) -> List[str]:
    type_list = []
    elems = get_head(clause)
    df = clause_heads_df
    for e in elems:
        e_lemma, e_deprel = get_full_lemma(e), e.data['deprel']
        rows = df[(df['head']==e_lemma) & (df['deprel']==e_deprel)]
        if rows.empty: continue
        fn = rows.iloc[0]['function']
        if pd.notna(fn):
            type_list.append(str(fn))
    return type_list
