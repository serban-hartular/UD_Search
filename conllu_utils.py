from __future__ import annotations

from typing import Callable, List

import pyconll
from pyconll.unit.sentence import Sentence
from pyconll.unit.token import Token


def split_conllu_by_doc(conllu_in : str, conllu_out1 : str, conllu_out2 : str, one_in = 4):
    conllu_out1 = open(conllu_out1, 'w', encoding='utf8')
    conllu_out2 = open(conllu_out2, 'w', encoding='utf8')
    doc_count = 0
    for sentence in pyconll.iter_from_file(conllu_in):
        if sentence.meta_present('newdoc id'):
            doc_count += 1
        if doc_count % one_in != 0:
            out = conllu_out1
        else:
            out = conllu_out2
        out.write(sentence.conll() + '\n\n')
    conllu_out1.close()
    conllu_out2.close()
    
def extract_sentences(conllu_in : str, conllu_out : str, condition : Callable[[Sentence], bool] | List[str]) -> int:
    conllu_out = open(conllu_out, 'w', encoding='utf8')
    if not isinstance(condition, Callable):
        id_list = condition
        condition = lambda s : s.id in id_list
    count = 0
    for sentence in pyconll.iter_from_file(conllu_in):
        if not sentence: continue
        if condition(sentence):
            conllu_out.write(sentence.conll() + '\n\n')
            count += 1
    conllu_out.close()
    return count

def sentence_by_id(conllu_filename : str, sent_id : str) -> Sentence|None:
    for sentence in pyconll.iter_from_file(conllu_filename):
        if sentence.id == sent_id:
            return sentence
    return None

def token_neighbors(sentence : Sentence, token_id : str, toks_before : int, toks_after : int) -> List[Token]:
    tok = sentence[token_id]
    tok_list = [t for t in sentence]
    tok_index = tok_list.index(tok)
    begin = tok_index - toks_before
    end = tok_index + toks_after + 1
    if begin < 0 or end > len(tok_list):
        return []
    return tok_list[begin:end]
