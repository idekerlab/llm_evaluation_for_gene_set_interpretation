
# https://huggingface.co/michiyasunaga/BioLinkBERT-large
# https://medium.com/@adriensieg/text-similarities-da019229c894

import torch
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


def getSentenceEmbedding(sentence, tokenizer, model):
    # Tokenize sentences
    encoded_input = tokenizer(sentence, padding=True, truncation=True, return_tensors='pt')

    # Compute token embeddings
    with torch.no_grad():
        model_output = model(**encoded_input)
        
    # Perform pooling. In this case, mean pooling.
    sentence_embedding = mean_pooling(model_output, encoded_input['attention_mask'])
    
    return sentence_embedding


def getSentenceSimilarity(sentence1, sentence2, tokenizer, model, simMetric):
    sentence1_embedding = getSentenceEmbedding(sentence1, tokenizer, model)
    sentence2_embedding = getSentenceEmbedding(sentence2, tokenizer, model)
    
    if simMetric == "cosine_similarity":
        sentenceSim = cosine_similarity(sentence1_embedding, sentence2_embedding)[0][0]
    # ToDo: add other simMetrics
    #elif simMetric == "cosine_similarity_primitive": # use primitive operations
   #     sentenceSim = np.dot(sentence1_embedding, sentence2_embedding)/(norm(sentence1_embedding)*norm(sentence2_embedding))
    
    return sentenceSim, sentence1_embedding, sentence2_embedding


def getNameSimilarities_noExpertName(names_DF, LLM_name_col, GO_name_col, tokenizer, model, simMetric, epsilon= 0.05):
    """
    names_DF: data frame with columns containing the names from various sources (each row is a different gene set)
    *_name_col: strings of column names """
    
    
    ## Initialize columns
    names_DF['LLM_name_GO_term_sim'] = None;
    
    nSystems = names_DF.shape[0]
    
    for systemInd in range(nSystems):
        print(systemInd)
        systemRow = names_DF.iloc[systemInd]
        LLM_name = systemRow[LLM_name_col]
        GO_term = systemRow[GO_name_col]  

        LLM_name_GO_term_sim, LLM_name_embedding, GO_term_embedding =  getSentenceSimilarity(LLM_name, GO_term, 
                                                     tokenizer, model,
                                                     simMetric)

        names_DF.loc[systemInd, 'LLM_name_GO_term_sim']  = LLM_name_GO_term_sim

    return names_DF
    

def getNameSimilarities(names_DF, LLM_name_col, GO_name_col, human_name_col, tokenizer, model, simMetric, epsilon= 0.05):
    """
    names_DF: data frame with columns containing the names from various sources (each row is a different gene set)
    *_name_col: strings of column names """
    
    
    ## Initialize columns
    names_DF['LLM_name_human_name_sim'] = None;
    names_DF['GO_term_human_name_sim'] = None;
    names_DF['winner'] = None;
    
    nSystems = names_DF.shape[0]
    
    for systemInd in range(nSystems):
        print(systemInd)
        systemRow = names_DF.iloc[systemInd]
        LLM_name = systemRow[LLM_name_col]
        human_name = systemRow[human_name_col] 
        GO_term = systemRow[GO_name_col]  

        LLM_name_human_name_sim, LLM_name_embedding, human_name_embedding =  getSentenceSimilarity(LLM_name, human_name, 
                                                     tokenizer, model,
                                                     simMetric)

        GO_term_human_name_sim, GO_term_embedding, human_name_embedding =  getSentenceSimilarity(GO_term, human_name, 
                                                     tokenizer, model,
                                                     simMetric)

        names_DF.loc[systemInd, 'LLM_name_human_name_sim']  = LLM_name_human_name_sim
        names_DF.loc[systemInd, 'GO_term_human_name_sim']  = GO_term_human_name_sim


        if (GO_term_human_name_sim < 0.4) and (LLM_name_human_name_sim < 0.4):
            names_DF.loc[systemInd, 'winner']  = "Neither"  
        elif abs(GO_term_human_name_sim - LLM_name_human_name_sim) <= epsilon:
            names_DF.loc[systemInd, 'winner']  = "Tied"   
        elif LLM_name_human_name_sim > GO_term_human_name_sim:
            names_DF.loc[systemInd, 'winner']  = "LLM"
        elif GO_term_human_name_sim > LLM_name_human_name_sim - epsilon:
            names_DF.loc[systemInd, 'winner']  = "GO"
        else:
            print("Impossible!")

        # print((LLM_name_human_name_sim, GO_term_human_name_sim))
    
    return names_DF
    