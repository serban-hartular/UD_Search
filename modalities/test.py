from modalities import pred_expr_comparison
from modalities.tree_to_modalities import tree_to_modal_exprs 
from valences.clause_types import clause_type, get_annotated_antecedent
import pyconll
import tree_path

filename = 'ellipses2.conllu'
for sentence in pyconll.load_from_file(filename):
    # if sentence.id != 'train-4087':
    #     continue
    tree = tree_path.conllu.from_conllu(sentence)
    ellipsis = None
    for node in tree.traverse():
        if node.data['misc'].get('GapType') == {'CompEllipsis'}:
            ellipsis = node
            break
    if not ellipsis:
        continue
    if ellipsis.data['deprel'] in ('ccomp', 'ccomp:pmod', 'xcomp', 'csubj', 'csubj:pass'):
        ellipsis_regent = ellipsis.parent
    else:
        ellipsis_regent = None
    ellipsis_type = clause_type(ellipsis if ellipsis else ellipsis_regent)
    antecedent, antecedent_regent = get_annotated_antecedent(ellipsis)
    antecedent_type = clause_type(antecedent if antecedent else antecedent_regent)
    if ellipsis_type[0] in ('rel', 'compar'): continue
    e = ellipsis if ellipsis else ellipsis_regent
    e_mods = tree_to_modal_exprs(e)
    print(sentence.id, sentence.text)
    print('Ellipsis: %s' % str(e))
    candidates = []
    best = None, 0, None, None
    print('Candidates:')
    for ant_regent_candidate in tree.traverse():
        if ant_regent_candidate in (ellipsis, ellipsis_regent) or ant_regent_candidate.data['deprel'] == 'aux':
            continue
        a_mods = tree_to_modal_exprs(ant_regent_candidate)
        if not a_mods:
            continue
        best = None, 0, None, None
        for a_mod, e_mod in zip(a_mods, e_mods):
            combo = pred_expr_comparison.find_best_combination(a_mod, e_mod)
            if combo[0] > best[1]:
                best = (ant_regent_candidate,) + combo
        print(best)
    print('Antecedent / Regent:\n%s\t%s' % (str(antecedent), str(antecedent_regent)))
    print()
