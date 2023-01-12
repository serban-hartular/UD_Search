from __future__ import annotations

from typing import List, Iterator, Dict


from tree_path.tree import Tree



def _local_before(n1 : Tree, n2 : Tree) -> bool:
    return float(n1._data['id']) < float(n2._data['id'])

before = _local_before

class Match:
    def __init__(self, node : Tree, children : List[Match] = None):
        self.node = node
        self.next_nodes = children if children is not None else []
        self.metadata = {}
    def data(self) -> Dict:
        return self.node._data
    def matches_level(self, depth) -> List[Match]:
        return Match.get_matches([self], depth)
    @staticmethod
    def get_matches(matches : List[Match], depth = 0) -> List[Match]:
        if depth < 0: return []
        if depth == 0:
            return matches
        match_list = []
        for match in matches:
            match_list += Match.get_matches(match.next_nodes, depth-1)
        return match_list
        
    def __str__(self):
        return str(self.node) + '->' + str(len(self.next_nodes))
    def __repr__(self):
        return self.__str__()

class Evaluator:
    def evaluate(self, node : Tree) -> List[Match]|bool:
        pass

class ConstantEvaluator(Evaluator):
    def __init__(self, value):
        self._value = value
    def evaluate(self, node : Tree) -> List[Match]|bool:
        return self._value

class ValueComparer(Evaluator):
    def __init__(self, operator : str, name : List[str], value : List[str]):
        self.operator = operator
        self.name = name
        self.value = set(value)
    def evaluate(self, node : Tree) -> List[Match]|bool:
        if node is None: # this is the cancan21-incerca-reusi-train-annot root
            return []
        token = node._data
        tok_val = token
        for key in self.name:
            tok_val = tok_val.get(key)
            if tok_val is None: break
        if isinstance(tok_val, str):
            tok_val = {tok_val}
        if tok_val is None:
            if self.operator == '?=': return True #[head_node]
            elif self.operator == '=': return False #[]
            else: raise Exception('Unknown operator ' + self.operator)
        if not isinstance(tok_val, set):
            raise Exception('Value of %s is not a string or set -- %s' % ('.'.join(self.name), str(tok_val)))
        # is it a star * ?
        if '*' in self.value:
            return True
        return bool(self.value.intersection(tok_val)) #[head_node] if self.value.intersection(tok_val) else []
    def __str__(self):
        return '.'.join(self.name) + self.operator + ','.join(self.value)
    def __repr__(self):
        return self.__str__()

class ValueExpression(Evaluator):
    def __init__(self, operator: str, left: Evaluator, right: Evaluator = None):
        self.operator = operator
        self.left = left
        self.right = right
    def evaluate(self, node : Tree) -> List[Match]|bool:        
        left_val = self.left.evaluate(node)
        right_val = self.right.evaluate(node) if self.right else None
        return_list = []
        return_list += left_val if isinstance(left_val, list) else []
        return_list += right_val if isinstance(right_val, list) else []
        if self.operator == '|':
            if left_val or right_val:
                return  return_list if return_list else True # [Match(t) for t in return_list]
            return False
        if self.operator == '&':
            if left_val and right_val:
                return return_list if return_list else True
            return False
        if self.operator == '!':
            return not bool(left_val)
        raise Exception('Unknown operator ' + self.operator)
    def __str__(self):
        return self.operator + '(' + self.left.__str__() + (' ' + self.right.__str__() if self.right else '') + ')'
    def __repr__(self):
        return self.__str__()


class NodeEvaluator(Evaluator):
    def __init__(self, path_type : str, evaluator : Evaluator, list_return = False ):
        self.path_type = path_type
        self.evaluator = evaluator
        self.list_return = list_return
    def evaluate(self, node : Tree) -> List[Match]|bool:
        if not node:
            return False
        if self.path_type == '../': # parent
            node_list = [node.parent]
        elif self.path_type == '/': # children
            node_list = node.children()
        elif self.path_type == '//': # all descendants
            node_list = [c for c in node.traverse() if c is not node]
        elif self.path_type == './': # children plus self
            node_list = [node] + node.children()
        elif self.path_type == './/': # all descendants plus self
            node_list = node.traverse()
        elif self.path_type == '.': # current head_node
            node_list = [node]
        elif self.path_type == '<':
            node_list = [child for child in node.children() if before(child, node)]
        elif self.path_type == '>':
            node_list = [child for child in node.children() if not before(child, node)]
        else:
            raise Exception("Unkown path " + str(self.path_type))
        return_list = []
        for candidate in node_list:
            eval = self.evaluator.evaluate(candidate)
            if not eval:
                continue
            if not isinstance(eval, list):               
                eval = []
            return_list.append(Match(candidate, eval))
        if self.list_return:            
            return return_list
        return bool(return_list)
    
    def __str__(self):
        return self.path_type + '[' + self.evaluator.__str__() + ']'
    def __repr__(self):
        return self.__str__()
