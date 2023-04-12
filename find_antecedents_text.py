import pickle
from typing import Dict, List

import pandas as pd

import stanza_parse
import antecedent_detection
import licenser_detection
import tree_path as tp
from antecedent_detection.antecedent_guess import Model

model = None
score =  0

def load_model(class_name : str):
    global model, score, labels
    with open('./antecedent_models/' + class_name + '.p', 'rb') as handle:
        model, score, labels = pickle.load(handle)

load_model('MLPClassifier')

    
doc : tp.ParsedDoc = None

def find_antecedents_in_text(text : str) -> pd.DataFrame:
    global doc
    doc = stanza_parse.text_to_doc(text)
    doc.doc_id = 'parse'
    licenser_detection.annotate_licensers(doc)
    licensers = [m.node for m in doc.search('.//[misc.Ellipsis=VPE]')]
    antecs, df = antecedent_detection.antecedent_guess.guess_antecedents(doc, licensers, model, labels)
    print('\t'.join(['Lic ID', 'Lic', 'Ant ID', 'Antec', 'Prob', 'Type']))
    for licenser, (antecedent_id, prob, antec_type) in zip(licensers, antecs):
        data = [doc.uid(licenser), licenser.sdata('form'), antecedent_id,
                doc.get_node_by_uid(antecedent_id).sdata('form'), '%.2f' % prob, antec_type]
        print('\t'.join(data))
    return df

def doc_annotate_ellipses(doc : tp.ParsedDoc, antecedent_detection_model : Model, labels : List[str]):
    licenser_detection.annotate_licensers(doc)
    licensers = [m.node for m in doc.search('.//[misc.Ellipsis=VPE]')]
    antecs, df = antecedent_detection.antecedent_guess.guess_antecedents(doc, licensers, antecedent_detection_model, labels)
    for licenser, (antec_id, antec_score, antec_type) in zip(licensers, antecs):
        licenser.assign('misc.TargetID', {antec_id})
        licenser.assign('misc.Antecedent', {antec_type})
        
def text_to_ellipsis_annotated_doc(text : str, antecedent_detection_model : Model, labels : List[str]) -> tp.ParsedDoc:
    doc = stanza_parse.text_to_doc(text)
    doc_annotate_ellipses(doc, antecedent_detection_model, labels)
    return doc

def textfile_to_ellipsis_annotated_doc(filename : str, antecedent_detection_model : Model, labels : List[str]) -> tp.ParsedDoc:
    with open(filename, 'r', encoding='utf-8') as handle:
        text = handle.read()
    return text_to_ellipsis_annotated_doc(text, antecedent_detection_model, labels)
