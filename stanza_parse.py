from typing import Dict

import stanza
from stanza.utils.conll import CoNLL

# stanza.download('ro') # download Romanian model
nlp = None
def init_nlp():
    global nlp
    nlp = stanza.Pipeline('ro') # initialize Romanian neural pipeline


def parse_and_dump(filename : str, outfile : str, src_prefix, parser = None):
    global nlp
    if parser is None:
        parser = nlp
    with open(filename, 'r', encoding='utf8') as handle:
        lines = handle.readlines()
    article_list = []
    article = ('', '')
    for line in lines:
        if line[0] == '#':
            if article[0] or article[1]:
                article_list.append(article)
            article = (line, '')
        else:
            article = (article[0], article[1] + line)
    # last article
    if article[0] or article[1]:
        article_list.append(article)

    outfile = open(outfile, 'w', encoding='utf8')
    article_index = 0
    for (src, text) in article_list:
        outfile.write('# doc_src = %s\n' % src.strip())
        outfile.write('# newdoc id = %s-%s\n' % (src_prefix, str(article_index).zfill(4)))
        print('# doc_src = %s\n' % src.strip())
        print('# newdoc id = %s-%s' % (src_prefix, str(article_index).zfill(4)))
        doc = parser(text)
        conllu = CoNLL.doc2conll(doc)
        conllu = '\n'.join(['\n'.join(s) + '\n' for s in conllu])
        outfile.write(conllu + '\n')
        article_index += 1
    outfile.close()

bad_diacritics = {'ş':'ș', 'Ş':'Ș', 'ţ':'ț', 'Ţ':'Ț', 'ã':'ă'}

def replace_chars(infile : str, outfile : str, char_dict : Dict[str, str]):
    if infile == outfile:
        raise Exception('infile and outfile have same name')
    infile = open(infile, 'r', encoding='utf8')
    outfile = open(outfile, 'w', encoding='utf8')
    while True:
        line = infile.readline()
        if not line:
            break
        for k,v in char_dict.items():
            line = line.replace(k, v)
        outfile.write(line)
    outfile.close()
    infile.close()

def replace_sentence_ids(conllu_file : str, outfile : str):
    if conllu_file == outfile:
        raise Exception('infile and outfile have same name')
    conllu_file = open(conllu_file, 'r', encoding='utf8')
    outfile = open(outfile, 'w', encoding='utf8')
    doc_id = ''
    sent_id = ''
    while True:
        line = conllu_file.readline()
        if not line:
            break
        if line.startswith('# newdoc id ='):
            [prefix, doc_id] = line.split('=',1)
            doc_id = doc_id.strip()
        if line.startswith('# sent_id ='):
            [prefix, sent_id] = line.split('=',1)
            sent_id = sent_id.strip()
            outfile.write(prefix + '= ' + doc_id + '-' + sent_id.zfill(4) + '\n')
        else:
            outfile.write(line)
    outfile.close()
    conllu_file.close()

