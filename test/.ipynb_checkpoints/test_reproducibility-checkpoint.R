

setwd("~/Desktop/projects/llm_go_evaluation/")
library(plyr)
library(tidyverse)

library(text)
library(lsa)
#textrpp_install()
#textrpp_initialize(save_profile = TRUE)


analyses_1_DF = read_delim("data/merged_new_LLM_GSEA_simVals_refs.txt", delim = "\t")
analyses_2_DF = read_delim("data/merged_subset_LLM_GSEA_simVals_refs.txt",  delim = "\t")

combined_analyses_1_2_DF = inner_join(analyses_1_DF %>%
                                        select(`DataSet`, `Human Name`, `GenesFixed`, `LLM Name`, `LLM Analysis`),
                                      analyses_2_DF %>%
                                        select(`Human Name`, `LLM Name`, `LLM Analysis`), 
                                      by = "Human Name")

# write_delim(x = combined_analyses_1_2_DF, file = "test/combined_analyses_1_2_DF.txt", delim = "\t")


getTextEmbedding = function(textStr){
  embeddingTibble = textEmbed(texts = textStr, 
                              model = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext",
                              aggregation_from_layers_to_tokens = "mean",
                              aggregation_from_tokens_to_texts = "mean")
  
  embeddingsArr = unlist(array(embeddingTibble$texts$texts))
  
  return(embeddingsArr)
}


combined_analyses_1_2_sim_DF = combined_analyses_1_2_DF %>%
  rowwise() %>%
  mutate(NameSim =cosine(getTextEmbedding(`LLM Name.x`), getTextEmbedding(`LLM Name.y`))[[1]])
         
combined_analyses_1_2_simText_DF = combined_analyses_1_2_sim_DF  %>%
  rowwise() %>%
  mutate(textSim =cosine(getTextEmbedding(`LLM Analysis.x`), getTextEmbedding(`LLM Analysis.y`))[[1]])

write_delim(x = combined_analyses_1_2_simText_DF,
            file = "test/combined_analyses_1_2_simText_DF.txt", delim = "\t")


