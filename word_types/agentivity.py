from collections import defaultdict
from typing import Tuple, Dict, List

import pyconll

from tree_path import Tree, Search, parsed_doc
from tree_path.conllu import get_full_lemma


def get_valence(node : Tree, to_include : List[str] = None) -> Tuple[str]:
    if to_include is None:
        to_include = ['obj', 'ccomp', 'xcomp', 'aux:pass', 'expl:pass', 'expl:pv',
                    'expl:impers', 'ccomp:pmod', 'iobj', 'obl:pmod', 'nmod:pmod', 'csubj', 'aux:pass']
    valence = {child._data['deprel'] for child in node.children() if child._data['deprel'] in to_include}
    if node.parent and node.parent._data['_lemma'] == 'putea' and node._data['feats'].get('VerbForm') and \
            'Inf' in node._data['feats'].get('VerbForm'):
        to_include = [v for v in to_include if v != node._data['deprel']]
        parent_valence = {child._data['deprel'] for child in node.parent.children() if child._data['deprel'] in to_include}
        valence = valence.union(parent_valence)
    valence = list([str(v) for v in valence])
    valence.sort()
    return tuple(valence)

filename = './../UD2.10/UD_Romanian-RRT/ro_rrt-ud-train.conllu'


def get_noun_count(conllu_filename : str) -> Dict[str, Dict[str, int]]:
    noun_count : Dict[str, Dict[str, int]] = defaultdict(lambda : defaultdict(int))
    for sentence in pyconll.iter_from_file(conllu_filename):
        tree = parsed_doc.from_conllu(sentence)
        verbs = Search('.//[upos=VERB  /[deprel=obj upos=NOUN,PROPN] /[deprel=nsubj upos=NOUN,PROPN] ]').find(tree)
        for verb in [m.node for m in verbs]:
            for deprel in ('nsubj', 'obj'):
                node = Search('/[deprel=%s upos=NOUN,PROPN]' % (deprel)).find(verb)[0].node
                noun_count[node._data['_lemma']][deprel] += 1
                noun_count[node._data['_lemma']]['total'] += 1                
    noun_count = {k:dict(v) for k,v in noun_count.items()}
    return noun_count


with open('./nouns_agentivity.txt', 'r', encoding='utf8') as handle:
    n_agent_score = handle.readlines()
    n_agent_score = {l.split('\t')[0]:float(l.split('\t')[1]) for l in n_agent_score}

n_agent_score.update({'PersPron12':1})

verb_deprel_agentivity : Dict[Tuple, Dict[str, Tuple[int, int]]] = defaultdict(lambda : defaultdict(lambda : (0, 0)))
# verb_deprel_agentivity[('avea', ('nsubj', 'obj')]['obj'] = (sum_of_scores, count_of_scores )

for sentence in pyconll.iter_from_file(filename):
    tree = parsed_doc.from_conllu(sentence)
    verbs = Search('.//[upos=VERB]').find(tree)
    for verb in [m.node for m in verbs]:
        valence = get_valence(verb)
        deprels = ['nsubj', 'obj', 'iobj', 'obl', 'obl:agent', 'obl:pmod']
        lemma = get_full_lemma(verb)
        key = (lemma, valence)
        for deprel in deprels:
            child = Search('/[deprel=%s]' % (deprel)).find(verb)
            score = None
            if not child:
                continue
            child = child[0].node
            if deprel.startswith('obl'):
                adp = Search('/[upos=ADP]').find(child)
                if adp:    deprel = deprel + ':' + adp[0].node._data['_lemma']
            if child._data['_lemma'] in n_agent_score:
                score = n_agent_score[child._data['_lemma']]
            else: # look for pers pronoun
                if Search('.[upos=PRON PronType=Prs (Person=1,2 | Strength=Strong) ]').find(child):
                    score = 1
            if score is not None:
                (score_sum, count) = verb_deprel_agentivity[key][deprel]
                verb_deprel_agentivity[key][deprel] = (score_sum + score, count + 1)

deprel_count_cutoff = 5
verb_deprel_agentivity = {k:{deprel:sum/count for deprel, (sum,count) in v.items() if count > deprel_count_cutoff-1} \
                          for k,v in verb_deprel_agentivity.items()}
verb_deprel_agentivity = {k:v for k,v in verb_deprel_agentivity.items() if v} # liminate empty
        