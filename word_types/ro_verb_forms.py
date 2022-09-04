from __future__ import annotations

from io import StringIO
from typing import Dict, Set

from tree_path import Tree, Match, Search

import pandas as pd

# read data files, init tables
import pkgutil
data = pkgutil.get_data(__package__, 'auxiliaries.txt')
_auxiliaries = data.decode('utf-8').split('\n')
_auxiliaries = [l.strip() for l in _auxiliaries if l and l.strip()]

data = pkgutil.get_data(__package__, 'ro_compound_tenses.txt')
data = StringIO(data.decode('utf-8'))
_compound_tenses_df = pd.read_csv(data, sep='\t') 


def get_verb_form(node : Tree, allowed_upos : Set[str] = None) -> Dict[str,Set]|None:
    if allowed_upos is None: allowed_upos = {'VERB'}
    if node.data['upos'] not in allowed_upos:
        return None
    d = {}
    VerbForm = node.data['feats']['VerbForm']
    id = node.data['id']
    # is this copulative or passive voice?
    cop = Search('/[deprel=aux:pass,cop]').find(node)
    if cop:
        cop = cop[0].node
        if 'Gender' in node.data['feats']:
            d.update({'Gender':node.data['feats']['Gender']})
        if cop.data['deprel'] == 'aux:pass':
            d.update({'Voice':{'Passive'}})
        VerbForm = cop.data['feats']['VerbForm']
        id = cop.data['id']
    # try:
    VerbForm = list(VerbForm)[0]
    # except:
    #     raise Exception('Empty VerbForm: ' + str(node))
    before = [c for c in node.children() if int(c.data['id']) < int(id)]
    aux = [c.data['form'].lower() for c in before]
    aux = [a for a in aux if a in _auxiliaries]
    aux = ' '.join(aux)
    df = _compound_tenses_df
    df = df[(df['VerbForm']==VerbForm) & (df['Auxiliary'] == aux)]
    params = {'Mood', 'Tense', 'Number', 'Person'}
    if not df.empty:
        if df.shape[0] > 1: # more than one row
            print('Warning, more than one match')
            print(df)
        d.update({k:{df.iloc[0][k]} for k in params if pd.notna(df.iloc[0][k])})
        return d
    d.update({k:node.data['feats'][k] for k in params if k in node.data['feats']})
    if VerbForm in ('Inf', 'Ger'):
        d.update({'Mood':{VerbForm}})
    if VerbForm == 'Part':
        mood = 'Supine' if Search('/[upos=ADP]').find(node) else 'Part'
        d.update({'Mood':{mood}})
    return d
