import sys
import json
import numpy as np
from collections import Counter
sys.path.append('../code/src/')
from excel_toolkit import get_sheet_names, get_sheet_tarr


def locate_table(texts):
    lengths=[len([1 for x in text if x!='']) for text in texts]
    i=0
    for length in lengths:
        if length>1:
            break
        i+=1
    j=len(texts)-1
    for length in lengths[::-1]:
        if length>1:
            break
        j-=1
    assert i<=j
    return i,j

def locate_header(texts):
    data_st=[]
    for colx in range(texts.shape[1]):
        col_len=[len(texts[rowx,colx]) for rowx in range(50)]
        mu=np.mean(col_len)
        std=np.std(col_len,ddof=1)
        i=0
        for x in col_len:
            if mu-std<x<mu+std:
                break
            i+=1
        data_st.append(i)
    data_st=Counter(data_st).most_common(1)[0][0]
    return data_st

def locate_attribute(texts):
    for colx in range(texts.shape[1]):
        if len(set(['::'.join(x) for x in texts[:,:colx+1]]))==texts.shape[0]:
            return colx

    return texts.shape[1]-1



def rule_predict(fname):
    file_type = fname.rsplit('.', 1)[-1]
    assert file_type in {'csv', 'xls', 'xlsx'}
    snames = get_sheet_names(fname, file_type=file_type)

    result = dict()
    for sname in snames:
        tarr, _, _ = get_sheet_tarr(fname, sname, file_type=file_type)
        i, j = locate_table(tarr)
        tables = tarr[i:j + 1]
        data_st=locate_header(tables)
        attr_ed=locate_attribute(tables[data_st:])
        labels=np.empty(tarr.shape,np.int32)
        labels[:i]=3
        labels[j+1:]=5
        labels[i:i+data_st]=2
        labels[i+data_st+1:j+1,:attr_ed+1]=0
        labels[i+data_st+1:j+1,attr_ed+1:]=1
        result[sname] = dict(text=tarr.tolist(), labels=labels.tolist())

    return result


if __name__=='__main__':
    rule_predict('test1.xls')
    