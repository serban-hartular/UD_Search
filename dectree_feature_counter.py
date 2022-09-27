from typing import List

import sklearn.tree._tree as dectree
from collections import defaultdict
import pickle
from sklearn.tree import DecisionTreeClassifier

root = 0
distance_feat = 35

pred : DecisionTreeClassifier
with open('dectree0.p', 'rb') as handle: 
    pred = pickle.load(handle)

class NodeGroup:
    def __init__(self, index : int, min_dist:float, max_dist:float, count:int):
        self.index = index
        self.min_dist, self.max_dist, self.count = min_dist, max_dist, count
        self.other_feats = []

def split(ng : NodeGroup, tree : dectree.Tree) -> List[NodeGroup]:
    feature = tree.feature[ng.index]