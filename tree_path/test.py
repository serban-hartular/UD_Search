
from tree import Tree
from search import Search

src = """
# sent_id = train-6814
# text = Dacă zidul nu era drept, ochiul acela se tulbura, fărâmau și o luau de la capăt.
1	Dacă	dacă	SCONJ	Csssp	Polarity=Pos	5	mark	_	_
2	zidul	zid	NOUN	Ncmsry	Case=Acc,Nom|Definite=Def|Gender=Masc|Number=Sing	5	nsubj	_	_
3	nu	nu	PART	Qz	Polarity=Neg	5	advmod	_	_
4	era	fi	VERB	Vaii3s	Mood=Ind|Number=Sing|Person=3|Tense=Imp|VerbForm=Fin	5	cop	_	_
5	drept	drept	ADV	Rgp	Degree=Pos	10	advcl	_	SpaceAfter=No
6	,	,	PUNCT	COMMA	_	5	punct	_	_
7	ochiul	ochi	NOUN	Ncmsry	Case=Acc,Nom|Definite=Def|Gender=Masc|Number=Sing	10	nsubj	_	_
8	acela	acela	DET	Dd3msr---o	Case=Acc,Nom|Gender=Masc|Number=Sing|Person=3|Position=Postnom|PronType=Dem	7	det	_	_
9	se	sine	PRON	Px3--a--------w	Case=Acc|Person=3|PronType=Prs|Reflex=Yes|Strength=Weak	10	expl:pv	_	_
10	tulbura	tulbura	VERB	Vmii3s	Mood=Ind|Number=Sing|Person=3|Tense=Imp|VerbForm=Fin	0	root	_	SpaceAfter=No
11	,	,	PUNCT	COMMA	_	12	punct	_	_
12	fărâmau	fărâma	VERB	Vmii3p	Mood=Ind|Number=Plur|Person=3|Tense=Imp|VerbForm=Fin	10	conj	_	_
13	și	și	CCONJ	Crssp	Polarity=Pos	15	cc	_	_
14	o	el	PRON	Pp3fsa--------w	Case=Acc|Gender=Fem|Number=Sing|Person=3|PronType=Prs|Strength=Weak	15	obj	_	_
15	luau	lua	VERB	Vmii3p	Mood=Ind|Number=Plur|Person=3|Tense=Imp|VerbForm=Fin	10	conj	_	_
16	de	de	ADP	Spsa	AdpType=Prep|Case=Acc	18	case	_	_
17	la	la	ADP	Spsa	AdpType=Prep|Case=Acc	18	fixed	_	OrigHead=16
18	capăt	capăt	NOUN	Ncms-n	Definite=Ind|Gender=Masc|Number=Sing	15	xcomp	_	SpaceAfter=No
19	.	.	PUNCT	PERIOD	_	10	punct	_	_

"""

tree = Tree.from_conllu(src)
expr = Search('.//[upos=VERB]/[upos=PRON,NOUN]/[upos=ADP,DET]')
result = expr.find(tree)
print(result)