import sys
import argparse
import torch
import json
import numpy as np

sys.path.append('../code/src/')

from models import ClassificationModel, CEModel, FeatEnc
from excel_toolkit import get_sheet_names, get_sheet_tarr, get_feature_array

def load(ce_model_path, fe_model_path, cl_model_path, w2v_path, vocab_size, infersent_source, infersent_model,device='cpu'):
    sys.path.append(infersent_source)
    from helpers import Preprocess, SentEnc, label2ind

    mode = 'ce+f'
    ce_dim = 512
    senc_dim = 4096
    window = 2
    f_dim = 43
    fenc_dim = 40
    n_classes = 6
    if device != 'cpu': torch.cuda.set_device(device)

    ce_model = CEModel(senc_dim, ce_dim // 2, window * 4)
    ce_model = ce_model.to(device)
    fe_model = FeatEnc(f_dim, fenc_dim)
    fe_model = fe_model.to(device)
    cl_model = ClassificationModel(ce_dim + fenc_dim, n_classes).to(device)

    ce_model.load_state_dict(torch.load(ce_model_path, map_location=device))
    fe_model.load_state_dict(torch.load(fe_model_path, map_location=device))
    cl_model.load_state_dict(torch.load(cl_model_path, map_location=device))

    label2ind = ['attributes', 'data', 'header', 'metadata', 'derived', 'notes']

    print('loading word vectors...')
    senc = SentEnc(infersent_model, w2v_path,
                   vocab_size, device=device, hp=False)
    prep = Preprocess()
    return senc,cl_model, ce_model, fe_model, senc, mode, device, label2ind

def process(fname,models):
    from test_cl import predict_labels
    senc,cl_model, ce_model, fe_model, senc, mode, device, label2ind=models
    file_type=fname.rsplit('.',1)[-1]
    assert file_type in {'csv','xls','xlsx'}
    snames = get_sheet_names(fname, file_type=file_type)

    result = dict()
    for sname in snames:
        tarr, n, m = get_sheet_tarr(fname, sname, file_type=file_type)
        ftarr = get_feature_array(fname, sname, file_type=file_type)
        print(ftarr)
        table = dict(table_array=tarr, feature_array=ftarr)

        sentences = set()
        for row in tarr:
            for c in row:
                sentences.add(c)
        senc.cache_sentences(list(sentences))

        labels, probs = predict_labels(table, cl_model, ce_model, fe_model, senc, mode, device)
        probs = np.exp(probs)
        labels = np.vectorize(lambda x: label2ind[x])(labels)
        result[sname] = dict(text=tarr.tolist(), labels=labels.tolist(), labels_probs=probs.tolist())
    return result

def main(fname, ce_model_path, fe_model_path, cl_model_path, w2v_path, vocab_size, infersent_source, infersent_model,device='cpu'):
    models=load(ce_model_path, fe_model_path, cl_model_path, w2v_path, vocab_size, infersent_source, infersent_model,device)
    result=process(fname,models)
    return result

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='processing inputs.')
    parser.add_argument('--file', type=str,
                        help='path to the .xls spreadsheet.')
    parser.add_argument('--ce_model', type=str,
                        help='path to the trained cell embedding model.')
    parser.add_argument('--fe_model', type=str,
                        help='path to the trained feature encoding model.')
    parser.add_argument('--cl_model', type=str,
                        help='path to the trained classification model.')
    parser.add_argument('--w2v', type=str,
                        help='path to the glove embeddings.')
    parser.add_argument('--vocab_size', type=int,
                        help='w2v vocab size.')
    parser.add_argument('--infersent_model', type=str,
                        help='path to the infersent model.')
    parser.add_argument('--infersent_source', type=str,
                        help='path to the infersent source code.')
    parser.add_argument('--out', type=str,
                        help='path to the output json file.')
    
    args = parser.parse_args()
    
    res = main(args.file, args.ce_model, args.fe_model, args.cl_model, args.w2v, args.vocab_size, args.infersent_source, args.infersent_model)
    json.dump(res, open(args.out, 'w'))
    