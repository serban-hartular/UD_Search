from typing import List, Dict

import tree_path as tp
import word_modality
from tree_path import ParsedDoc, Search, ParsedSentence, Tree
import clause_info as cli

    

def is_part_of_complex(v : Tree) -> bool:
    return (v.sdata('deprel') in ('csubj', 'ccomp', 'ccomp:pmod') or Search('.[deprel=xcomp upos=VERB]').find(v))\
           and not Search('/[feats.PronType=Rel | /[feats.PronType=Rel deprel=fixed] ]').find(v)

class ComplexPredicate(List[Tree]):
    def __init__(self, node : Tree):
        super().__init__()
        self.extend(ComplexPredicate.grab_complex_ancestors(node))
    def bottom(self) -> Tree:
        return self[-1]
    def top(self) -> Tree:
        return self[0]
    def regents(self) -> List[Tree]:
        return self[:-1]
    def get_polarity(self) -> bool:
        polarity = True
        search = tp.Search('/[lemma=nu]')
        for n in self:
            if search.find(n):
                polarity = not polarity
            mod_rec = word_modality.get_node_modality(n, True)
            if mod_rec and mod_rec[0] and mod_rec[0][0] and len(mod_rec[0][0]) > 2 and mod_rec[0][0][2].startswith('NEG'):
                polarity = not polarity
        return polarity
    def __str__(self):
        return str(["(%s) %s" % (n.sdata('id'), n.sdata('form')) for n in self])
    def __repr__(self):
        return str(self)
    def __hash__(self):
        return hash(tuple(self))
    @staticmethod
    def grab_complex_ancestors(node : Tree) -> List[Tree]:
        queue = [node]
        while node:
            if node.sdata('deprel') == 'conj':
                node = node.parent
            if is_part_of_complex(node):
                queue = [node.parent] + queue
                node = node.parent
            else:
                break
        return queue


def group_statements(sentence : ParsedSentence) -> List[ComplexPredicate]:
    predicates = Search('.//[upos=VERB | (upos=AUX deprel=ccomp,csubj,ccomp:pmod) | /[deprel=cop] ]').find(sentence)
    predicates = [m.node for m in predicates]
    predicates = [ComplexPredicate(n) for n in predicates]
    to_elim = []
    for p in predicates:
        if [q for q in predicates if p.bottom() in q.regents()]: # bottom item appears in other complex pred
            to_elim.append(p)
    predicates = [p for p in predicates if p not in to_elim]
    predicates.sort(key=lambda cp : int(cp.bottom().sdata('id')))
    return predicates

def group_doc_statements(doc : ParsedDoc) -> List[ComplexPredicate]:
    predicates = []
    for sentence in doc:
        predicates.extend(group_statements(sentence))
    return predicates

def complex_pred_relation(first : ComplexPredicate, second : ComplexPredicate) -> str:
    if first.top() == second.top():
        return 'conj'
    if second.top().parent in first:
        return second.top().sdata('deprel')
    if first.top().parent in second:
        return first.top().sdata('deprel')
    return None

            

