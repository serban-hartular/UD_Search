
#from parglare import Parser, Grammar
import parglare
import tree_path.search #import _g, _parser, _grammar, _actions
from tree_path.search import Search
from tree_path.evaluator import Match
from tree_path.tree import Tree
from tree_path.conllu import search_conllu_files, ParsedSentence

search._g = parglare.Grammar.from_string(search._grammar)
search._parser = parglare.Parser(search._g, debug=False, actions=search._actions)
