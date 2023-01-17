from collections import defaultdict
from typing import List, Dict, Tuple

import tree_path as tp
from tree_path import ParsedDoc

def generate_upos_dict_from_docs(doc_list : List[ParsedDoc]) ->  Dict[str, Tuple[str, float]]:
    form_dict = defaultdict(lambda : defaultdict(int))
    for doc in doc_list:
        for node in doc.token_iter():
            form_dict[node.sdata('form').lower()][node.sdata('upos')] += 1
    form_dict = {form : [t for t in upos_dict.items()] for form,upos_dict in form_dict.items()}
    for form, upos_tuples in form_dict.items():
        upos_tuples.sort(key=lambda t : -t[1]) # sort decreasing
        upos_sum = sum([t[1] for t in upos_tuples])
        form_dict[form] = [(upos,count/upos_sum) for (upos, count) in upos_tuples]
    return form_dict

