from typing import List

from tree_path.evaluator import Evaluator, ValueComparer, ValueExpression, NodeEvaluator, ConstantEvaluator, Match
from tree_path.tree import Tree

_grammar = r"""

node_list   : head_node
           | head_node node_list 
           | '!' node_list
            ;
            
head_node    : PATH_MARKER token
        ;

token   : '[' attribs ']'
        ;

attribs : attribs '|' attribs  {left, 14}
        | attribs '&' attribs  {left, 15}
        | attribs attribs {left, 15} //same as &
        | '!' attribs  {16}
        | '(' attribs ')'
        | name EQU value
        | head_node
        | '*' //head_node any head_node
        ;
 
value : value ',' WORD
        | WORD
        | '*'
        ; 

name    : name DOT WORD
        | WORD
        ;

PATH_MARKER : '/' | '//' | DOT DOT '/' | DOT '/' | DOT '//' | DOT | '<' | '>';
EQU : '='
    | '?='
    ;

terminals
WORD: /[\w'][\w\-\:]*/;
DOT: /\./;
"""

def _node_list_return(n : List[NodeEvaluator]):
    if len(n) == 1:
        n[0].list_return = True
        return n[0]
    n[1].list_return = True
    new_node = NodeEvaluator(n[0].path_type, ValueExpression('&', n[0].evaluator, n[1]), True)
    return new_node

_actions = {
    "token": [lambda _, n: n[1],
             ],
    "attribs": [ lambda _, n: ValueExpression(n[1], n[0], n[2]), # or
                 lambda _, n: ValueExpression(n[1], n[0], n[2]), # and
                 lambda _, n: ValueExpression('&',  n[0], n[1]), # same as and
                 lambda _, n: ValueExpression(n[0], n[1]),  # not
                 lambda _, n: n[1], # parenthesis
                 lambda _, n: ValueComparer(n[1], n[0], n[2]), # name = value
                 lambda _, n: n[0], # head_node
                 lambda _, n: ConstantEvaluator(True)
                ],
    "head_node": [ lambda _, n: NodeEvaluator(n[0], n[1]),
                   # lambda _, n: ValueExpression(n[0], n[1])  # not n[1]
            ],
    "node_list": [lambda _, n: _node_list_return(n),  #n[0],
                  lambda _, n: _node_list_return(n),  #NodeEvaluator(n[0].path_type, ValueExpression('&', n[0].evaluator, n[1]))
                  lambda _, n: ValueExpression(n[0], n[1]),  # not
                  ],
    "value": [lambda _, n: n[0] + [n[2]],
              lambda _, n: [n[0]],
              lambda _, n: [n[0]],
            ],
    "name": [
        lambda _, n: n[0] + [n[2]],
        lambda _, n: [n[0]],
    ],
    "PATH_MARKER": [
        lambda _, n: n[0],
        lambda _, n: n[0],
        lambda _, n: ''.join(n),
        lambda _, n: ''.join(n),
        lambda _, n: ''.join(n),
        lambda _, n: n[0],
        lambda _, n: n[0],
        lambda _, n: n[0],
    ],
    "EQU": [
        lambda _, n: n[0],
        lambda _, n: n[0],
    ],
}

# _g = Grammar.from_string(_grammar)
# _parser = Parser(_g, debug=False, _actions=_actions)

_g = None
_parser = None


class Search:
    def __init__(self, expression : str):
        self._expression = expression
        try:
            self._expr_tree : Evaluator = _parser.parse(expression)
        except Exception as e:
            raise Exception('Parse error in expression %s: %s' % (expression, str(e)))
    def find(self, tree : Tree) -> List[Match]:
        return self._expr_tree.evaluate(tree)
    def __str__(self):
        return str(self._expr_tree)
    def __repr__(self):
        return repr(str(self))


