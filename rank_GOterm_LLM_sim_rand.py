from transformers import AutoTokenizer, AutoModel
from semanticSimFunctions import getSentenceEmbedding
from sklearn.metrics.pairwise import cosine_similarity
SapBERT_tokenizer = AutoTokenizer.from_pretrained('cambridgeltl/SapBERT-from-PubMedBERT-fulltext')
SapBERT_model = AutoModel.from_pretrained('cambridgeltl/SapBERT-from-PubMedBERT-fulltext')

import pandas as pd
from tqdm import tqdm
import pickle
import random 
random.seed(2023)
import os 
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', type=str, help='input file path')
parser.add_argument('--emb_file', type=str, help='embedding of all GO terms file path')
parser.add_argument('--topn', type=int, help='collect top n hits names and sim scores')
parser.add_argument('--output_file', type=str, help='output file path')
parser.add_argument('--background_file', type=str, help='all go sim background file path')

args = parser.parse_args()
input_file = args.input_file
emb_file = args.emb_file 
output_file = args.output_file 
background_file = args.background_file 


# load the go terms with llm name and analysis (1000 terms)
df = pd.read_csv(input_file, sep='\t')
df.set_index('GO', inplace=True)

# get a pool of GO names 
go_names_pool = df['Term_Description'].tolist()

# load the embeddings of all GO terms
with open(emb_file, 'rb') as handle:
    all_go_terms_embeddings_dict = pickle.load(handle)


# collect the similarity of llm and other go as a long list 
all_go_sim_list = []
df['LLM_name_GO_term_sim'] = None
df['sim_rank'] = 0
df['true_GO_term_sim_percentile'] = None

# add random GO term name and sim

df['random_GO_name'] = None
df['random_go_llm_sim'] = None
df['random_sim_rank'] = 0
df['random_sim_percentile'] = None

# add columns for top n hits and their similarity scores
n = args.topn # top n hits
df[f'top_{n}_hits'] = None
df[f'top_{n}_sim'] = None

def get_similarity(LLM_name_emb, GO_term):
    GO_emb = all_go_terms_embeddings_dict[GO_term] # the embedding of the actual GO term
    if GO_emb is None:
        raise Exception(f"Missing embedding for GO term: {GO_term}")
    #get other go terms emb
    other_GO_terms = all_go_terms_embeddings_dict.copy()
    other_GO_terms.pop(GO_term) # remove the actual GO term from the list
    GO_llm_sim = cosine_similarity(LLM_name_emb, GO_emb)[0][0]
    return GO_llm_sim, other_GO_terms


i = 0
for ind, row in tqdm(df.iterrows(), total=df.shape[0]):
        
    if row['true_GO_term_sim_percentile'] is None: # skip the ones that are already processed
        try: 
            GO_term = row['Term_Description'] # the actual GO term
            LLM_name = row['LLM Name'] # the LLM name
            # get llm name embedding
            LLM_name_emb = getSentenceEmbedding(LLM_name, SapBERT_tokenizer, SapBERT_model)
            
            GO_llm_sim, other_GO_terms = get_similarity(LLM_name_emb, GO_term)
            # print(GO_llm_sim)
            df.loc[ind, 'LLM_name_GO_term_sim'] = GO_llm_sim
            
            random_go_name = random.choice(go_names_pool)
            df.loc[ind, 'random_GO_name'] = random_go_name
            random_go_llm_sim, rand_other_GO_terms = get_similarity(LLM_name_emb, random_go_name)
            df.loc[ind, 'random_go_llm_sim'] = random_go_llm_sim
            
            top_n_hits = [(GO_llm_sim, GO_term)] + [(0, '')] * (n-1)  # Initialize list with true GO term and dummy tuples

            rank = 1
            for term, emb in other_GO_terms.items():
                # print(emb)
                GO_llm_sim_temp = cosine_similarity(LLM_name_emb, emb)[0][0]
                # print(GO_llm_sim_temp)
                all_go_sim_list.append(GO_llm_sim_temp) # collect all go term similarities
                
                min_score, _ = min(top_n_hits)  # Get the smallest score and corresponding term
                if GO_llm_sim_temp > min_score:
                    top_n_hits.remove((min_score, _))  # Remove this smallest score
                    top_n_hits.append((GO_llm_sim_temp, term))  # Append new score and term
                
                if GO_llm_sim_temp > GO_llm_sim:
                    rank += 1
            print(rank)

            df.loc[ind, 'sim_rank'] = rank
            # calculate the percentile of the actual GO term in the ranked list, reverse the percentile to have % of GO terms with lower sim
            percentile = 1- (rank/len(all_go_terms_embeddings_dict))
            df.loc[ind, 'true_GO_term_sim_percentile'] = percentile
            
            # save the top n hits and their similarity scores
            top_n_hits.sort(reverse=True)
            top_n_hits_str = '|'.join(str(hit) for _, hit in top_n_hits)
            df.loc[ind, f'top_{n}_hits'] = top_n_hits_str
            top_n_sim_str = '|'.join(str(score) for score, _ in top_n_hits)
            df.loc[ind, f'top_{n}_sim'] = top_n_sim_str
        except Exception as e:
            print(f"Error processing row {ind}: {str(e)}")
            continue  # skips the rest of this loop and moves to next row
        
        # calculate random sim rank and percentile
        rand_rank = 1
        for _, emb1 in rand_other_GO_terms.items():
            # print(emb)
            GO_llm_sim_temp = cosine_similarity(LLM_name_emb, emb1)[0][0]     
            if GO_llm_sim_temp > random_go_llm_sim:
                rand_rank += 1
        print(rand_rank)
        df.loc[ind, 'random_sim_rank'] = rand_rank
        # calculate the percentile of the actual GO term in the ranked list
        rand_percentile = 1-(rand_rank/len(all_go_terms_embeddings_dict))
        df.loc[ind, 'random_sim_percentile'] = rand_percentile
        
        
        i += 1
        if i % 10 == 0:
            df.to_csv(output_file, sep='\t', index=True)
            print(f'Saved progress after {i} rows.')
            with open(background_file, "w") as f:
                for sim in all_go_sim_list:
                    f.write(str(sim) + "\n")
                    
                    
df.to_csv(output_file, sep='\t', index=True) # index is the GO term, so set true

# save the list of all go term similarities
with open(background_file, "w") as f:
    for sim in all_go_sim_list:
        f.write(str(sim) + "\n")
        
print('DONE')
