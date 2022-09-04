from typing import List

from valences import clause_types

import word_types
from tree_path import Tree, Search
from modalizer import PredExpression, Term, get_modalizer
from tree_path.conllu import get_full_lemma

class PredExprMapper:
    """
    Class obtained from mapping a PredExpression to a verbal node. The result is a list of dicts
    """
    @staticmethod
    def map_tree(expression : PredExpression, node : Tree, modalizer_object : str) -> PredExpression:
        new_expr : List[Term] = []
        mod_obj = Search('/[deprel=%s]' % (modalizer_object)).find(node)
        mod_obj = mod_obj[0].node if mod_obj else None
        for term in expression:
            d = {}
            term = term.copy()
            if term.type() == Term.PREDICATE:
                if Search('/[feats.Polarity=Neg]').find(node):
                    term.args.append('n')
                if term.name() == 'P' and mod_obj:
                    d['lemma'] = get_full_lemma(mod_obj)
            else: # it's an entity
                entity_params = ('Person', 'Number', 'Gender')
                if term.name() in ('x', 'v'): # we don't know what it is
                    d = {}
                elif term.name() in ('subj', 'nsubj'): # look for subj
                    d = word_types.get_verb_form(node)
                    d = {k:v for k,v in d.items() if k in entity_params} if d else {}
                    subj = Search('/[deprel=nsubj]').find(node)
                    if subj:
                        subj = subj[0].node
                        d.update({k:v for k,v in subj.data['feats'].items() if k in entity_params})
                        if subj.data['upos'] == 'NOUN':
                            d['Person'] = {'3'}
                            d['lemma'] = get_full_lemma(subj)
                else: # look for the deprel
                    x = Search('/[deprel=%s]' % (term.name())).find(node)
                    if x:
                        x = x[0].node
                        d = ({k:v for k,v in x.data['feats'].items() if k in entity_params})
                        if x.data['upos'] == 'NOUN':
                            d['Person'] = {'3'}
                            d['lemma'] = get_full_lemma(x)
                    else:
                        d = {}
            term.update(d)
            new_expr.append(term)
        return PredExpression(new_expr)

def tree_to_modal_exprs(node : Tree) -> List[List[PredExpression]]:
    lemma = get_full_lemma(node)
    valence = clause_types.get_valence(node)
    modalizers = get_modalizer(False, lemma, str(valence), '') # no conj. filter later
    possibilities : List[List[PredExpression]] = []
    for m in modalizers:
        object_deprel = m.object
        # see if modalizer conjunction matches
        obj = Search('/[deprel=%s]' % object_deprel).find(node)
        if obj:
            cl_type, cl_conj = clause_types.clause_type(obj[0].node)
            if cl_type == 'conj':
                cl_conj = cl_conj[0]
                if cl_conj in ('că', 'dacă'): cl_conj = 'că'
                elif cl_conj in ('ca', 'să'): cl_conj = 'să'
                else: cl_conj = ''
            if cl_conj and m.conj and cl_conj != m.conj:
                continue
        # now extract expressions
        modal_exprs: List[PredExpression] = []
        for pexp in m.expressions:
            mapping = PredExprMapper.map_tree(pexp, node, object_deprel)
            modal_exprs.append(mapping)
        possibilities.append(modal_exprs)
    return possibilities
