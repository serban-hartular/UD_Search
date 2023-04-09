from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Dict, List
import tree_path as tp
from tree_path import ParsedDoc, ParsedSentence, DocList

AnnotationToken = Dict[str, str]

TOKEN_ID_KEY = 'id'
DOC_ID_STR = 'newdoc id'  # this messes things up


@dataclass
class AnnotationSequence:
    doc_id: str
    tokens: List[AnnotationToken]
    def to_dict(self) -> Dict[str, List|str]:
        d = dataclasses.asdict(self)
        d[DOC_ID_STR] = d['doc_id'] # becasue 'newdoc id' has a space in it
        d.pop('doc_id')
        return d
    @staticmethod
    def from_dict(d : Dict[str, List|str]) -> AnnotationSequence:
        d['doc_id'] = d[DOC_ID_STR]
        d.pop(DOC_ID_STR)
        return AnnotationSequence(**d)


def sentence_to_annotation_sequence(sentence : ParsedSentence, keys_aliases : Dict,
                                    doc : ParsedDoc = None) -> List[AnnotationToken]:
    """key_aliases = {'lemma':'lemma', 'misc.Ellipsis':'Ellipsis', etc}"""
    projection = sentence.projection_nodes()
    dict_list = []
    for node in projection:
        d = {alias : node.sdata(key) for key,alias in keys_aliases.items()
                if node.sdata(key) }
        if doc:
            d[TOKEN_ID_KEY] = doc.uid(node)
        dict_list.append(d)
    return dict_list

def doc_to_annotation_sequence(doc : ParsedDoc, keys_aliases : Dict) -> AnnotationSequence:
            # , sentence_search : str|Search|None = None) \
    dict_list = []
    for sentence in doc:
        s_toks = sentence_to_annotation_sequence(sentence, keys_aliases, doc)
        dict_list.extend(s_toks)
    return AnnotationSequence(doc.doc_id, dict_list)

import pickle
def doclist_to_annot_seq(doclist : DocList, keys_aliases : Dict, pickle_outfile : str = '') -> List[Dict]:
    """If pickle_outfile, will pickle return value to destination"""
    anl = [doc_to_annotation_sequence(doc, keys_aliases).to_dict() for doc in doclist]
    if pickle_outfile:
        with open(pickle_outfile, 'wb') as handle:
            pickle.dump(anl, handle)
    return anl

def apply_annotations_to_doc(annot_seq : AnnotationSequence|Dict, doc : ParsedDoc, key_aliases : Dict,
                             remove_absent_keys : bool = True):
    """if remove_absent_keys, keys in the key_aliases dict that 
    don't appear in an annotation token will be removed from the corresponding node data"""
    # sanity check
    if isinstance(annot_seq, Dict):
        annot_seq = AnnotationSequence.from_dict(annot_seq)

    if len(list(key_aliases.values())) != len(set(key_aliases.values())):
        raise Exception('Keys and aliases must be unique!')
    if TOKEN_ID_KEY in key_aliases.values() or TOKEN_ID_KEY in key_aliases.keys():
        raise Exception('Trying to delete node id: ' + str(key_aliases))
    
    for annot in annot_seq.tokens:
        uid = annot[TOKEN_ID_KEY]
        node = doc.get_node_by_uid(uid)
        if node is None: raise 'Could not find node with uid ' + uid
        aliases_keys = {v:k for k,v in key_aliases.items()}
        update_dict = {k:v for k,v in annot.items() if k in aliases_keys.keys()} # filter
        for local_key, alias in key_aliases.items():
            if alias in annot:
                node.assign(local_key, {annot[alias]} ) # attention! make set!
            elif remove_absent_keys:
                node.remove(local_key)

def apply_annot_seq_to_doclist(source : str | List[Dict], doclist : DocList, key_aliases : Dict,
                               remove_absent_keys : bool = True):
    if isinstance(source, str):
        with open(source, 'rb') as handle:
            source = pickle.load(handle)
    if len(set([doc.doc_id for doc in doclist])) < len(doclist):
        raise Exception('Doc ids not unique!')
    doc_dict = {doc.doc_id : doc for doc in doclist}
    anl = [AnnotationSequence.from_dict(d) for d in source]
    for annot in anl:
        if annot.doc_id in doc_dict:
            apply_annotations_to_doc(annot, doc_dict[annot.doc_id], key_aliases, remove_absent_keys)
