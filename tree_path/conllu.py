from __future__ import annotations

from typing import List, Dict

import pyconll
from pyconll.unit.token import Token
from pyconll.unit.sentence import Sentence

from tree_path import Tree, Search, Match
from tree_path.tree import Sequence


def conllu_dict(conllu_token: Token | str, attrib_list: List[str] = None) -> Dict[str, Dict | str]:
    data: Dict[str, Dict | str] = dict()
    if isinstance(conllu_token, str):
        conllu_token = Token(conllu_token)
    if not attrib_list:
        attrib_list = ['deprel', 'deps', 'feats', 'form', 'head', 'id', 'lemma', 'misc', 'upos', 'xpos']
    for attrib in attrib_list:
        data[attrib] = conllu_token.__getattribute__(attrib)
    return data

def from_conllu(sentence: Sentence | str) -> Tree:
    if isinstance(sentence, str):
        sentence = Sentence(sentence)
    data_list = Sequence([conllu_dict(tok) for tok in sentence])
    tree_dict = {d['id']: Tree(d, None, []) for d in data_list}
    root: Tree | None = None
    for id in [d['id'] for d in data_list]:  # just making sure to take ids in order
        tree = tree_dict[id]
        if int(tree.data['head']) == 0:
            tree.parent = None
            root = tree
        else:
            try:
                tree.parent = tree_dict[tree.data['head']]
            except:
                raise Exception('Unknown head id "%s"' % tree.data['head'])
            tree.parent._children.append(tree)
    if root is None:
        raise Exception('No root found.')
    parentless = [t for t in tree_dict.values() if t.parent is None and t is not root]
    if parentless:
        raise Exception('Parentless nodes %s' % str([t.data['id'] for t in parentless]))
    return root


def search_conllu_files(search : str|Search , filenames : List[str]) -> List[Match]:
    matches : List[Match] = []
    if not isinstance(search, Search):
        search = Search(search)
    for filename in filenames:
        for sentence in pyconll.iter_from_file(filename):
            try:
                tree = from_conllu(sentence)
            except Exception as e:
                print(str(e) + ' in ' + (str(sentence.id) if sentence and sentence.id else ''))
                continue
            sentence_matches = search.find(tree)
            for m in sentence_matches:
                m.metadata.update({'filename':filename, 'sent-id':sentence.id, 'text':sentence.text})
            matches += sentence_matches
    return matches

def before(n1 : Tree, n2 : Tree) -> bool:
    return float(n1.data['id']) < float(n2.data['id'])

def get_full_lemma(n : Tree):
    s = Search('/[deprel=fixed]')
    lemma = n.data['lemma']
    ms = s.find(n)
    if ms:
        lemma += (' ' + ' '.join([m.data()['lemma'] for m in ms]))
    return lemma
