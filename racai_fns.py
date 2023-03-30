
import json
import urllib.request
from typing import List

teprolin_url = 'http://relate.racai.ro:5000/'
teprolin_cmd = 'process'
data_prefix = "text="
operations = 'operations'


def get_relate_ops() -> List[str]:
    request = teprolin_url + operations
    with urllib.request.urlopen(request) as response: #, text.encode('utf-8')) as response:
        response = response.read()
    response = response.decode('utf-8')
    parse = json.loads(response)
    return parse['can-do']

def fix_diacritics(text : str) -> str:
    ops = get_relate_ops()
    op_name = 'diacritics-restoration'
    if op_name not in ops:
        raise Exception('Diacritics restoration not available!')
    text = data_prefix + text
    exec = 'exec='+op_name
    data = '&'.join([text, exec])
    # _data = text
    data = data.encode('utf-8')
    request = teprolin_url + teprolin_cmd
    with urllib.request.urlopen(request, data) as response: #, text.encode('utf-8')) as response:
        response = response.read()
    response = response.decode('utf-8')
    parse = json.loads(response)
    return parse['teprolin-result']['text']

import stanza_parse
def add_diacritics(articles_filename : str, outname : str):
    a_list = stanza_parse.articles_text_to_list(articles_filename)
    outfile = open(outname, 'w', encoding='utf-8')
    count = 0
    for src, text in a_list:
        dia_text = fix_diacritics(text)
        outfile.write(src)
        outfile.write(dia_text + '\n\n')
        count += 1
        print('%d of %d' % (count, len(a_list)))
    outfile.close()
