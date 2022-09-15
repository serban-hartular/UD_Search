import itertools
from typing import List

from sklearn.calibration import CalibratedClassifierCV
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
from sklearn.ensemble import AdaBoostClassifier, BaggingClassifier, ExtraTreesClassifier, GradientBoostingClassifier, \
    RandomForestClassifier
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.mixture import BayesianGaussianMixture, GaussianMixture
from sklearn.naive_bayes import BernoulliNB, ComplementNB, GaussianNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.semi_supervised import LabelPropagation, LabelSpreading
from sklearn.svm import NuSVC, SVC

import training_data
import pandas as pd

# df = pd.DataFrame()
# for pdoc in training_data.iter_docs_from_conll('./cancan21-train-vpeonly.0.conllu'):
#     # for pair in generate_clause_pairs(pdoc):
#     #     print(pair)
#     df = pd.concat([df, training_data.generate_clause_pair_df(training_data.generate_clause_pairs(pdoc), pdoc)], ignore_index=True)

df = pd.read_pickle('./training_data.1.p')
# df = df_load.drop(columns=['prob0', 'prob1'])
X = df.drop(columns=['result', 'e_uid', 'a_uid'])
y = df['result']


from sklearn.linear_model import LogisticRegression, LinearRegression, PassiveAggressiveRegressor, Ridge, \
    PassiveAggressiveClassifier, RidgeClassifier, LogisticRegressionCV, SGDClassifier
from sklearn.tree import DecisionTreeClassifier, ExtraTreeClassifier
from sklearn.multioutput import MultiOutputClassifier

predictors = [AdaBoostClassifier, BaggingClassifier, BayesianGaussianMixture, BernoulliNB, 
CalibratedClassifierCV, ComplementNB,DecisionTreeClassifier,ExtraTreeClassifier,ExtraTreesClassifier,
GaussianMixture,GaussianNB,GaussianProcessClassifier,GradientBoostingClassifier,KNeighborsClassifier,
LabelPropagation,LabelSpreading,LinearDiscriminantAnalysis,LogisticRegression,LogisticRegressionCV,
MLPClassifier,MultinomialNB,NuSVC,QuadraticDiscriminantAnalysis,RandomForestClassifier,SGDClassifier,
SVC]
predictors = [LogisticRegression, LabelSpreading, DecisionTreeClassifier, BaggingClassifier]


def evaluate_predictor(predictor, X, y) -> (float, List[float]):
    predictor = predictor.fit(X, y)
    print(predictor.score(X,y))
    y_pred = predictor.predict_proba(X)
    y_pred_df = pd.DataFrame(y_pred, columns=['prob0', 'prob1'])
    df_pred = pd.concat([df, y_pred_df], axis=1)
    correct = df_pred[df_pred['result']==1]
    correct = {t[0]:t[1] for t in zip(correct['e_uid'], correct['a_uid'])}
    ellipsis_ids = [k for k in correct.keys()]
    sum, count = 0, 0
    good_scores = []
    for e_uid in ellipsis_ids:
        df_part = df_pred[df_pred['e_uid']==e_uid]
        scores = [z for z in zip(df_part['a_uid'], df_part['prob1'])]
        scores.sort(key=lambda t: -t[1])
        good_antecedent = [c for c in scores if c[0] == correct[e_uid]]
        if not good_antecedent:
            print('Good antecedent not found for ' + e_uid)
            continue
        good_antecedent = good_antecedent[0]
        i = scores.index(good_antecedent)
        if i != 0: # report 
            print('\t'.join([str(i) for i in [e_uid] + list(good_antecedent) + list(scores[0])]))
        sum += (1 if i == 0 else 0)
        count += 1
        if i == 0:
            good_scores.append(scores[0][1])
    return sum/count, good_scores

# predictor_dict = {}
# for predictor in predictors:
#     predictor_dict[predictor] = evaluate_predictor(predictor, X, y)
# print(predictor_dict)

predictor = DecisionTreeClassifier() #class_weight={0:1.0, 1:1.0})
print('e_uid\ta_uid good\tprob_good\ta_uid guessed\tprob_guessed')
a, b = evaluate_predictor(predictor, X, y)
