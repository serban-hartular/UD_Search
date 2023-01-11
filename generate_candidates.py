from collections import defaultdict
from typing import Dict, Tuple, List, Callable

import pyconll

from tree_path import Search, Tree, parsed_doc
from tree_path.conllu import get_full_lemma


def default_get_valence(node : Tree) -> Tuple[str]:
    valence = list()
    for child in node.children():
        if child._data['deprel'] in ['obj', 'ccomp', 'xcomp', 'aux:pass', 'expl:pass', 'expl:pv',
                                'expl:impers', 'ccomp:pmod', 'iobj', 'obl:pmod', 'nmod:pmod', 'csubj']:
            valence.append(str(child._data['deprel']))
    valence.sort()
    return tuple(valence)

def inspect_valences(conllu_in:str, lemmas : List[str],
                     get_valence_fn : Callable[[Tree], Tuple] = default_get_valence) \
        -> Dict[str, Dict[Tuple, int]]:
    val_dict = defaultdict(lambda : defaultdict(int))
    for sentence in pyconll.iter_from_file(conllu_in):
        tree = parsed_doc.from_conllu(sentence)
        for node in tree.traverse():
            if get_full_lemma(node) in lemmas:
                val_dict[get_full_lemma(node)][get_valence_fn(node)] += 1
    return {k:dict(v) for k,v in val_dict.items()}

def generate_candidates(conllu_in: str, conllu_out:str, lemma_valence_dict:Dict[str, List[Tuple]],
                        mark : Tuple[str, str], get_valence_fn : Callable[[Tree], Tuple] = default_get_valence):
    """If valence of node is in dict, add mark[0]=mark[1] to the misc column.
    save to conllu_out"""
    conllu_out = open(conllu_out, 'w', encoding='utf8')
    lemmas_first = [l.split(' ')[0] for l in lemma_valence_dict.keys()]
    search = Search('.//[upos=VERB !(deprel=aux,fixed) _lemma=%s]' % ','.join(lemmas_first))
    for sentence in pyconll.iter_from_file(conllu_in):
        tree = parsed_doc.from_conllu(sentence)
        ms = search.find(tree)
        for m in ms:
            node = m.node
            full_lemma = get_full_lemma(node)
            if full_lemma not in lemma_valence_dict: continue
            valence = get_valence_fn(node)
            if valence not in lemma_valence_dict[full_lemma]: continue
            sentence[node._data['id']].misc[mark[0]] = {mark[1]}
        conllu_out.write(sentence.conll() + '\n\n')
    conllu_out.close()
