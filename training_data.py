from __future__ import annotations

from collections import defaultdict
from typing import List, Iterator, Dict, Tuple, Callable

import pandas as pd
import pyconll

import annotator
import tree_path
import tree_path.conllu
from tree_path import Tree, Search, Match
from tree_path.conllu import ParsedSentence

doc_id_key = 'newdoc id'
# SENT_ID_KEY = 'sent-id'
# SENT_LEN_KEY = 'sent-len'
# SENT_TEXT_KEY = 'sent-text'


class ParsedDoc(List[ParsedSentence]):
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
                               sent_dist_fn=lambda n : n) -> float:
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

def iter_docs_from_conll(conll_in : str, id_list : List[str] = '') -> Iterator[ParsedDoc]:
    tree_doc : ParsedDoc = ParsedDoc('')
    for sentence in pyconll.iter_from_file(conll_in):
        if sentence.meta_present(doc_id_key):
            previous_doc = tree_doc
            tree_doc = ParsedDoc(sentence.meta_value(doc_id_key))
            if previous_doc and (not id_list or previous_doc.doc_id in id_list):
                yield previous_doc   
        sentence_tree = tree_path.conllu.from_conllu(sentence)
        sentence_tree = ParsedSentence(sentence_tree, sentence.id, sentence.text)
        tree_doc.append(sentence_tree)
    # end loop
    if tree_doc and (not id_list or tree_doc.doc_id in id_list):
        yield tree_doc

from valences import clause_info2

# create record for ellipsis/antecedent pair
# Characteristics of individual clause
clause_heads = ['rel','adv','cauza-efect','coord','expr','inf','loc','raport','SA','sconj','scop','timp',]
deprels = ['ccomp','ccomp:pmod','csubj','advcl']
# compared characteristics
compared = ['same_lemma','syntactic_distance','cata-ana-phoric']

def individual_clause_chars(clause : Tree, suffix:str) -> Dict[str, int]:
    keys = clause_heads+deprels
    char_dict = {k+suffix:0 for k in keys}
    info = clause_info2.get_head_types(clause)
    info += [clause.data['deprel']]
    char_dict.update({k+suffix:1 for k in info if k+suffix in char_dict})
    if clause.data['feats'].get('Mood') == {'Sub'}:
        char_dict['SA'] = 1
    return char_dict

def compared_clause_chars(cl1 : Tree, cl2 : Tree, pdoc : ParsedDoc) -> Dict[str, int]:
    char_dict = {k:0 for k in compared}
    # if cl1.data['lemma'] == cl2.data['lemma']:
    #     char_dict['same_lemma'] = 1
    char_dict['syntactic_distance'] = pdoc.get_syntactic_distance(cl1, cl2)
    char_dict['cata-ana-phoric'] = 1 if pdoc.uid(cl2) < pdoc.uid(cl1) else 0
    return char_dict


def filter_conllu_by_doc(conllu_in : str, conllu_out : str, filter_fn : Callable[[ParsedDoc], bool]):
    conllu_out = open(conllu_out, 'w', encoding='utf8')
    for pdoc in iter_docs_from_conll(conllu_in):
        if filter_fn(pdoc):
            conllu_out.write(pdoc.conllu())
    conllu_out.close()

def generate_clause_pairs(pdoc : ParsedDoc, delta_before=5, delta_after=2) -> Iterator[Tuple[Tree, Tree, int]]:
    " Iterator of ellipsis, antecedent, 1=good/0=bad "
    for m in pdoc.search('.//[misc.Ellipsis=VPE]'):
        if not 'TargetID' in m.node.data['misc']: continue
        for clause_pair in generate_antecedent_candidates(m.node, pdoc, delta_before, delta_after):
            yield clause_pair
        
def generate_antecedent_candidates(ell_node : Tree, pdoc : ParsedDoc, delta_before=5, delta_after=2) ->\
            Iterator[Tuple[Tree, Tree, int]]:
        ell_sent = pdoc.root(ell_node)
        if 'TargetID' in ell_node.data['misc']:
            a_uid = list(ell_node.data['misc']['TargetID'])[0]
            ant_node, ant_sent = pdoc.get_node_by_uid(a_uid)
        else:
            ant_node, ant_sent = None, None
        index0 = pdoc.index(ell_sent) - delta_before
        if index0 < 0: index0 = 0
        index1 = pdoc.index(ell_sent) + delta_after + 1
        if index1 > len(pdoc): index1 = len(pdoc)
        for i in range(index0, index1):
            sentence = pdoc[i]
            for node in sentence.traverse():
                if node == ell_node: continue
                if not Search('.[upos=VERB & !(deprel=aux) ]').find(node): continue
                yield ell_node, node, 1 if node == ant_node else 0

import word_modality.modality

def generate_clause_pair_df(clause_pairs : Iterator[Tuple[Tree, Tree, int]], pdoc : ParsedDoc) -> pd.DataFrame:
    suffixes = ('_e', '_a')
    result_key = 'result'
    data_dict = defaultdict(list)
    for cl_e, cl_a, result in clause_pairs:
        char_e = individual_clause_chars(cl_e, suffixes[0])
        char_a = individual_clause_chars(cl_a, suffixes[1])
        char_common = compared_clause_chars(cl_e, cl_a, pdoc)
        row_dict = {result_key:result, 'e_uid':pdoc.uid(cl_e), 'a_uid':pdoc.uid(cl_a)}
        row_dict.update(char_e)
        row_dict.update(char_a)
        row_dict.update(char_common)
        row_dict.update(word_modality.modality.get_modality_record(cl_e, cl_a))
        for k,v in row_dict.items():
            data_dict[k].append(v)
    return pd.DataFrame.from_dict(data_dict)

