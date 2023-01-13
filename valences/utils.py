
import tree_path as tp
import tree_path.evaluator
from tree_path import ParsedSentence, Tree, Search

def complex_predicate_root(node : Tree) -> Tree:
    while node.parent:
        if node.data('deprel') in ('ccomp', 'ccomp:pmod', 'csubj'):
            node = node.parent
        else: break
    return node

def is_imbrique(node : Tree) -> bool:
    sentence : ParsedSentence = node.root()
    head = complex_predicate_root(node)
    head_proj = head.projection_nodes()
    sentence_proj = sentence.projection_nodes()
    preceding = sentence_proj[sentence_proj.index(head_proj[0])-1]\
        if sentence_proj.index(head_proj[0]) > 0 else None
    succeeding =  sentence_proj[sentence_proj.index(head_proj[-1])+1]\
        if sentence_proj.index(head_proj[-1]) < len(sentence_proj)-1 else None
    beginning_test = head_proj[0] == sentence_proj[0] or head_proj[0].data('upos') == 'PUNCT' or \
                (preceding and preceding.data('upos') == 'PUNCT')
    ending_test = head_proj[-1] == sentence_proj[-1] or head_proj[-1].data('upos') == 'PUNCT' or \
                  (succeeding and succeeding.data('upos') == 'PUNCT')
    return beginning_test and ending_test

def anaphoric_advmod_present(node : Tree) -> (bool, bool):
    """Returns if present, and true if before"""
    node = complex_predicate_root(node)
    advmods = ['după cum', 'așa cum', 'așa', 'cum', 'altfel']
    before = [n for n in node.projection_nodes() if tree_path.evaluator.before(n, node)]
    after = [n for n in node.projection_nodes() if n is not node and n not in before]
    before = ' '.join([n.data('form') for n in before])
    after = ' '.join([n.data('form') for n in after])
    in_before = any([a in before for a in advmods])
    in_after = any([a in after for a in advmods])
    return in_before or in_after, in_before
