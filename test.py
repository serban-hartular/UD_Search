
import pickle
import tree_path as tp
import antecedent_detection
from antecedent_detection.antecedent_guess import *

with open('./antecedent_models/MLPClassifier.p', 'rb') as handle:
    model = pickle.load(handle)
labels = ['candidate_licenser_rel', 'candidate_precedent_rel', 'cataphoric', 'same_lemma', 'same_modality', 'same_mod_class', 'epist_e', 'aprecia_e', 'aspect_e', 'deont_e', 'dicendi_e', 'epist_a', 'aprecia_a', 'aspect_a', 'deont_a', 'dicendi_a', 'subjunctive', 'group_dist']

print('Loading...', end=' ')
dl = tp.DocList.from_conllu('./sent_id_parses/cancan21-annot-2-VPE.correct.conllu')
print('Done\n')

for doc in dl:
    test_guess_antecedent(doc, model, labels)
