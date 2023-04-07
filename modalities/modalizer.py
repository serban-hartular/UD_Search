from __future__ import annotations

from typing import List, Dict

import pandas as pd

import antecedent_detection.labels

df = pd.read_csv('lemma_modalities2.txt', sep='\t')

_aspect = ['INCEPE', 'CONTINUA','TERMINA' ]
_epist = ['CREDE', 'STIE', 'DICE', 'SIMTE']
_deont = ['INTENT', 'PERMIS', 'VREA',  'CAPABIL', 'TREBUIE']
_others = ['APREC', 'FACE' ]

_operator_types = {
    'aspect':_aspect,
    'epist':_epist,
    'deont':_deont,
    'other':_others,
}

class Term(Dict):
    TYPE = 'TYPE'
    NAME = 'NAME'
    ENTITY = 'entity'
    PREDICATE = 'object'
    types = (ENTITY, PREDICATE)
    def __init__(self, type:str, name:str, args:List[str] = None):
        super().__init__({Term.NAME:name, Term.TYPE:type})
        if type not in Term.types:
            raise Exception('Unkown term type %s' % (type))
        self.args = args if args else []
    def name(self):
        return self[Term.NAME]
    def type(self):
        return self[Term.TYPE]
    def polarity(self) -> bool:
        return '-' not in self.args
    def change_polarity(self):
        if '-' in self.args:
            self.args.remove('-')
        else:
            if '+' in self.args: self.args.remove('+')
            self.args.append('-')
    def is_change(self) -> bool:
        return 's' in self.args
    def copy(self) -> Term:
        c = Term(self.type(), self.name(), list(self.args))
        c.update(self)
        return c
    def __str__(self):
        attribs = {k:(v if isinstance(v, str) else '|'.join(v)) for k,v in self.items() if k not in (Term.NAME, Term.TYPE)}
        attribs = self.args + [v for v in attribs.values()]
        # if self.type() == 'entity': return self.name()
        return self.name() + (('(' + ','.join(attribs) + ')') if attribs else '')
    def __repr__(self):
        return str(self)

class PredExpression(List[Term]):
    def __init__(self, l = None):
        super().__init__(l if l else [])
    @staticmethod
    def from_string(pred : str) -> PredExpression:
        preds = pred.split('.')
        pred_dicts : List[Term] = []
        for pred in preds:
            if pred[0].islower():
                pred_dicts.append(Term(Term.ENTITY, pred))
                continue
            pred = pred.split('(')
            name = pred.pop(0)
            if pred:
                pred = pred[0]
                pred = pred.rstrip(')')
                args = pred.split(',')
            else:
                args = []
            pred_dicts.append(Term(Term.PREDICATE, name, args))
        return PredExpression(pred_dicts)
    def __str__(self):
        return '.'.join([str(i) for i in self])
    def __repr__(self):
        return str(self)
    def copy(self) -> PredExpression:
        return PredExpression([term.copy() for term in self])

class Modalizer:
    def __init__(self, lemma:str, conj:str, object:str, valences:List[str], elliptic_valence:str, expressions:List[PredExpression]):
        self.lemma = lemma
        self.conj = conj
        self.object = object
        self.valences = valences
        self.elliptic_valence = elliptic_valence
        self.expressions = expressions
    def __str__(self):
        attrs = ('_lemma', 'conj', 'clause_info', 'elliptic_valence')
        s = ','.join(['%s=%s' % (attr, str(self.__getattribute__(attr))) for attr in attrs])
        s += '\n'
        for expr in self.expressions:
            s += ('\t' + str(expr) + '\n')
        return s
    def __repr__(self):
        return str(self)
    def to_passive(self) -> Modalizer|None:
        if self.object == 'ccomp': return None
        elliptic_valence = self.elliptic_valence
        valences = [elliptic_valence] + self.valences
        valences = [list(eval(v)) for v in valences]
        for v in valences:
            if not 'obj' in v: return None
            v.remove('obj')
            v.append('aux:pass')
            v.sort()
        valences = [str(tuple(v)) for v in valences]
        transitive_to_passive = {'obj':'subj', 'subj':'obl:agent'}
        operators : List[PredExpression] = []
        for oplist in self.expressions:
            new_oplist : List[Term] = []
            for op in oplist:
                if op.type() == Term.ENTITY and op.name() in transitive_to_passive:
                    new_oplist.append(Term(Term.ENTITY, transitive_to_passive[op.name()]))
                else:
                    new_oplist.append(op.copy())
            operators.append(PredExpression(new_oplist))
        return Modalizer(self.lemma, self.conj, self.object, valences[1:], valences[0], PredExpression(operators))
    @staticmethod
    def from_data_row(row):
        preds = [row[i] for i in ('pred1', 'pred2', 'pred3') if row[i] and pd.notna(row[i])]
        preds = [PredExpression.from_string(pred) for pred in preds]
        valences = [s for s in [row['valence1'], row['valence2']] if pd.notna(s) ]
        return Modalizer(row['_lemma'], row['conj'] if pd.notna(row['conj']) else '', row['predicate'], valences, row['elliptic_valence'], preds)
    def to_data_row(self) -> List[str]:
        operators = [str(o) for o in self.expressions]
        operators = operators + ([''] * (3 - len(operators))) # pad up to 3
        return [self.object, self.lemma, self.valences[0], self.valences[1] if len(self.valences) > 1 else '',
                self.elliptic_valence, self.conj, '', ''] + operators

def get_modalizer(elliptic_only : bool, lemma:str, valence:str='', conj:str=''):
    rows = df[df['_lemma'] == lemma]
    if valence:
        if elliptic_only:
            rows = rows[rows['elliptic_valence']==valence]
        else:
            rows = rows[(rows['elliptic_valence']==valence) | (rows['valence1']==valence) | (rows['valence2']==valence)]
    if conj:
        rows = rows[(rows['conj'] == conj) | (pd.isna(rows['conj']))]
    return [Modalizer.from_data_row(row) for row in rows.iloc]



# add passives
_ms = [Modalizer.from_data_row(row) for row in df.iloc]
_passive = [m.to_passive().to_data_row() for m in _ms if m.to_passive()]
df = pd.concat([df, pd.DataFrame(_passive, columns=antecedent_detection.labels.columns)], axis=0, ignore_index=True)