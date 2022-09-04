from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

import pyconll
from pyconll.unit.sentence import Sentence

import tree_path
from tree_path import Search, Match, Tree
import valences.lemma_pipeline as v_lem

question_options = {
    'Ellipsis' : ['BadParse', 'Expression', 'NotVerb', 'Voice', 'Absolute', 'WrongValence', 'Semantic', 'RNR', 'VPE'],
    'Antecedent': ['Present', 'Elided', 'External', 'Exophoric'],
    'TargetID' : []
}

continue_answers = ['RNR', 'VPE', 'Present', 'Elided']

import valences.clause_types as ct


def _get_hint(node : Tree) -> (str, str, str):
    if ct.is_mis_parse(node) or ct.no_diacritics(node):
        return 'Bad Parse', '', ''
    if ct.is_expression(node):
        return 'Expression', '', ''
    rnr = ct.is_rnr(node)
    if rnr:
        return 'RNR', 'Present', rnr.data['id']
    if ct.is_relative(node) or ct.is_comparative(node) or ct.is_cause_effect(node):
        return 'VPE', 'Present', node.parent.data['id'] if node.parent else ''
    if ct.is_coord_conjunct(node):
        guess = ct.get_previous_conjunct(node)
        ccomp = Search('/[deprel=ccomp]').find(guess)
        if ccomp: guess = ccomp[0].node
        return 'VPE', 'Present', guess.data['id']
    return '', '', ''

def annotate_conllu(conllu_in : str, conllu_out : str, lemma_valence_dict : Dict[str, List[Tuple]], sent_ids : List[str] = None):
    conllu_out = open(conllu_out, 'w', encoding='utf8')
    lemmas = [l for l in lemma_valence_dict.keys()]
    l0 = [l.split(' ')[0] for l in lemmas]
    search = Search('.//[lemma=%s upos=VERB]' % ','.join(l0))
    answer = None
    for sentence in pyconll.iter_from_file(conllu_in):
        if sent_ids and sentence.id not in sent_ids:
            continue
        tree = tree_path.conllu.from_conllu(sentence)
        ms = search.find(tree)
        tokens = tree.projection()
        sentence_display = ' '.join(['(%s)%s' % (t['id'], t['form']) for t in tokens])
        for m in ms:
            node = m.node
            if node.data['deprel'] in ('fixed' or 'flat'): continue
            lemma = v_lem.get_full_lemma(node)
            if lemma not in lemmas: continue
            valence = v_lem.get_valence(node)
            if valence not in lemma_valence_dict[lemma]: continue
            answer_dict = {}
            hints = _get_hint(node)
            for question, hint in zip(('Ellipsis', 'Antecedent', 'AntecedentID'), hints):
                while True:
                    print('Sentence %s: ' % sentence.id + sentence.text)
                    print(sentence_display)
                    print('Node: ' + str(node))
                    if answer_dict: print(answer_dict)
                    print(question + '=?')
                    options = question_options[question]
                    if options and hint and hint not in options: raise Exception('Invalid hint ' + hint)
                    print('\n'.join(['%d. %s' % (i,o) for i,o in zip(range(0,len(options)), options)]))
                    answer = input('Default %s' % hint if hint else '')
                    if answer == '' and hint:
                        answer = hint
                    else:
                        try:
                            answer = int(answer)
                            if answer == -1: break
                            answer = options[answer] if options else str(answer)
                        except: 
                            print('Bad input ' + str(answer))
                            continue
                        # if answer == -1: break
                        # answer = options[answer] if options else str(answer)
                    answer_dict[question] = {answer}
                    break
                if answer not in continue_answers: break
            if answer == -1: break
            print(answer_dict)
            pyconll_tok = sentence[node.data['id']]
            pyconll_tok.misc.update(answer_dict)
        if answer == -1: break
        sentence_conllu = sentence.conll()
        # print(sentence_conllu)
        conllu_out.write(sentence_conllu + '\n\n')
    conllu_out.close()

import word_types.ro_verb_forms as vb_forms

def get_vp_characteristics(node : Tree) -> Tuple[Dict, Dict]:
    if node.data['upos'] not in ('VERB', 'AUX'):
        return {'lemma': node.data['lemma']}, {}

    form = vb_forms.get_verb_form(node)
    subj_info = {k:v for k,v in form.items() if k in ('Person','Number')}
    subj = Search('/[deprel=nsubj,csubj]').find(node)
    if subj:
        subj = subj[0].node
        subj_info['lemma'] = subj.data['lemma']
    verb_info = {'lemma':node.data['lemma']}
    verb_info.update({k:v for k,v in form.items() if k in ('Mood','Tense')})
    return verb_info, subj_info

def infodict_to_str(infodict : Dict) -> str:
    return '|'.join([k+'='+(v if isinstance(v, str) else ','.join(v)) for k,v in infodict.items()])

def list_ellipses_antecedents(conllu_filename : str):
    for sentence in pyconll.iter_from_file(conllu_filename):
        tree = tree_path.conllu.from_conllu(sentence)
        tokens = tree.projection()
        for ellipsis in [t for t in tokens if t['misc'].get('Ellipsis') == {'VPE'} and t['misc'].get('Antecedent') == {'Present'}]:
            e_id = ellipsis['id']
            a_id = list(ellipsis['misc']['AntecedentID'])[0]
            e_node = tree.search(lambda t : t.data['id'] == e_id)[0]
            a_node = tree.search(lambda t : t.data['id'] == a_id)[0]
            e_info = get_vp_characteristics(e_node)
            a_info = get_vp_characteristics(a_node)
            a_regent = a_node.parent if a_node.parent and a_node.data['deprel'] in ('ccomp', 'csubj', 'ccomp:pmod', 'obj') else None
            if a_regent:
                a_regent_info = get_vp_characteristics(a_regent)
            else:
                a_regent_info = {}, {}
            print(sentence.id + '\t' + sentence.text)
            print('Antecedent:\t' + ' '.join([infodict_to_str(d) for d in a_regent_info]) + '\t' +' '.join([infodict_to_str(d) for d in a_info]))
            print('Ellipsis:\t' + ' '.join([infodict_to_str(d) for d in e_info]))

def collect_annotations(filenames : List[str]) -> Dict[str, Dict[str, Dict]]:
    """Returns d[sent_id][tok_id] = dict to update misc with"""
    annot_dict = defaultdict(lambda : defaultdict(dict))
    for filename in filenames:
        for sentence in pyconll.iter_from_file(filename):
            sent_id = sentence.id
            for token in sentence:
                tok_id = token.id
                if set(token.misc.keys()).intersection(question_options.keys()):
                    annot_dict[sent_id][tok_id].update({k:v for k,v in token.misc.items() if k in question_options.keys()})
    annot_dict = {sid : {tkid : dict(misc) for tkid, misc in v.items()} for sid, v in annot_dict.items()}
    return annot_dict

def add_annotations(conllu_in : str, conllu_out : str, annot_dict : Dict[str, Dict[str, Dict]]):
    conllu_out = open(conllu_out, 'w', encoding='utf8')
    for sentence in pyconll.iter_from_file(conllu_in):
        if sentence.id in annot_dict.keys():
            for token in sentence:
                if token.id not in annot_dict[sentence.id].keys(): continue
                token.misc.update(annot_dict[sentence.id][token.id])
        sentence_conllu = sentence.conll()        
        conllu_out.write(sentence_conllu + '\n\n')
    conllu_out.close()
    
def dump_annotated_text(conllu_filename : str, out = None):
    for sentence in pyconll.iter_from_file(conllu_filename):
        if not sentence.id: continue
        if sentence.meta_present('newdoc id'):
            print('newdoc id = ' + sentence.meta_value('newdoc id'))
        s_string = ''
        for token in sentence:
            space_after = ' '
            s_string = s_string + token.form
            if 'Ellipsis' in token.misc:
                s_string += '{' + list(token.misc['Ellipsis'])[0] + '}'
            s_string += space_after
        print(sentence.id + '\t' + s_string)

import json

def _tok_unique_id(sent_id : str, tok_id : str) -> str:
    return sent_id + '-' + tok_id

def sentence_annotation_json(sentence : Sentence) -> List:
    json_list = []
    prev_char = 0
    for token in sentence:
        json_tok = {'form':token.form, 'id':_tok_unique_id(sentence.id, token.id), 'str_after':' '}
        json_tok.update({k:list(v)[0] for k,v in token.misc.items() if k in question_options.keys()})
        json_list.append(json_tok)
    json_list[-1]['str_after'] = '\n'
    return json_list

_docid_key = 'newdoc id'
def doc_annotation_json(conllu_filename : str) -> List[Dict]:
    doc_id = ''
    doc_dict = {}
    doc_list = []
    for sentence in pyconll.iter_from_file(conllu_filename):
        if not sentence.id: continue
        if sentence.meta_present(_docid_key):
            if doc_dict: doc_list.append(doc_dict)
            doc_dict = {_docid_key :  sentence.meta_value(_docid_key), 'tokens':list()}
        doc_dict['tokens'] += sentence_annotation_json(sentence)
    return doc_list