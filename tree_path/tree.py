from __future__ import annotations

from typing import Dict, List, Iterator, Callable, Union, Any
from pyconll.unit.sentence import Sentence
from pyconll.unit.token import Token

import pyconll

class Sequence(List[Dict[str, Any]]):
    def __init__(self, data_list : List[Dict[str, Any]]):#, id_tag = 'id', meta_data : Dict = None):
        super().__init__(data_list)
        self.sort(key=lambda tok : float(tok['id']))
    def before(self, id : str) -> Sequence:
        before_list = []
        for tok in self:
            if str(tok['id']) == id:
                break
            before_list.append(tok)
        return Sequence(before_list)
    def after(self, id : str) -> Sequence:
        after_list = []
        after_flag = False
        for tok in self:
            if str(tok[id]) == id:
                after_flag = True
                continue
            if after_flag:
                after_list.append(tok)
        return Sequence(after_list)
    def id_index(self, id : str) -> int:
        for tok, i in zip(self, range(0, len(self))):
            if tok['id'] == id:
                return i
        return -1

class Tree:
    def __init__(self, data : Dict[str, Dict|str], parent : Tree|None, children : List[Tree]):
        self.data = data
        self.parent = parent
        self._children = children
        self.str_from_conllu = True 
    def children_tokens(self) -> Sequence:
        return Sequence([t.data for t in self._children])
    def children(self) -> List[Tree]:
        return list(self._children)
    def traverse(self) -> Iterator[Tree]:
        yield self
        for child in self._children:
            for node in child.traverse():
                yield node
    def search(self, filter : Callable[[Tree], bool]) -> List[Tree]:
        return [n for n in self.traverse() if filter(n)]
    def ancestors(self) -> List[Tree]:
        node = self
        ancestors = []
        while node is not None:
            ancestors.append(node)
            node = node.parent
        return ancestors
    def depth(self) -> int:
        return len(self.ancestors()) - 1
    def root(self) -> Tree:
        r = self
        while r.parent:
            r = r.parent
        return r
    def projection(self) -> Sequence:
        tok_list = [n.data for n in self.traverse()]
        tok_list.sort(key=lambda tok : float(tok['id']))
        return Sequence(tok_list)
    def __str__(self):
        if self.str_from_conllu and self.data and 'id' in self.data and 'form' in self.data:
            return '(%s) %s' % (str(self.data['id']), str(self.data['form']))
        return str(self.data)
    def __repr__(self):
        return self.__str__()

