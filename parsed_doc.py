from __future__ import annotations

from collections import defaultdict
from typing import List, Dict, Iterator

import pyconll

import tree_path
from tree_path import Tree, Search, Match, ParsedSentence
from tree_path.conllu import from_conllu

doc_id_key = 'newdoc id'

class ParsedDoc(List[ParsedSentence]):
    IN_QUOTE='InQuote'
    sentence_distance_fn = lambda n : n
    def __init__(self, doc_id : str):
        super().__init__()
        self.doc_id = doc_id
        self.id_dict : Dict[str, ParsedSentence] = None
    def conllu(self) -> str:
        c = '# newdoc id = ' + self.doc_id + '\n'
        for s in self:
            c += s.conllu()
        c += '\n'
        return c
    def make_id_dict(self):
        self.id_dict = {t.sent_id : t for t in self }      #(t,i) for t,i in zip(self, range(len(self)))}
    def sentence(self, sent_id : str):
        if self.id_dict is None: self.make_id_dict()
        return self.id_dict.get(sent_id)
    def root(self, n : Tree) -> ParsedSentence | None:
        n = n.root()
        if n in self:
            return n
        return None
        
    def search(self, expr : str) -> List[Match]:
        search = Search(expr)
        matches = []
        for s in self:
            matches += search.find(s)
        return matches
    def uid(self, node:Tree) -> str:
        s = node.root()
        if s not in self: return None
        return s.uid(node)
    def get_node_by_uid(self, uid : str) -> (Tree, ParsedSentence):
        """Get node by its unique id. Also return sentence root"""
        (sent_id, node_id) = tree_path.conllu.sent_tok_id_from_unique(uid)
        root = self.sentence(sent_id)
        if not root: return (None, None)
        node = root.search(lambda n : n.data['id'] == node_id)
        node = node[0] if node else None
        return node, root
    
    def get_sentence_distance(self, sent_id_1 : str, sent_id_2 : str) -> int|None:
        if self.id_dict is None: self.make_id_dict()
        if sent_id_1 not in self.id_dict or sent_id_2 not in self.id_dict: return None
        return self.index(self.id_dict[sent_id_2]) -\
               self.index(self.id_dict[sent_id_1])
    
    def get_syntactic_distance(self, node_uid_1:str|Tree, node_uid_2:str|Tree,
                               sent_dist_fn=None) -> float:
        if sent_dist_fn is None:
            sent_dist_fn = ParsedDoc.sentence_distance_fn
        if isinstance(node_uid_1, Tree):
            n1, t1 = node_uid_1, node_uid_1.root()
        else:
            n1, t1 = self.get_node_by_uid(node_uid_1)
        if isinstance(node_uid_2, Tree):
            n2, t2 = node_uid_2, node_uid_2.root()
        else:
            n2, t2 = self.get_node_by_uid(node_uid_2)
        if not all([n1, t1, n2, t2]): return None
        if t1 == t2:
            return t1.get_syntactic_distance(n1, n2)
        else:
            return n1.depth() + \
                   abs(sent_dist_fn(self.get_sentence_distance(t1.sent_id, t2.sent_id))) + \
                    n2.depth()
    def get_token_distance(self, node_uid_1:str|Tree, node_uid_2:str|Tree) -> int:
        s1 : ParsedSentence
        s2 : ParsedSentence
        if isinstance(node_uid_1, Tree):
            n1, s1 = node_uid_1, node_uid_1.root()
        else:
            n1, s1 = self.get_node_by_uid(node_uid_1)
        if isinstance(node_uid_2, Tree):
            n2, s2 = node_uid_2, node_uid_2.root()
        else:
            n2, s2 = self.get_node_by_uid(node_uid_2)
        if not all([n1, s1, n2, s2]): return None
        if s1 == s2 and n1 == n2: return 0
        s1_index = self.index(s1)
        s2_index = self.index(s2)
        n1_index = s1.node_list.index(n1)
        n2_index = s2.node_list.index(n2)
        if s1_index == s2_index:
            return n2_index - n1_index
        dir = 1 if s2_index > s1_index else -1
        if dir == 1:
            d1 = len(s1.node_list) - n1_index - 1
            d2 = n2_index
            between_range = range(s1_index+1, s2_index)
        else:
            d2 = len(s2.node_list) - n2_index - 1
            d1 = n1_index
            between_range = range(s2_index+1, s1_index)
        d_between = sum([len(self[i].node_list) for i in between_range])
        return dir * (d1 + d_between + d2)
    def token_iter(self) -> Iterator[Tree]:
        for sentence in self:
            for token in sentence.node_list:
                yield token
    def mark_in_quote(self, key=IN_QUOTE):
        quote_flag = False
        for token in self.token_iter():
            if token.data['xpos'] == 'DBLQ':
                quote_flag = not quote_flag
            elif quote_flag:
                token.data['misc'][key] = {'Yes'}
    
                


def iter_docs_from_conll(conll_in : str, id_list : List[str] = '') -> Iterator[ParsedDoc]:
    tree_doc : ParsedDoc = ParsedDoc('')
    for sentence in pyconll.iter_from_file(conll_in):
        if sentence.meta_present(doc_id_key):
            previous_doc = tree_doc
            tree_doc = ParsedDoc(sentence.meta_value(doc_id_key))
            if previous_doc and (not id_list or previous_doc.doc_id in id_list):
                yield previous_doc   
        sentence_tree = from_conllu(sentence)
        sentence_tree = ParsedSentence(sentence_tree, sentence.id, sentence.text)
        tree_doc.append(sentence_tree)
    # end loop
    if tree_doc and (not id_list or tree_doc.doc_id in id_list):
        yield tree_doc


def display_uids_from_file(conllu_in: str, uid_dict : Dict[str, str]) -> List[str]:
    sent_tok_ids = defaultdict(dict)
    for uid, annot in uid_dict.items():
        sent_id, tok_id = tree_path.conllu.sent_tok_id_from_unique(uid)
        sent_tok_ids[sent_id][tok_id] = annot
    str_list = []
    for sentence in pyconll.iter_from_file(conllu_in):
        if sentence.id not in sent_tok_ids: continue
        sent_str = ''
        for token in sentence:
            sent_str += token.form
            if token.id in sent_tok_ids[sentence.id]:
                sent_str += sent_tok_ids[sentence.id][token.id]
            sent_str += ' '
        str_list.append(sent_str)
        sent_tok_ids.pop(sentence.id)
        if not sent_tok_ids:
            break
    return str_list
