from __future__ import annotations

from collections import defaultdict
from typing import List, Tuple

import tree_path as tp
from tree_path import Search, Match, Tree, ParsedSentence, ParsedDoc
from valences import check_valences


class FullLemma:
    def __init__(self, lemma : str, others : List[Search|str], others_rep : List[str] = None):
        self._lemma = lemma
        self.others : List[Search] = [Search(o) if isinstance(o, str) else o for o in others]
        self.others_rep = others_rep
        if not self.others_rep:
            self.others_rep = [str(o) for o in self.others]
    def __hash__(self):
        vals = [str(s) for s in self.others]
        vals.sort()
        vals = (self._lemma,) + tuple(vals)
        return vals.__hash__()
    def __eq__(self, other):
        if not isinstance(other, FullLemma): return False
        return self.__hash__() == other.__hash__()
    def __str__(self):
        return ' '.join([str(s) for s in ([self._lemma] + self.others_rep)])
    def __repr__(self):
        return repr(str(self))
    def matches(self, node : Tree) -> bool:
        if node.data('lemma') != self._lemma: return False
        others = list(self.others)
        while others:
            if not others[-1].find(node): return False
            others.pop()
        return True

def get_verb_lemma(node : Tree) -> FullLemma:
    lemma = node.data('lemma')
    fixed = Search('/[deprel=fixed]').find(node)
    others = [Search('/[deprel=fixed lemma=%s]' % m.node.data('lemma')) for m in fixed]
    others_rep = [m.node.data('lemma') for m in fixed]
    lemma = FullLemma(lemma, others, others_rep)
    return lemma


doc = tp.ParsedDoc.from_json_zip('../rrt-all.3.jz')
verbs = doc.search('.//[upos=VERB]')

aspectuale = ['începe', 'continua', 'termina']
relatare = ['spune', 'zice', 'întreba', 'afirma', 'aminti', 'anunța', 'dezvălui', 'explica', 'observa', 
            'povesti', 'raporta', 'răspunde', 'reieși', 'relata', 'releva', 'ruga', 'șopti',
            'repeta', 'preciza', 'răcni']

for m in verbs:
    verb = m.node
    if verb.data('misc.Mood') == {'Part'}:
        continue
    if verb.data('lemma') in aspectuale and verb.data('misc.Mood') == {'Ger'}:
        continue
    if verb.data('lemma') in relatare and (verb.data('deprel') == 'parataxis' or
            Search('/[deprel=parataxis]').find(verb) ):
        continue
    lemma = get_verb_lemma(verb)
    lemma_str = str(lemma)
    if lemma_str in check_valences.lemma_valence_dict:
        for valence in check_valences.lemma_valence_dict[lemma_str]:
            if valence.matches(verb):
                # Ellipsis, Antecedent, și TargetID
                annot = {'Ellipsis':'VPE'}
                if verb.parent:
                    annot.update({'Antecedent':'Present', 'TargetID':doc.uid(verb.parent)})
                else:
                    annot.update({'Antecedent':'Exoforic'})
                verb.data('misc').update(annot)

doc.to_json_zip('../rrt-all.3.annot.0.jz')
