from __future__ import annotations

import gzip
import json
from collections import defaultdict
from typing import List, Dict, Iterator, Set

import pyconll

import tree_path
from tree_path import Tree, Search, Match, ParsedSentence
from tree_path.conllu import from_conllu



class ParsedDoc(List[ParsedSentence]):
    IN_QUOTE='InQuote'
    sentence_distance_fn = lambda n : n
    def __init__(self, doc_id : str, meta_data : Dict[str, str] = None):
        super().__init__()
        self.doc_id = doc_id
        self.id_dict : Dict[str, ParsedSentence] = None
        self.meta_data = meta_data if meta_data else {}
    def conllu(self, doc_id_key : str = '') -> str:
        """If not doc_id_key, no newdoc id will be entered"""
        c = '' if not doc_id_key else ('# newdoc id = ' + self.doc_id + '\n')
        for k,v in self.meta_data.items():
            meta_line = '# %s = %s\n' % (k, v) if v else '# %s\n' % k
            c += meta_line
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
    
    def uid(self, node:Tree) -> str|None:
        s : ParsedSentence = node.root()
        if s not in self: return None
        txt = s.uid(node)
        if self.doc_id:
            txt = self.doc_id + '-' + txt
        return txt
    def get_node_by_uid(self, uid : str) -> Tree|None: #, ParsedSentence|None):
        """Get node by its unique id. Also return sentence root"""
        # (sent_id, node_id) = tree_path.conllu.sent_tok_id_from_unique(uid)
        
        # new method
        if self.doc_id and uid.startswith(self.doc_id + '-'):
            uid = uid[len(self.doc_id + '-'):] # slice off doc id
        (sent_id, node_id) = uid.rsplit('-', 1)
        # end new method
        if sent_id is None: return None, None
        root = self.sentence(sent_id)
        if not root: return (None, None)
        node = root.search(lambda n : n._data['id'] == node_id)
        node = node[0] if node else None
        return node   #, root
    
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
            n1 = self.get_node_by_uid(node_uid_1)
            t1 = n1.root()
        if isinstance(node_uid_2, Tree):
            n2, t2 = node_uid_2, node_uid_2.root()
        else:
            n2 = self.get_node_by_uid(node_uid_2)
            t2 = n2.root()
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
            n1 = self.get_node_by_uid(node_uid_1)
            s1 = n1.root()
        if isinstance(node_uid_2, Tree):
            n2, s2 = node_uid_2, node_uid_2.root()
        else:
            n2 = self.get_node_by_uid(node_uid_2)
            s2 = n2.root()
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

def iter_docs_from_conll(conll_in : str, doc_id_key : str, id_list : List[str] = '') -> Iterator[ParsedDoc]:
    tree_doc : ParsedDoc = ParsedDoc('')
    for sentence in pyconll.iter_from_file(conll_in):
        if sentence.meta_present(doc_id_key):
            previous_doc = tree_doc
            tree_doc = ParsedDoc(sentence.meta_value(doc_id_key))
            meta_keys_skip = ('newdoc id', 'sent_id', 'text') 
            tree_doc.meta_data = {k:v for k,v in sentence._meta.items() if k not in meta_keys_skip} # add meta data
            if previous_doc and (not id_list or previous_doc.doc_id in id_list):
                yield previous_doc   
        sentence_tree = from_conllu(sentence)
        sentence_tree = ParsedSentence(sentence_tree, sentence.id, sentence.text)
        tree_doc.append(sentence_tree)
    # end loop
    if tree_doc and (not id_list or tree_doc.doc_id in id_list):
        tree_doc.make_id_dict()
        yield tree_doc

class DocList(List[ParsedDoc]):
    DOC_ID_KEY = 'newdoc id'
    def __init__(self, doc_list : List[ParsedDoc]):
        super().__init__(doc_list)
        self.doc_dict = {}
        self.make_doc_dict()
    def make_doc_dict(self):
        self.doc_dict = {doc.doc_id:doc for doc in self}
    def get_doc(self, uid:str) -> ParsedDoc:
        uid = uid.split('-')
        for i in range(1, len(uid)):
            doc_id = '-'.join(uid[0:i])
            if doc_id in self.doc_dict:
                return self.doc_dict[doc_id]
        return None
    def get_node_by_uid(self, uid:str) -> Tree|None:        
        doc = self.get_doc(uid)
        # if len(doc) != 1: raise Exception('Found %d docs named %s' % (len(doc), doc_id))
        # doc = doc[0]
        return doc.get_node_by_uid(uid)
        
    def to_conllu_file(self, outfile : str, doc_id_key = DOC_ID_KEY):
        with open(outfile, 'w', encoding='utf-8') as handle:
            for doc in self:
                handle.write(doc.conllu(doc_id_key) + '\n')
    @staticmethod
    def from_conllu(filename, doc_id_key : str = None):
        if doc_id_key is None:
            doc_id_key = DocList.DOC_ID_KEY
        return DocList([d for d in iter_docs_from_conll(filename, doc_id_key)])
    def to_json_zip(self, filename : str):
        encoded = json.dumps([d.to_jsonable() for d in self])\
            .encode('utf-8')
        data = gzip.compress(encoded)
        if not filename:
            return data
        with open(filename, 'wb') as handle:
            handle.write(data)
    @staticmethod
    def from_json_zip(src : bytes|str, make_dict_id : bool = True) -> DocList:
        if isinstance(src, str): # it's a filename
            with open(src, 'rb') as handle:
                src = handle.read()
        decomp = gzip.decompress(src)
        decoded = decomp.decode('utf-8')
        json_list = json.loads(decoded) #ParsedDoc.from_jsonable(json.loads(decoded))
        return DocList([ParsedDoc.from_jsonable(j, make_dict_id) for j in json_list])



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


# def _datum_to_str(datum : str|Set) -> str:
#     if not datum: return ''
#     return datum if isinstance(datum, str) else ','.join(datum)

doc_id_str = 'newdoc id'
token_key_str = 'tokens'
node_id_key = 'id'



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

    