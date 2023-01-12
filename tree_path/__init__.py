
#from parglare import Parser, Grammar
import parglare
import tree_path.search #import _g, _parser, _grammar, _actions
from tree_path.search import Search
from tree_path.evaluator import Match, before
from tree_path.tree import Tree
from tree_path.conllu import ParsedSentence, search_conllu_files
from tree_path.parsed_doc import ParsedDoc, iter_docs_from_conll

search._g = parglare.Grammar.from_string(search._grammar)
search._parser = parglare.Parser(search._g, debug=False, actions=search._actions)
