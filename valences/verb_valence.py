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

aspectuale = ['începe', 'continua', 'termina']
relatare_parataxa =\
            {'afirma', 'zice', 'autoriza', 'povesti', 'ruga', 'avea grijă', 'afla', 'preciza',
            'solicita', 'scrie', 'reieși', 'stabili', 'informa', 'crede', 'relata', 'începe',
            'întreba', 'releva', 'obliga', 'aminti', 'dori', 'raporta', 'anunța', 'continua',
            'spune', 'declara', 'aproba', 'prevedea', 'cugeta', 'răspunde', 'putea', 'mulțumi',
            'șopti', 'sublinia', 'invita', 'indica', 'descoperi', 'admite', 'urma', 'răcni',
            'repeta', 'explica', 'dezvălui', 'prefera', 'mărturisi', 'avertiza', 'recunoaște',
            'conveni', 'observa', 'îndemna', 'da seamă', 'asigura', }

basic_filter_expr = 'upos=VERB & !deprel=fixed & !misc.Mood=Part'
supine_filter_expr = '!misc.Mood=Supine | (misc.Mood=Supine & deprel=ccomp)'
basic_filter = Search('.[%s & (%s) ]' % (basic_filter_expr, supine_filter_expr))