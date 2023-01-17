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
            'spune', 'declara', 'aproba', 'prevedea', 'cugeta', 'răspunde', 'mulțumi',
            'șopti', 'sublinia', 'invita', 'indica', 'descoperi', 'admite', 'urma', 'răcni',
            'repeta', 'explica', 'dezvălui', 'prefera', 'mărturisi', 'avertiza', 'recunoaște',
            'conveni', 'observa', 'îndemna', 'da seamă', 'asigura', }

basic_filter_expr = 'upos=VERB & !deprel=fixed & !misc.Mood=Part'
supine_filter_expr = '!misc.Mood=Supine | (misc.Mood=Supine & deprel=ccomp)'
def basic_filter(node : Tree) -> bool:
    # aspectual gerunds
    if node.data('lemma') in aspectuale and Search('.[misc.Mood=Ger]').find(node):
        return False
    return bool(Search('.[%s & (%s) ]' % (basic_filter_expr, supine_filter_expr)).find(node))

_val = lambda s : list(s)[0]

def quote_introduction_filter(node : Tree) -> bool:
    """False if verb is introducing a quote, otherwise true """
    if _val(node.data('misc.FullLemma')) not in relatare_parataxa:
        return True
    if node.data('deprel') == 'parataxis': return False
    parataxis = Search('/[deprel=parataxis]').find(node)
    if not parataxis: return True
    # is it a line heading, like (e), 3., or a parenthesis?
    parataxis = parataxis[0].node
    if parataxis.data('misc.FullLemma') and _val(parataxis.data('misc.FullLemma')) in relatare_parataxa:
        return True
    proj = parataxis.projection_nodes()
    if proj[0].data('xpos') in ['COLON', 'QUOT', 'DBLQ']:
        return False
    # 1), 1., (e), etc
    if proj[0].data('upos') in ['PUNCT', 'NUM'] and proj[-1].data('xpos') in ('RPAR', 'PERIOD') or \
            proj[0].data('id') == '1' and proj[-1].data('xpos') in ('RPAR', 'PERIOD'):
        return True
    return False

def basic_next_word_filter(node : Tree) -> bool:
    """Check if next word is an infinitive or the particle _să_.
    False if this is the case, True otherwise"""
    proj = node.projection_nodes()
    if proj[-1] is node: return True # can't tell
    next = proj[proj.index(node)+1]
    if next.data('form') == 'să' or \
            Search('.[(upos=VERB & misc.Mood=Inf) | (upos=AUX & feats.VerbForm=Inf)]').find(next) \
            or Search('.[lemma=a upos=PART]').find(next):
        return False
    return True
