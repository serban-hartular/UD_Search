
import valences
import word_types
import tree_path as tp
import clause_info

def prep_document(doc : tp.ParsedDoc):
    for verb in [m.node for m in doc.search('.//[upos=VERB]')]:
        morpho = word_types.ro_verb_forms.get_verb_form(verb)
        full_lemma = str(valences.get_verb_lemma(verb))
        for k,v in morpho.items():
            verb.assign('misc.'+k, v)
        verb.assign('misc.FullLemma', full_lemma)

def filter(node : tp.Tree) -> bool:
    """Returns false if to skip, true if to mark"""
    if node.sdata('upos') != 'VERB': return False
    filter_fns = [valences.basic_filter, valences.basic_next_word_filter]
    filter_results = [fn(node) for fn in filter_fns]
    return all(filter_results)

def annotate_licensers(doc : tp.ParsedDoc):
    prep_document(doc)
    for sentence in doc:
        for node in sentence.traverse():
            if not filter(node):
                continue
            if not valences.get_matching_valences(node):
                continue
            if not valences.quote_introduction_filter(node):
                node.assign('misc.Ellipsis', {'Quote'})
                continue
            if clause_info.clause_types.is_rnr(node):
                node.assign('misc.Ellipsis', {'RNR'})
                continue
            if clause_info.clause_types.is_expression(node):
                node.assign('misc.Ellipsis', {'Expression'})
                continue
            node.assign('misc.Ellipsis', {'VPE'})
