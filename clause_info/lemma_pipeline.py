from collections import defaultdict
from typing import Tuple, Dict, List

import pyconll

from tree_path import Search, Tree, parsed_doc


class Deprel: # = namedtuple('Deprel', ['name', 'head'])
    def __init__(self, name : str, head : str = ''):
        self.name = name
        self.head = head
    def to_tuple(self):
        return (self.name, self.head)
    def __str__(self):
        return str(self.to_tuple())
    def __repr__(self):
        return str(self)
    
def get_valence(node : Tree, to_include : List[str] = None) -> Tuple[str]:
    if not to_include:
        to_include = ['obj', 'ccomp', 'xcomp', 'aux:pass', 'expl:pass', 'expl:pv',
                    'expl:impers', 'ccomp:pmod', 'iobj', 'obl:pmod', 'nmod:pmod', 'csubj', 'aux:pass']
    valence = {child._data['deprel'] for child in node.children() if child._data['deprel'] in to_include}
    if node.parent and node.parent._data['_lemma'] == 'putea' and node._data['feats'].get('VerbForm') and \
            'Inf' in node._data['feats'].get('VerbForm'): # 'putea' modal
        to_include = [v for v in to_include if v != node._data['deprel']]
        parent_valence = {child._data['deprel'] for child in node.parent.children() if child._data['deprel'] in to_include}
        valence = valence.union(parent_valence)
    valence = [str(v) for v in valence]
    valence.sort()
    return tuple(valence)


def get_full_lemma(node : Tree) -> str:
    return ' '.join([node._data['_lemma']] + [c._data['_lemma'] for c in node.children() if c._data['deprel'] in ('flat', 'fixed')])

def extract_lemma_valences(conllu_filename : str, lemmas : List[str], upos : str = None) -> Dict[str, Dict[Tuple[str], int]]:
    valence_count : Dict[str, Dict[Tuple[str], int]] = defaultdict(lambda : defaultdict(int))
    lemma_first_words = [l.split(' ')[0] for l in lemmas]
    search = './/[_lemma=%s' % ','.join(lemma_first_words)
    if upos: search += (' upos=' + upos)
    search += ']'
    search = Search(search)
    for sentence in pyconll.iter_from_file(conllu_filename):
        try: tree = parsed_doc.from_conllu(sentence)
        except: continue
        matches = search.find(tree)
        for m in matches:
            lemma = get_full_lemma(m.node)
            if lemma not in lemmas: continue
            valence = get_valence(m.node)
            valence_count[lemma][valence] += 1
    valence_count = {k:dict(v) for k,v in valence_count.items()} # convert to simple dict
    return valence_count

def get_sentence_ids(conllu_filename : str, lemma : str, valences : List[Tuple[str]], upos : str = '') -> List[str]:
    search = Search('.//[_lemma=%s %s]' % (lemma.split(' ')[0], '' if not upos else ('upos='+upos)))
    id_list = []
    for sentence in pyconll.iter_from_file(conllu_filename):
        try: tree = parsed_doc.from_conllu(sentence)
        except: continue
        matches = search.find(tree)
        for m in matches:
            if not get_full_lemma(m.node) == lemma: continue
            if get_valence(m.node) not in valences: continue
            id_list.append(sentence.id)
            break
    return id_list

def generate_elliptic_valences(valence_dict : Dict[str, Dict[Tuple[str], int]], to_remove = 'ccomp') -> Dict[str, List[Tuple[str]]]:
    elliptic_valences : Dict[str, List[Tuple[str]]] = defaultdict(list)
    for lemma, valences in valence_dict.items():
        for valence in valences:
            if to_remove in valence:
                valence = list(valence)
                valence.remove(to_remove)
                elliptic_valences[lemma].append(tuple(valence))
    return dict(elliptic_valences)

if __name__ == 'main':
    filename = '../cancan2.1.3-train.conllu'
    valence_count = extract_lemma_valences(filename, ['putea'])
    # (), ('iobj',)