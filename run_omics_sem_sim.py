from transformers import AutoTokenizer, AutoModel
from semanticSimFunctions import getSentenceEmbedding, getSentenceSimilarity, getNameSimilarities, getNameSimilarities_noExpertName

import pandas as pd
import numpy as np

## Load the sapbert model and tokenizer
SapBERT_tokenizer = AutoTokenizer.from_pretrained('cambridgeltl/SapBERT-from-PubMedBERT-fulltext')
SapBERT_model = AutoModel.from_pretrained('cambridgeltl/SapBERT-from-PubMedBERT-fulltext')

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--inputFile", type=str, help="Input file path")
parser.add_argument("--nameCol1", type=str, help="Column name for the first name")
parser.add_argument("--nameCol2", type=str, help="Column name for the second name")
args = parser.parse_args()


inputFile = args.inputFile
nameCol_LLM = args.nameCol1
nameCol_GO = args.nameCol2

reduced_LLM_genes_DF = pd.read_csv(inputFile, sep = "\t") 
reduced_LLM_genes_DF[nameCol_GO] = reduced_LLM_genes_DF[nameCol_GO].replace(np.nan, 'NaN')

## initialize the dataframe with dummy values
new_DF = reduced_LLM_genes_DF.copy()
new_DF['LLM_name_GO_term_sim'] = None

# skip rows with LLM Name as 'system of unrelated proteins'
filtered_DF = reduced_LLM_genes_DF[reduced_LLM_genes_DF[nameCol_LLM] != 'System of unrelated proteins'].reset_index(drop = True)
skipped_rows = reduced_LLM_genes_DF[reduced_LLM_genes_DF[nameCol_LLM] == 'System of unrelated proteins'].reset_index(drop = True)

names_DF = getNameSimilarities_noExpertName(filtered_DF, nameCol_LLM, nameCol_GO, SapBERT_tokenizer, SapBERT_model, "cosine_similarity")

# add back the rows with LLM Name as 'system of unrelated proteins'
names_DF = pd.concat([names_DF, skipped_rows]).reset_index(drop = True)


names_DF.to_csv(inputFile.replace(".tsv", "_simVals_DF.tsv"), sep = "\t", index = False)
print("Done with ", inputFile)
