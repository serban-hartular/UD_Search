from __future__ import annotations

from typing import List, Dict, Iterator, Tuple

import pyconll
from pyconll.unit.sentence import Sentence
from pyconll.unit.token import Token

from tree_path import Tree, Search, Match
from tree_path.tree import Sequence, _sets2lists, _lists2sets


def datum_to_conllu(datum) -> str:
    if not datum:
        return '_'
    if isinstance(datum, str):
        return datum
    if isinstance(datum, dict):
        return '|'.join(k+'='+\
                        ','.join((v,) if isinstance(v, str) else v)
                    for k, v in datum.items())
    raise Exception('Bad datum ' + str(datum))

def conllu_node(node : Tree) -> str:
    attrib_list = ['id', 'form', 'lemma', 'upos', 'xpos', 'feats', 'head', 'deprel', 'deps',  'misc']
    return '\t'.join(datum_to_conllu(node._data[a]) for a in attrib_list)


def from_conllu(sentence: Sentence | str) -> Tree:
    if isinstance(sentence, str):
        sentence = Sentence(sentence)
    data_list = Sequence([conllu_dict(tok) for tok in sentence])
    tree_dict = {d['id']: Tree(d, None, []) for d in data_list}
    root: Tree | None = None
    for id in [d['id'] for d in data_list]:  # just making sure to take ids in order
        tree = tree_dict[id]
        if int(tree._data['head']) == 0:
            tree.parent = None
            root = tree
        else:
            try:
                tree.parent = tree_dict[tree._data['head']]
            except:
                raise Exception('Unknown head id "%s"' % tree._data['head'])
            tree.parent._children.append(tree)
    if root is None:
        raise Exception('No root found.')
    parentless = [t for t in tree_dict.values() if t.parent is None and t is not root]
    if parentless:
        raise Exception('Parentless nodes %s' % str([t._data['id'] for t in parentless]))
    return root


def conllu_dict(conllu_token: Token | str, attrib_list: List[str] = None) -> Dict[str, Dict | str]:
    data: Dict[str, Dict | str] = dict()
    if isinstance(conllu_token, str):
        conllu_token = Token(conllu_token)
    if not attrib_list:
        attrib_list = ['deprel', 'deps', 'feats', 'form', 'head', 'id', 'lemma', 'misc', 'upos', 'xpos']
    for attrib in attrib_list:
        data[attrib] = conllu_token.__getattribute__(attrib)
    return data


class ParsedSentence(Tree):
    def __init__(self, node : Tree, sent_id : str, sent_text : str, meta_data : Dict = None):
        super().__init__(node._data, None, node.children())
        for child in self.children():
            child.parent = self
        self.sent_id = sent_id
        self.sent_text = sent_text
        self.meta_data = meta_data if meta_data else {}
        self.node_list = [n for n in self.traverse()]
        self.node_list.sort(key=lambda n : int(n._data['id']))
        self.node_dict = {n._data['id']:n for n in self.node_list}
    def __str__(self):
        return self.sent_text
    def __repr__(self):
        return "'" + str(self) + "'"
    def to_jsonable(self) -> Dict:
        json_dict = {'sent_id':self.sent_id, 'sent_text':self.sent_text,
                     'meta_data':_sets2lists(self.meta_data)}
        json_dict['node'] = Tree.to_jsonable(self)
        return json_dict
    @staticmethod
    def from_jsonable(json_dict : Dict) -> ParsedSentence:
        sent_id = json_dict['sent_id']
        sent_text = json_dict['sent_text']
        meta_data = _lists2sets(json_dict['meta_data'])
        node = Tree.from_jsonable(json_dict['node'])
        return ParsedSentence(node, sent_id, sent_text, meta_data)
    @staticmethod
    def iter_from_file(filename : str) -> Iterator[ParsedSentence]:
        for s_conllu in pyconll.iter_from_file(filename):
            tree = from_conllu(s_conllu)
            psentence = ParsedSentence(tree, s_conllu.id, s_conllu.text, dict(s_conllu._meta))
            yield psentence
    
    def conllu(self) -> str:
        c = '# sent_id = ' + self.sent_id + '\n'
        c += '# text = ' + self.sent_text + '\n'
        for s in self.node_list:
            c += conllu_node(s) + '\n'
        c += '\n'
        return c
        
    def node(self, key : str|int):
        if isinstance(key, int):
            return self.node_list[key]
        else:
            return self.node_dict[key]
    def uid(self, node : Tree|str):
        if isinstance(node, Tree): node = node._data['id']
        return tok_unique_id(self.sent_id, node)
    @staticmethod
    def get_syntactic_distance(n1 : Tree, n2 : Tree) -> int|None:
        ancestors1 = n1.ancestors() # note, ancestors include self
        ancestors2 = n2.ancestors()
        common = [a for a in ancestors1 if a in ancestors2]
        if not common:
            return None
        common = common[0]
        return ancestors1.index(common) + ancestors2.index(common)


def tok_unique_id(sent_id : str, tok_id : str) -> str:
    return sent_id + '-' + tok_id


def sent_tok_id_from_unique(unique_id : str) -> Tuple:
    if '-' not in unique_id:
        return None, None
    return tuple(unique_id.rsplit('-', 1))


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


def get_full_lemma(n : Tree):
    s = Search('/[deprel=fixed]')
    lemma = n._data['lemma']
    ms = s.find(n)
    if ms:
        lemma += (' ' + ' '.join([m.data()['lemma'] for m in ms]))
    return lemma