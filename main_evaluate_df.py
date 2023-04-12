import pickle
from typing import List, Tuple

import antecedent_detection.antecedent_guess

print('New Main DF')
print('Loading libraries')

import pandas as pd
from sklearn.tree import DecisionTreeClassifier

import tree_path as tp
import annotations as an
import word_modality as wm


from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import AdaBoostClassifier, BaggingClassifier, ExtraTreesClassifier, GradientBoostingClassifier, \
    RandomForestClassifier
from sklearn.naive_bayes import ComplementNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.semi_supervised import LabelPropagation, LabelSpreading
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegressionCV, LinearRegression

print('Loading data')
df = pd.read_csv('./model_data_files/df-20230411-noduplicate.csv', sep='\t', encoding='utf-8')
print(df.columns, 'y' in df.columns)

print('Loading models')
model_names = ['BaggingClassifier', 'MLPClassifier', 'ExtraTreesClassifier', 'RandomForestClassifier'
               ]
model_dict = {}
for name in model_names:
    with open('./antecedent_models/' + name + '.p', 'rb') as handle:
        model_dict[name] = pickle.load(handle)

print('Evaluating')
model, score, labels = model_dict['BaggingClassifier']
good_antecedents = antecedent_detection.antecedent_guess.extract_correct_antecedents_from_df(df)
guessed_antecedents = antecedent_detection.antecedent_guess.extract_proba_antecedents_from_df(
    antecedent_detection.antecedent_guess.antecedent_proba_to_df(df, model, labels)
)
good_guesses = {k:v for k,v in guessed_antecedents.items() if good_antecedents[k].matches(v)}
bad_guesses = {k:v for k,v in guessed_antecedents.items() if not good_antecedents[k].matches(v)}