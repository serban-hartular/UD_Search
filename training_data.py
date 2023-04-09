from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterator, Dict, Tuple, Callable, List

import pandas as pd

from tree_path.parsed_doc import ParsedDoc, iter_docs_from_conll
from tree_path import Tree, Search

# SENT_ID_KEY = 'sent-id'
# SENT_LEN_KEY = 'sent-len'
# SENT_TEXT_KEY = 'sent-text'
from tree_path.conllu import get_full_lemma

target_lemmas = ['putea', 'vrea', 'reuși', 'termina', 'trebui', 'dori', 'începe']

from clause_info import clause_info2

# create record for ellipsis/antecedent pair
# Characteristics of individual clause
clause_heads = ['rel','adv','cauza-efect','coord','expr','inf','loc','raport','SA','DACA','sconj','scop','timp',]
deprels = ['ccomp','ccomp:pmod','csubj','advcl']
other_chars = ['CCONTRST', 'polarity']
# compared characteristics
compared = ['SDIST','CATA', 'CCOM', 'QOT']

def individual_clause_chars(clause : Tree, suffix:str) -> Dict[str, int]:
    keys = clause_heads+deprels+other_chars
    char_dict = {k+suffix:0 for k in keys}
    polarity = not clause_info2.is_negative(clause)
    info, conj_contrast, polarity_change = clause_info2.get_head_types(clause)
    if polarity_change: polarity = not polarity
    info += [clause._data['deprel']]
    char_dict.update({k+suffix:1 for k in info if k+suffix in char_dict})
    if clause._data['feats'].get('Mood') == {'Sub'}:
        char_dict['SA'+suffix] = 1
    char_dict.update({'CCONTRST'+suffix:int(conj_contrast), 'polarity'+suffix:int(polarity)})
                     
    return char_dict

def ccom_plus(cle : Tree, other : Tree) -> bool:
    while True:
        if cle == other: return False
        if cle._data['deprel'] in ['ccomp', 'csubj', 'ccomp:pmod']:
            cle = cle.parent
        else:
            break
    return cle in other.ancestors()

def compared_clause_chars(cl1 : Tree, cl2 : Tree, pdoc : ParsedDoc) -> Dict[str, int]:
    char_dict = {k:0 for k in compared}
    char_dict['SDIST'] = pdoc.get_syntactic_distance(cl1, cl2)
    char_dict['SDIST_LN'] = math.log2(pdoc.get_syntactic_distance(cl1, cl2))
    char_dict['DIST'] = abs(pdoc.get_token_distance(cl1, cl2))
    char_dict['DIST_LN'] = math.log2(abs(pdoc.get_token_distance(cl1, cl2)))
    char_dict['CATA'] = 1 if pdoc.get_token_distance(cl1, cl2) > 0 else 0
    char_dict['CCOM'] = 1 if ccom_plus(cl1, cl2) else 0
    char_dict['QOT'] = 1 if cl1._data['misc'].get(ParsedDoc.IN_QUOTE) != \
                            cl2._data['misc'].get(ParsedDoc.IN_QUOTE) \
        else 0
    return char_dict


def filter_conllu_by_doc(conllu_in : str, conllu_out : str, filter_fn : Callable[[ParsedDoc], bool]):
    conllu_out = open(conllu_out, 'w', encoding='utf8')
    for pdoc in iter_docs_from_conll(conllu_in):
        if filter_fn(pdoc):
            conllu_out.write(pdoc.conllu())
    conllu_out.close()

def generate_clause_pairs(pdoc : ParsedDoc, delta_before=5, delta_after=2) -> Iterator[Tuple[Tree, Tree, int]]:
    " Iterator of ellipsis, antecedent, 1=good/0=bad "
    pdoc.mark_in_quote()
    for m in pdoc.search('.//[misc.Ellipsis=VPE & misc.Antecedent=Present,External]'):
        if target_lemmas and get_full_lemma(m.node) not in target_lemmas:
            continue
        if not 'TargetID' in m.node._data['misc']: continue
        for clause_pair in generate_antecedent_candidates(m.node, pdoc, delta_before, delta_after):
            yield clause_pair

def operator_ancestors(node : Tree) -> List[Tree]:
    op_list = []
    parent = node.parent
    while parent:
        if node._data['deprel'] in ['ccomp', 'csubj', 'ccomp:pmod'] and \
                not 'rel' in clause_info2.get_head_types(node)[0]:
            op_list.append(parent)
            node = parent
            parent = parent.parent
        else:
            break
    return op_list
        
def generate_antecedent_candidates(ell_node : Tree, pdoc : ParsedDoc, delta_before=5, delta_after=2) ->\
            Iterator[Tuple[Tree, Tree, int]]:
        ell_sent = pdoc.root(ell_node)
        if 'TargetID' in ell_node._data['misc']:
            a_uid = list(ell_node._data['misc']['TargetID'])[0]
            ant_node = pdoc.get_node_by_uid(a_uid)
        else:
            ant_node = None
        index0 = pdoc.index(ell_sent) - delta_before
        if index0 < 0: index0 = 0
        index1 = pdoc.index(ell_sent) + delta_after + 1
        if index1 > len(pdoc): index1 = len(pdoc)
        for i in range(index0, index1):
            sentence = pdoc[i]
            for node in sentence.traverse():
                if node == ell_node: continue
                if node in operator_ancestors(ell_node): continue
                if not Search(
                    '.[(upos=VERB & !(deprel=aux)) | /[deprel=cop] | (upos=AUX & deprel=ccomp) ' 
                    # + ' | (upos=ADJ & deprel=csubj)  ]'
                    + ']')\
                        .find(node): continue
                yield ell_node, node, 1 if node == ant_node else 0

import word_modality.modality

def generate_clause_pair_df(clause_pairs : Iterator[Tuple[Tree, Tree, int]], pdoc : ParsedDoc) -> pd.DataFrame:
    suffixes = ('_e', '_a')
    result_key = 'result'
    data_dict = defaultdict(list)
    for cl_e, cl_a, result in clause_pairs:
        char_e = individual_clause_chars(cl_e, suffixes[0])
        char_a = individual_clause_chars(cl_a, suffixes[1])
        char_common = compared_clause_chars(cl_e, cl_a, pdoc)
        row_dict = {result_key:result, 'e_uid':pdoc.uid(cl_e), 'a_uid':pdoc.uid(cl_a)}
        row_dict.update(char_e)
        row_dict.update(char_a)
        row_dict.update(char_common)
        row_dict.update(word_modality.modality.get_modality_record(cl_e, cl_a))
        row_dict.update({'POLCNTRST':int(row_dict['polarity_e'] != row_dict['polarity_a'])})
        for k,v in row_dict.items():
            data_dict[k].append(v)
        lengths = [len(v) for v in data_dict.values()]
        lengths = set(lengths)
        if len(lengths) != 1:
            print('Unequal lengths!')
            print(data_dict)
    return pd.DataFrame.from_dict(data_dict)

