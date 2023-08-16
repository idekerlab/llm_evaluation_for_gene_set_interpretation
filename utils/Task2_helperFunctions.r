
getHumanConsensus = function(Winner_human1,Winner_human2,  Winner_human3, OverridingDecision = NaN ){
  # dataframe row 
  if (!is.na(OverridingDecision)){
    humanConsensus = OverridingDecision
  } else {
    winnerList =  c(Winner_human1, Winner_human2,Winner_human3 )
    sortedCounts = sort(table(winnerList), decreasing = TRUE)
    if  (sortedCounts[1] ==1){
      # all are tied
        if (("Tied" %in% winnerList) & ("Neither" %in% winnerList) ){
            humanConsensus = "Neither" # Neither is stronger than Tied
      } else if ("Tied" %in% winnerList){
        humanConsensus = "Tied"
      } else if ("Neither" %in% winnerList){
        humanConsensus = "Neither"
      } else {
        humanConsensus = "need help"
      }
      
    } else {
      
   # print(sortedCounts)
      humanConsensus = names(sortedCounts[1] )
      
    }
  }
  
  return(humanConsensus)
}

getSetSize = function(genesStr){
    geneList = str_split(string = genesStr, pattern = "[, ]")[[1]]
    return(length(geneList))
}

getGSEAGeneCount = function(systemGenes, GSEA_Genes){
    systemGenesList = str_split(string = systemGenes, pattern = " ")[[1]];
    GSEA_GenesList = str_split(string = GSEA_Genes, pattern = ";")[[1]];
    return(length(intersect(systemGenesList, GSEA_GenesList)))
    }
    

getLLMGeneCount  = function(GenesFixed, LLM_Analysis){
    systemGenesList = str_split(string = GenesFixed, pattern = " ")[[1]];
    
    n_LLMGenes = to_vec(for(systemGene in systemGenesList) str_detect(string = LLM_Analysis, pattern = systemGene)) %>%
           sum()
        
    return(n_LLMGenes)


    }