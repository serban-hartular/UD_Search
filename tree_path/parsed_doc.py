from __future__ import annotations

import gzip
import json
from collections import defaultdict
from typing import List, Dict, Iterator, Set

import pyconll

import tree_path
from tree_path import Tree, Search, Match, ParsedSentence
from tree_path.conllu import from_conllu

_doc_id_key = 'newdoc id'

class ParsedDoc(List[ParsedSentence]):
    IN_QUOTE='InQuote'
    sentence_distance_fn = lambda n : n
    def __init__(self, doc_id : str, meta_data : Dict[str, str] = None):
        super().__init__()
        self.doc_id = doc_id
        self.id_dict : Dict[str, ParsedSentence] = None
        self.meta_data = meta_data if meta_data else {}
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
        
    def search(self, expr : str) -> Iterator[Match]:
        search = Search(expr)
        # matches = []
        for s in self:
            matches = search.find(s)
            while matches:
                yield matches[0]
                matches.pop(0)
    
    def uid(self, node:Tree) -> str:
        s = node.root()
        if s not in self: return None
        return s.uid(node)
    def get_node_by_uid(self, uid : str) -> (Tree|None, ParsedSentence|None):
        """Get node by its unique id. Also return sentence root"""
        (sent_id, node_id) = tree_path.conllu.sent_tok_id_from_unique(uid)
        if sent_id is None: return None, None
        root = self.sentence(sent_id)
        if not root: return (None, None)
        node = root.search(lambda n : n._data['id'] == node_id)
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
            if token._data['xpos'] == 'DBLQ':
                quote_flag = not quote_flag
            elif quote_flag:
                token._data['misc'][key] = {'Yes'}
    def to_jsonable(self):
        json_dict = {'doc_id': self.doc_id, 'meta_data': self.meta_data,
                     'sentences': [s.to_jsonable() for s in self]}
        return json_dict
    def to_json_zip(self, filename : str = '') -> bytes|None:
        encoded = json.dumps(self.to_jsonable()).encode('utf-8')
        data = gzip.compress(encoded)
        if not filename:
            return data
        with open(filename, 'wb') as handle:
            handle.write(data)
            
    @staticmethod
    def from_jsonable(json_dict : Dict, make_dict_id : bool = True) -> ParsedDoc:
        doc_id = json_dict['doc_id']
        meta_data = json_dict['meta_data']
        doc = ParsedDoc(doc_id, meta_data)
        for json_sentence in json_dict['sentences']:
            doc.append(ParsedSentence.from_jsonable(json_sentence))
        if make_dict_id:
            doc.make_id_dict()
        return doc
    @staticmethod
    def from_json_zip(src : bytes|str, make_dict_id : bool = True) -> ParsedDoc:
        if isinstance(src, str): # it's a filename
            with open(src, 'rb') as handle:
                src = handle.read()
        decomp = gzip.decompress(src)
        decoded = decomp.decode('utf-8')
        doc = ParsedDoc.from_jsonable(json.loads(decoded))
        if make_dict_id:
            doc.make_id_dict()
        return doc
    def extract_tokens_for_annotation(self, key_list : List[str]) -> Dict:
        json_dict = {'doc_id': self.doc_id, 'meta_data':self.meta_data, 'tokens':[]}
        for node in self.token_iter():
            data = {k:node._data[k] for k in node._data if k in key_list}
            data['id'] = self.uid(node)
            json_dict['tokens'].append(data)
        return json_dict

def iter_docs_from_conll(conll_in : str, doc_id_key : str = _doc_id_key, id_list : List[str] = '') -> Iterator[ParsedDoc]:
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
        tree_doc.make_id_dict()
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


def _datum_to_str(datum : str|Set) -> str:
    if not datum: return ''
    return datum if isinstance(datum, str) else ','.join(datum)

doc_id_str = 'newdoc id'
token_key_str = 'tokens'
node_id_key = 'id'


def sentence_to_annotation_sequence(sentence : ParsedSentence, keys_aliases : Dict,
                                    doc : ParsedDoc = None) -> List[Dict[str, str]]:
    """key_aliases = {'lemma':'lemma', 'misc.Ellipsis':'Ellipsis', etc}"""
    projection = sentence.projection_nodes()
    dict_list = []
    for node in projection:
        d = {alias : _datum_to_str(node.data(key)) for key,alias in keys_aliases.items()
                if _datum_to_str(node.data(key)) }
        if doc:
            d[node_id_key] = doc.uid(node)
        dict_list.append(d)
    return dict_list

def doc_to_annotation_sequence(doc : ParsedDoc, keys_aliases : Dict, sentence_search : str|Search|None = None) \
        -> Dict[str, str|List[Dict[str, str]]]:
    if sentence_search and isinstance(sentence_search, str):
        sentence_search = Search(sentence_search)
    dict_list = []
    for sentence in doc:
        if sentence_search and not sentence_search.find(sentence):
            continue
        s_toks = sentence_to_annotation_sequence(sentence, keys_aliases, doc)
        dict_list.extend(s_toks)
    return {doc_id_str:doc.doc_id, token_key_str:dict_list}

def apply_annotations_to_doc(annots : List[Dict[str, str|Set]], doc : ParsedDoc, key_aliases : Dict,
                             remove_absent_keys : bool = True):
    """if remove_absent_keys, keys don't appear in the annotation will be removed from node data"""
    # sanity check
    if not isinstance(annots, List) or not isinstance(annots[0], Dict):
        raise Exception('Bad format annotations')
    if len(list(key_aliases.values())) != len(set(key_aliases.values())):
        raise Exception('Keys and aliases must be unique!')
    if node_id_key in key_aliases.values() or node_id_key in key_aliases.keys():
        raise Exception('Trying to delete node id: ' + str(key_aliases))
    for annot in annots:
        uid = annot[node_id_key]
        node, _ = doc.get_node_by_uid(uid)
        if node is None: raise 'Could not find node with uid ' + uid
        aliases_keys = {v:k for k,v in key_aliases.items()}
        update_dict = {k:v for k,v in annot.items() if k in aliases_keys.keys()} # filter
        for local_key, alias in key_aliases.items():
            if alias in annot:
                node.assign(local_key, annot[alias])
            elif remove_absent_keys:
                node.remove(local_key)

def annot_dict_to_list(annot_dict : Dict, make_sets : List[str]):
    # sanity check
    if not isinstance(annot_dict.get(token_key_str), List):
        raise Exception("annotation dict does not contain list at " + token_key_str)
    annots : List[Dict]= list(annot_dict[token_key_str])
    # not pythonic
    for annot in annots:
        for k in annot.keys():
            if k in make_sets and isinstance(annot[k], str):
                annot[k] = {annot[k]}
    
    return annots

def overwrite_sentences(orig_doc : ParsedDoc, overwrite_src : ParsedDoc) -> ParsedDoc:
    """Overwrites all sentences in overwrite_src that it finds (by sent_id) in orig_doc"""
    overwrite_src.make_id_dict()
    new_sent_list : List[ParsedSentence] = []
    for sentence in orig_doc:
        if sentence.sent_id not in overwrite_src.id_dict:
            new_sent_list.append(sentence)
        else:
            new_sent_list.append(overwrite_src.sentence(sentence.sent_id))
    new_doc = ParsedDoc(orig_doc.doc_id, dict(orig_doc.meta_data))
    new_doc.extend(new_sent_list)
    new_doc.make_id_dict()
    return new_doc

def doc_to_annotation_table(doc : ParsedDoc, doc_search : str|Search, labels : List[str] = None) -> List[Dict[str, str]]:
    """Not tested yet"""
    if not labels:
        labels = ['misc.Ellipsis', 'misc.Antecedent', 'misc.Info', 'misc.TargetID']
    default_labels_before = ['UID', 'Licenser', 'Lemma']
    default_labels_after = ['TargetForm', 'TargetDeprel', 'Text']
    table = []
    nodes = [m.node for m in doc.search(doc_search)]
    for node in nodes:
        # labels before
        uid = doc.uid(node)
        licenser = node.sdata('form')
        lemma = node.sdata('misc.FullLemma')
        d = {k:v for k,v in zip(default_labels_before, [uid, licenser, lemma])}
        # labels from data
        d.update({k:node.sdata(k) for k in labels})
        # labels after
        targetform, targetdeprel = '',''
        if 'misc.TargetID' in labels:
            target, _ = doc.get_node_by_uid(node.sdata('misc.TargetID'))
            if target:
                targetform = target.sdata('form')
                targetdeprel = target.sdata('deprel')
        text = str(node.root())
        d.update({k:v for k,v in zip(default_labels_after, [targetform, targetdeprel, text])})
        table.append(d)
    return table

def apply_annotation_table(doc : ParsedDoc, annot_table : List[Dict[str, str]], labels : List[str] = None):
    if not labels:
        labels = ['misc.Ellipsis', 'misc.Antecedent', 'misc.Info', 'misc.TargetID']
    for d in annot_table:
        uid = d['UID']
        node, _ = doc.get_node_by_uid(uid)
        for k in labels:  # first remove
            node.remove(k) 
        for k in labels: # now add values
            if d.get(k):
                node.assign(k, {d[k]}) # needs to be a set

    