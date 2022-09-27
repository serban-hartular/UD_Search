from __future__ import annotations

from io import StringIO
from typing import List

from tree_path import Tree, Search
from tree_path.conllu import before, get_full_lemma


def children_before(node : Tree):
    return [c for c in node.children() if before(c, node)]

def is_rel_word(node : Tree) -> Tree|None:
    if 'PronType' in node.data['feats'] and node.data['feats']['PronType'].intersection({'Int', 'Rel'}):
        return node
    if get_full_lemma(node) in ['orice', 'oricine', 'oricând', 'oriunde', 'oricum']:
        return node
    for child in node.children():
        if child.data['deprel'] in ['fixed', 'advmod']:
            rel_w = is_rel_word(child)
            if rel_w: return rel_w if child.data['deprel'] == 'advmod' else node
    return None

def get_head(clause : Tree) -> List[Tree]:
    elems = []
    for pre in children_before(clause):
        if pre.data['deprel'] in ('cc', 'mark'):
            elems.append(pre)
        if is_rel_word(pre):
            elems.append(is_rel_word(pre))
    return elems

def is_negative(clause : Tree) -> bool:
    return bool(Search('/[lemma=nu upos=PART feats.Polarity=Neg]').find(clause))

import pkgutil
import pandas as pd
data = pkgutil.get_data(__package__, 'clause_heads.txt')
data = StringIO(data.decode('utf-8'))
clause_heads_df = pd.read_csv(data, sep='\t') 

def get_head_types(clause : Tree) -> (List[str], bool, bool):
    """Returns list of head types (eg 'cauza-efect' for 'pentru că')
    Returns True if one of the heads indicates a contrast (eg 'dar', 'deși')
    Returns True if a head (eg 'fără') changes the polarity of the clause 
        (eg 'fără să vrea' means 'deși _nu_ a vrut')
     """
    type_list = []
    elems = get_head(clause)
    df = clause_heads_df
    contrast = False
    polarity_change = False
    for e in elems:
        e_lemma, e_deprel = get_full_lemma(e), e.data['deprel']
        rows = df[(df['head']==e_lemma) & (df['deprel']==e_deprel)]
        if rows.empty: continue
        fn = rows.iloc[0]['function']
        if pd.notna(fn):
            type_list.append(str(fn))
        if rows.iloc[0]['contrast'] == 'Y':
            contrast = True
        if (e_lemma, e_deprel) == ('fără', 'mark'):
            polarity_change = True
    return type_list, contrast, polarity_change
