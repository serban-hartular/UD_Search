from __future__ import annotations

from typing import Tuple

from pyconll.unit.sentence import Sentence

import conllu_utils
import tree_path
from tree_path import Tree, Search
import pyconll


from tree_path.conllu import get_full_lemma, before
import word_types.ro_verb_forms as vb_forms


def is_verb(node : Tree) -> bool:
    return node.data['upos'] == 'VERB' or Search('/[deprel=cop]').find(node)

def get_previous_conjunct(node : Tree) -> Tree|None:
    if node.data['deprel'] != 'conj': return None
    parent = node.parent
    conjs = Search('/[deprel=conj]').find(parent)
    conjs = [m.node for m in conjs]
    index = conjs.index(node)
    return parent if index == 0 else conjs[index-1]

def no_diacritics(tree : Tree) -> bool:
    for node in tree.root().traverse():
        if set('ăîâșțĂÎÂȘȚ').intersection(set(node.data['form'])):
            return False
    return True

def is_relative(node : Tree) -> str|None:
    indef_rel_prons = ['oricine', 'orice', 'oricând', 'oriunde', 'oricum', 'oricand']
    rel = Search('/[feats.PronType=Rel | lemma=%s | /[lemma=cum,%s] ]' % (','.join(indef_rel_prons),','.join(indef_rel_prons)))
    rel = rel.find(node)
    if rel:
        rel = [get_full_lemma(r.node) for r in rel if before(r.node, node)]
        if rel:
            return rel[0]
    # search for first subordinate that has 'cât' as a subordinate
    if node.children() and before(node.children()[0], node):
        first = node.children()[0]
        if Search('/[lemma=cât]').find(first):
            head = ' '.join([n['lemma'] for n in first.projection()])
            return head
    return None

def is_coord_conjunct(node : Tree) -> str|None:
    if node.data['deprel'] != 'conj':
        return None
    coord = Search('/[deprel=cc]').find(node)
    return get_full_lemma(coord[0].node) if coord else '{}' 
    
def is_comparative(node : Tree) -> str|None:
    comp = Search('/[lemma=decât]').find(node)
    if comp and before(comp[0].node, node):
        return get_full_lemma(comp[0].node)
    return None
    
def is_cause_effect(node : Tree) -> str|None:
    cause_effect_markers = ['dacă', 'pentru că', 'deși', 'dat fiind că', 'fără', 'că']
    if node.data['deprel'] == 'ccomp': return None
    mark = Search('/[deprel=mark]').find(node)
    if not mark:
        return None
    mark = get_full_lemma(mark[0].node)
    if mark in cause_effect_markers:
        return mark
    return None

def get_annotated_antecedent(ellipsis : Tree) -> Tuple[Tree|None, Tree|None]:
    antecedent_id = ellipsis.data['misc'].get('Antecedent')
    antecedent_regent_id = ellipsis.data['misc'].get('AntecedentLicenser')
    if not antecedent_id and not antecedent_regent_id:
        return (None, None)
    tree = ellipsis.root()
    if antecedent_id:
        antecedent_id = antecedent_id.pop()
        antecedent = tree.search(lambda n: n.data['id'] == antecedent_id)[0]
    else:
        antecedent = None
    if antecedent_regent_id:
        antecedent_regent_id = antecedent_regent_id.pop()
        antecedent_regent = tree.search(lambda n: n.data['id'] == antecedent_regent_id)[0]
    else:
        antecedent_regent = None
    if not antecedent_regent and antecedent.data['deprel'] in \
            ('ccomp', 'ccomp:pmod', 'xcomp', 'csubj', 'csubj:pass', 'nmod'):
        antecedent_regent = antecedent.parent
    return antecedent, antecedent_regent

def find_treepath(n1 : Tree, n2 : Tree):
    # find common ancestor
    ancestors1 = n1.ancestors()
    ancestors2 = n2.ancestors()
    progenitor = None
    for n in ancestors1:
        if n in ancestors2:
            progenitor = n
            break
    if not progenitor: return (None, None)
    ancestors = [a[:a.index(progenitor)+1] for a in (ancestors1, ancestors2)]
    # ellipsis_ancestors = ellipsis_ancestors[:ellipsis_ancestors.index(progenitor)+1]
    # antecedent_ancestors = antecedent_ancestors[:antecedent_ancestors.index(progenitor) + 1]
    return tuple(ancestors)

def is_paranthetic(node : Tree) -> bool:
    if len(node.children()) < 2: return False
    first = node.children()[0]
    last = node.children()[-1]
    return (first.data['form'] == '(' and last.data['form'] == ')') or \
        (first.data['form'] == '-' and last.data['form'] == '-')

def is_mis_parse(node : Tree) -> str:
    tokens = node.root().projection()
    index = tokens.id_index(node.data['id'])
    if index == len(tokens)-1: return ''
    next = tokens[index+1]
    if next['lemma'] in ('să','că') or next['feats'].get('VerbForm') == {'Inf'}:
        return next['id']
    nsubj = Search('./[deprel=nsubj]').find(node)
    if nsubj:
        nsubj = nsubj[0].node
        if nsubj.data['lemma'] in ('ce', 'ceva'):
            return nsubj.data['id']
        verb_info = vb_forms.get_verb_form(node, {'VERB'})
        if verb_info.get('Person') and verb_info.get('Person').intersection({'1','2'}) and \
                ('Person' not in nsubj.data['feats'] or not \
                        verb_info.get('Person').intersection(nsubj.data['feats']['Person'])):
            #disagreement
            return nsubj.data['id']
    return ''

def is_expression(node : Tree) -> str|None:
    tokens = node.projection()
    index = tokens.id_index(node.data['id'])
    if index >= 2:
        seq = tokens[index-2:index+1]
        seq = ' '.join([t['lemma'] for t in seq])
        if seq == 'nu mai putea':
            return seq
    if index >= 3:
        seq = tokens[index-3:index+1]
        seq = ' '.join([t['form'].lower() for t in seq])
        if seq in ('fără doar și poate', 'fara doar si poate'):
            return seq
    return None

def is_rnr(node : Tree) -> Tree|None:
    rnr = Search('/[deprel=conj /[deprel=cc]]/[deprel=ccomp]').find(node)
    if rnr:
        return rnr[0].next_nodes[0].node
    return None

