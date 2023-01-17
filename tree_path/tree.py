from __future__ import annotations

import json
from typing import Dict, List, Iterator, Callable, Union, Any, Set, Tuple
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

def _sets2lists(d : Dict) -> Dict:
    d2 = {}
    for k,v in d.items():
        if isinstance(v, set):
            d2[k] = list(v)
        elif isinstance(v, dict):
            d2[k] = _sets2lists(v)
        else:
            d2[k] = v
    return d2

def _lists2sets(d : Dict) -> Dict:
    d2 = {}
    for k,v in d.items():
        if isinstance(v, list):
            d2[k] = set(v)
        elif isinstance(v, dict):
            d2[k] = _lists2sets(v)
        else:
            d2[k] = v
    return d2


class Tree:
    def __init__(self, data : Dict[str, Dict|str], parent : Tree|None, children : List[Tree]):
        self._data = data
        self.parent = parent
        self._children = children
        self.str_from_conllu = True 
    def data(self, path:str|List[str] = None) -> str|Dict|Set|None:
        if not path:
            return self._data
        if isinstance(path, str):
            path = path.split('.')
        d = self._data
        for key in path:
            if key in d:
                d = d[key]
            else:
                return None
        return d
    def sdata(self, path:str|List[str]) -> str:
        """data(path) as string. Sets, lists, tuples are returned joined by ',' """
        data = self.data(path)
        if not data: return ''
        if isinstance(data, (Set, List, Tuple)):
            return ','.join(data)
        return str(data)
        
    def _path_to_dict_and_key(self, path:str|List[str], create_if_absent : bool) -> (Dict, str):
        if isinstance(path, str):
            path = path.split('.')
        d = self._data
        for key in path[:-1]:
            if key in d:
                d = d[key]
            elif create_if_absent:
                d[key] = dict()
                d = d[key]
            else:
                return None, None
        key = path[-1]
        return d, key

    def assign(self, path: str | List[str], value: str | Set, create_if_absent : bool = True) -> bool:
        d, key = self._path_to_dict_and_key(path, create_if_absent)
        if d is None: return False
        if key in d or create_if_absent:
            d[key] = value
            return True
        return False
    def remove(self, path: str | List[str]) -> bool:
        d, key = self._path_to_dict_and_key(path, False)
        if d is None: return False
        if key in d:
            d.pop(key)
            return True
        return False

                
    def children_tokens(self) -> Sequence:
        return Sequence([t._data for t in self._children])
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
        tok_list = [n._data for n in self.traverse()]
        tok_list.sort(key=lambda tok : float(tok['id']))
        return Sequence(tok_list)
    def projection_nodes(self) -> List[Tree]:
        node_list = [n for n in self.traverse()]
        node_list.sort(key=lambda n : float(n.data('id')))
        return node_list
    def __str__(self):
        if self.str_from_conllu and self._data and 'id' in self._data and 'form' in self._data:
            return '(%s) %s' % (str(self._data['id']), str(self._data['form']))
        return str(self._data)
    def __repr__(self):
        return self.__str__()
    def to_jsonable(self) -> Dict:
        json_dict = {'_data': _sets2lists(self._data),
                     'children':[c.to_jsonable() for c in self.children()]}
        return json_dict
    @staticmethod
    def from_jsonable(json_dict : Dict) -> Tree:
        data = _lists2sets(json_dict['_data'])
        node = Tree(data, None, [])
        for child_data in json_dict['children']:
            child = Tree.from_jsonable(child_data)
            child.parent = node
            node._children.append(child)
        return node
    
