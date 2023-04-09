import pickle
from typing import Dict

import pandas as pd

import stanza_parse
import antecedent_detection
import licenser_detection
import tree_path as tp

model = None

def load_model(class_name : str):
    global model
    with open('./antecedent_models/' + class_name + '.p', 'rb') as handle:
        model = pickle.load(handle)

load_model('MLPClassifier')

with open('antecedent_models/labels.p', 'rb') as handle:
    labels = pickle.load(handle)
    
doc : tp.ParsedDoc = None

def find_antecedents_in_text(text : str) -> pd.DataFrame:
    global doc
    doc = stanza_parse.text_to_doc(text)
    doc.doc_id = 'parse'
    licenser_detection.annotate_licensers(doc)
    licensers = [m.node for m in doc.search('.//[misc.Ellipsis=VPE]')]
    antecs, df = antecedent_detection.antecedent_guess.guess_antecedents(doc, licensers, model, labels)
    print('\t'.join(['Lic ID', 'Lic', 'Ant ID', 'Antec', 'Prob']))
    for licenser, (antecedent_id, prob) in zip(licensers, antecs):
        data = [doc.uid(licenser), licenser.sdata('form'), antecedent_id,
                doc.get_node_by_uid(antecedent_id).sdata('form'), '%.2f' % prob]
        print('\t'.join(data))
    return df
