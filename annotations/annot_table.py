from __future__ import annotations

from typing import List, Dict

from tree_path import ParsedDoc, Search, DocList
import pandas as pd

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
        #if 'misc.TargetID' in labels:
        if node.sdata('misc.TargetID'):
            target, _ = doc.get_node_by_uid(node.sdata('misc.TargetID'))
            if target:
                targetform = target.sdata('form')
                targetdeprel = target.sdata('deprel')
        text = str(node.root())
        d.update({k:v for k,v in zip(default_labels_after, [targetform, targetdeprel, text])})
        table.append(d)
    return table

def doclist_to_csv_table(doclist : DocList, doc_search : str|Search, outfile : str, labels : List[str] = None) -> pd.DataFrame:
    table = []
    for doc in doclist:
        table += doc_to_annotation_table(doc, doc_search, labels)
    df = pd.DataFrame(table)
    if outfile:
        df.to_csv('df.csv', sep='\t', encoding='utf-8')
    return df


def apply_annotation_table_to_doc(doc : ParsedDoc, annot_table : List[Dict[str, str]], labels : List[str] = None):
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


def apply_annotation_df_to_doclist(doclist : DocList, source : pd.DataFrame|str, labels : List[str] = None):
    if not labels:
        labels = ['misc.Ellipsis', 'misc.Antecedent', 'misc.Info', 'misc.TargetID']
    if isinstance(source, str):
        source = pd.read_csv(source, sep='\t', encoding='utf-8')
    rows = source.to_dict(orient='records')
    rows = [{k: '' if pd.isna(v) else v 
             for k,v in d.items()} for d in rows]
    # separate by doc_id
    for d in rows:
        uid = d['UID']
        node = doclist.get_node_by_uid(uid)
        for k in labels:  # first remove
            node.remove(k) 
        for k in labels: # now add values
            if d.get(k):
                node.assign(k, {d[k]}) # needs to be a set

    