import pyconll

import tree_path.conllu
from tree_path import Search, parsed_doc
from tree_path.conllu import ParsedSentence
from clause_info.lemma_pipeline import get_full_lemma



for s_conll in pyconll.iter_from_file('cancan_annot/cancan21-train-annot.2.conllu'):
    sentence = ParsedSentence(parsed_doc.from_conllu(s_conll), s_conll.id, s_conll.text)
    ms = Search('.//[misc.Ellipsis=Expression]').find(sentence)
    for m in ms:
        node = m.node
        target = None
        if 'TargetID' in node._data['misc']:
            target_uid = list(node._data['misc']['TargetID'])[0]
            sent_id, target_id = tree_path.conllu.sent_tok_id_from_unique(target_uid)
            if sent_id == sentence.sent_id:
                target = sentence.node(target_id)
        # print(sentence.sent_id, m.node, sentence.sent_text)
        print(get_full_lemma(node), node._data['deprel'], end='\t')
        if target:
            print(get_full_lemma(target), target.data['deprel'])
        else:
            print()
