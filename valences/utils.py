from __future__ import annotations

from typing import List

import tree_path as tp
import tree_path.evaluator
from tree_path import ParsedSentence, Tree, Search

def complex_predicate_root(node : Tree) -> Tree:
    while node.parent:
        if node.data('deprel') in ('ccomp', 'ccomp:pmod', 'csubj'):
            node = node.parent
        else: break
    return node

def is_imbrique(node : Tree) -> bool:
    sentence : ParsedSentence = node.root()
    head = complex_predicate_root(node)
    head_proj = head.projection_nodes()
    sentence_proj = sentence.projection_nodes()
    preceding = sentence_proj[sentence_proj.index(head_proj[0])-1]\
        if sentence_proj.index(head_proj[0]) > 0 else None
    succeeding =  sentence_proj[sentence_proj.index(head_proj[-1])+1]\
        if sentence_proj.index(head_proj[-1]) < len(sentence_proj)-1 else None
    beginning_test = head_proj[0] == sentence_proj[0] or head_proj[0].data('upos') == 'PUNCT' or \
                (preceding and preceding.data('upos') == 'PUNCT')
    ending_test = head_proj[-1] == sentence_proj[-1] or head_proj[-1].data('upos') == 'PUNCT' or \
                  (succeeding and succeeding.data('upos') == 'PUNCT')
    return beginning_test and ending_test

def anaphoric_advmod_present(node : Tree) -> (bool, bool):
    """Returns if present, and true if before"""
    node = complex_predicate_root(node)
    advmods = ['după cum', 'așa cum', 'așa', 'cum', 'altfel']
    before = [n for n in node.projection_nodes() if tree_path.evaluator.before(n, node)]
    after = [n for n in node.projection_nodes() if n is not node and n not in before]
    before = ' '.join([n.data('form') for n in before])
    after = ' '.join([n.data('form') for n in after])
    in_before = any([a in before for a in advmods])
    in_after = any([a in after for a in advmods])
    return in_before or in_after, in_before

def real_parent(node : Tree) -> Tree:
    """if a conjunct, returns parent of conjunct"""
    if node.data('deprel') == 'conj' and node.parent:
        return node.parent.parent
    return node.parent


def get_attributive_relpron_source(node : Tree) -> Tree|None:
    # must be care or ce
    if node.sdata('lemma') not in ('care', 'ce'): return None
    # its parent must be an adverbial clause
    if not node.parent or node.parent.sdata('deprel')=='acl': return None
    parent = real_parent(node.parent) # to avoid returning previous conjunct
    return parent

semiadverbe = ['mai', 'și', 'chiar', 'doar', 'numai', 'măcar', 'decât', 'nu', 'cam', 'tot']

def get_nonthematic_subordinates(verb : Tree) -> (List[Tree], List[Tree]):
    """returns nonthematic dependents before and after verb"""
    core_deprels = ['advmod', 'advcl', 'obl', ]
    deprels = list(core_deprels)
    deprels += [d + ':tmod' for d in core_deprels]
    deprels += [d + ':tcl' for d in core_deprels]
    ms_before = Search('<[deprel=%s !lemma=%s]' % (','.join(deprels), ','.join(semiadverbe))).find(verb)
    ms_after = Search('>[deprel=%s]' % ','.join(deprels)).find(verb)
    return [m.node for m in ms_before], [m.node for m in ms_after]
