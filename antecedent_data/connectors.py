from __future__ import annotations

from typing import List, Dict, Tuple

from antecedent_data.statement_group import ComplexPredicate

import tree_path as tp
from tree_path import ParsedDoc, Search, ParsedSentence, Tree
import clause_info as cli

def get_full_expr(node : Tree):
    if not node: return 'None'
    expr = [node] + [c for c in node.children() if c.sdata('deprel') == 'fixed']
    return ' '.join([n.sdata('form').lower() for n in expr])

def get_connectors(cp : ComplexPredicate) -> List[Tree]:
    node = cp.top()
    children = [c for c in node.children() if tp.before(c, node)]
    children = [c for c in children if c.sdata('deprel') in ('cc', 'mark', 'advmod', 'obl') or \
        Search('./[feats.PronType=Rel]').find(c)]
    return [children[0]] if children else []

def get_syntactic_rels(groups : List[ComplexPredicate]) -> Dict[Tuple[ComplexPredicate, ComplexPredicate], str]:
    d = {}
    for cp1 in groups:
        top = cp1.top()
        while top:
            found = False
            for cp2 in [g for g in groups if g is not cp1]:
                if (cp2, cp1) in d:
                    continue
                if top in cp2:
                    d[(cp1, cp2)] = 'conj' if cp1.top() == cp2.top() else cp1.top().sdata('deprel')
                    found = True
                    break
            if found:
                break
            top = top.parent
    d.update({(k[1],k[0]):v for k,v in d.items()})
    return d