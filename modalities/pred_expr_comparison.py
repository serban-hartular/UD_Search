from typing import List
import itertools

from modalizer import Term, PredExpression, Modalizer

NO_WAY = -1
NO_SIMILARITY = 0

def term_type(t1 : Term, t2 : Term) -> int:
    return NO_WAY if t1.type() != t2.type() else 0

def compare_lemma(t1 : Term, t2 : Term) -> int:
    return 1 if t1.get('_lemma') and t1.get('_lemma') == t2.get('_lemma') else 0

_mods = ['CREDE', 'CONTINUA', 'INCEPE', 'VREA', 'FACE', 'TERMINA', 'PERMIS', 'SIMTE', 'INTENT', 'APREC', 'TREBUIE', 'CAPABIL', 'DICE', 'STIE']
CLASS2 = {
'DEONT': ['VREA', 'INTENT', 'CAPABIL', 'PERMIS', 'TREBUIE'],
'ASPECT': ['INCEPE', 'CONTINUA', 'TERMINA'],
'EPIST': ['CREDE', 'STIE'],
'INFO' : ['SIMTE', 'DICE'],
}
CLASS3 = {
'ACTIUNE' : CLASS2['DEONT'] + CLASS2['ASPECT'] + ['APREC'],
'STARE' : CLASS2['EPIST'] + CLASS2['INFO'] + CLASS2['ASPECT'] + ['APREC'],
}
def _get_class(name : str, class_dict : dict):
    for k,v in class_dict.items():
        if name in v:
            return k
    return None
    
def compare_modality(t1 : Term, t2 : Term) -> int:
    if compare_lemma(t1, t2): return 5
    if t1.name() == t2.name(): return 4
    if _get_class(t1.name(), CLASS2) and _get_class(t1.name(), CLASS2) == _get_class(t2.name(), CLASS2): return 3
    if _get_class(t1.name(), CLASS3) and _get_class(t1.name(), CLASS3) == _get_class(t2.name(), CLASS3): return 2
    return 0

def compare_entities(t1 : Term, t2 : Term) -> int:
    if compare_lemma(t1, t2): return 5
    params = ('Person', 'Number', 'Gender')
    score = 0
    for p in params:
        v1, v2 = t1.get(p), t2.get(p)
        if v1 and v2:
            v1 = {v1} if isinstance(v1, str) else set(v1)
            v2 = {v1} if isinstance(v2, str) else set(v2)
            if v1.intersection(v2):
                score += 1
            else:
                return 0
    return score

def pred_expr_match_score(expr1 : PredExpression, expr2 : PredExpression) -> (int, int, int):
    short = expr1 if len(expr1) < len(expr2) else expr2
    long = expr2 if short == expr1 else expr1
    max_score, max_i = 0, 0
    for i in range(0, len(long)-len(short)+1):
        score = 0
        for j in range(0, len(short)):
            t1 = long[i+j]
            t2 = short[j]
            if term_type(t1, t2) == NO_WAY:
                continue
            score += (compare_modality(t1, t2) if t1.type() == Term.PREDICATE else compare_entities(t1, t2))
        if score > max_score:
            max_score, max_i = score, i
    if long == expr1:
        return max_score, max_i, 0
    else:
        return max_score, 0, max_i
    
def find_best_combination(expr_list1 : List[PredExpression], expr_list2 : List[PredExpression]) -> (int, tuple, tuple):
    min_len = min(len(expr_list1), len(expr_list2))
    permutations1 = itertools.permutations(expr_list1, min_len)
    permutations2 = itertools.permutations(expr_list2, min_len)
    combos = itertools.product(permutations1, permutations2)
    best = 0, None, None
    for (combo1, combo2) in combos:
        score = 0
        for e1, e2 in zip(combo1, combo2):
            score += pred_expr_match_score(e1, e2)[0]
        if score > best[0]:
            best = score, combo1, combo2
    return best
