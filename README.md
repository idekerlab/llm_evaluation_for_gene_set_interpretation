# Evaluation of large language models for discovery of gene set function


## Description
Code associated with paper ["Evaluation of large language models for discovery of gene set function"](https://www.nature.com/articles/s41592-024-02525-x)

## Dependencies
### Set up an environment
```
conda create -n llm_eval python=3.11.5
```
### Set up an environment variable to store GPT-4 API key 

```
conda activate llm_eval
conda env config vars set OPENAI_API_KEY="<your api key>" 
conda deactivate  # reactivate 

conda activate llm_eval
echo $OPENAI_API_KEY # make sure the key setup 

%python
import os
import openai
 
openai.api_key = os.environ["OPENAI_API_KEY"]
```

From OpenAI website for [the best practice for API key safety](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety) 

### Python requirements:
The code was developed using Python 3.11.5.

```
git clone git@github.com:idekerlab/llm_evaluation_for_gene_set_interpretation.git

cd llm_evaluation_for_gene_set_interpretation

pip install -r requirements.txt
```

UPDATE 12/17/2024: openai package requires an httpx version that is not compatible with their function, manually downgrade httpx to 0.27.2 until OpenAI fixed their bug

```
pip uninstall httpx
pip install httpx==0.27.2
```

DDOT is required for downloading GO and can be installed in one of two ways:

To install DDOT by downloading the zip file of the source tree:
```
wget https://github.com/idekerlab/ddot/archive/refs/heads/python3.zip
unzip python3.zip
cd ddot-python3
python setup.py bdist_wheel
pip install dist/ddot*py3*whl
```

To install DDOT by cloning the repo:
```
git clone --branch python3 https://github.com/idekerlab/ddot.git
cd ddot
python setup.py bdist_wheel
pip install dist/ddot*py3*whl
```

## Documentation
The notebooks are numbered according to the evaluation steps 

0. Data Preperation (this step can be omitted for testing purposes)

   The data is already in the [data directory](./data) (refer to the README in this directory for detail information about the data)
   
   If need to download GO, follow the code below: 
    ```
    ## download and parse GO_BP terms
    outdir = 'data/GO_BP/'
    namespace = 'biological_process'
    python process_the_gene_ontology.py $outdir --namespace $namespace 
    ```
    and the [notebook](0.[Prep%20GO]Download_and_parse_GO.ipynb) for parsing GO terms
	
    The addition of contamination to the gene set is filed in [this notebook](0.%20[GO%20set]add_random_contamination.ipynb)

	If need to download Omics data, run [notebook](0.[Omics_revamped]_ProcessOmicsData.ipynb). The notebook processes the omics data and saves them into a tab delimited text file.
   

1. Query GPT-4 for names and supporting analysis and run functional enrichment

   GO gene set GPT-4 analysis is stored in [Run_LLM_analysis](1.[GO%20set]Run_LLM_analysis.ipynb)

   GO gene set analysis with [different models](1A.[GO%20set]Compare_models.ipynb)

   Batch run 1000 GO terms using [slurm job](thousandGOsets_GPT4Run.sh) with the [parameter file](thousandGOsets_GPT4Run_params.txt) 


    [omic gene set GPT-4 analysis](1A.[Omics_revamped]GenerateLLM_analysis.ipynb) and [omics gene set gProfiler](1B-2.[Omics_revamped]run_gProfiler.ipynb)

  

    ``` 
    ## example code to process from 1st to 5th terms in the table
    # run in the command line  

    input_file='data/GO_term_analysis/toy_example.csv' #input table path
    config='./jsonFiles/GOLLMrun_config.json' #configuration file 
    set_index='GO' #index of the table
    gene_column='Genes' #name of the gene list column
    start=0
    end=5   
    out_file='data/GO_term_analysis/LLM_processed_toy_example_gpt_4' #output path prefix

    source activate llm_eval
    # Run the Python script for the given range
    python query_llm_for_analysis.py --config $config \
                --initialize \
                --input $input_file \
                --input_sep  ','\
                --set_index $set_index \
                --gene_column $gene_column\
                --gene_sep ' ' \
                --start $start \
                --end $end \
                --output_file $out_file
    ```

2. Semantic Similarity evaluation of names

    [GO gene set analysis evalution](2.[GO%20set]Rank_LLM_GO_term_pair_sim.ipynb)

    ```
    # get the ranking of similarities from the GO gene set analysis

    python rank_GOterm_LLM_sim_rand.py --input_file ./data/GO_term_analysis/LLM_processed_toy_example_w_contamination_gpt_4.tsv --emb_file data/all_go_terms_embeddings_dict.pkl --topn 3 --output_file ./data/GO_term_analysis/simrank_LLM_processed_toy_example.tsv --background_file data/GO_term_analysis/all_go_sim_scores_toy.txt
    ```

3. Further evaluation of the performance: model comparison evaluation, gene set functional enrichment, and gene set similarity comparison
    **Evaluation Task 1 related**
    
    *Model Comparison*

    Analysis related to Fig. 2A
    [Compare the semantic similarities between models](3A.[model%20compare]compare_semantic_similarity.ipynb)

   Analysis related to Fig. 3
    [Run GO gene set functional enrichment for control](3A.[model%20compare]functional_enrichment_analysis_control.ipynb)

   [Compare the confidence score between real, contaminated, and random gene sets](3B-2.[model%20compare]Check_confidence_scoring_metrics.ipynb)

    *Check broader concepts of the LLM names*
   
    Analysis for Fig. 2d
   
    [Analysis for whether the best matching GO term is a broader concept as the queried term](3C.[GO%20set]Evaluate_gene_set_similarity.ipynb)

    **Evaluation Task 2 related**
    [Count genes supporting LLM name](2A.[Omics_revamped]_CountSupportingGenes.ipynb), then [calculate LLM name Jaccard Index](2B.[Omics_revampled]Calculate_LLM_JI.ipynb)

    Analysis related to Fig.4 

    [Omics data naming evaluation](3A.[omics_revamped]Analyze_gprofiler_annotation.ipynb)

    Evaluate LLM name matching with any significantly enriched GO term name, use [this notebook](3B[Omics_revamped]Compare_enriched_GO_and_LLM_name_sim.ipynb)




6. Development and assessment of the [citation module](4.Reference%20search%20and%20validation.ipynb)


7. Quantification of citation module [check citation module](5.Quantify%20reference%20checking.ipynb)

8. Visualization of results

    [extended data fig.1 + Fig.2 + Fig.3](6.[GO%20set]Plot_GO_analysis_figs.ipynb)
   
    [extract sub hierarchy (Fig.2e)](6.[GO%20set]%20subhierarchy_GO_example.ipynb)
   
    [Omics figures (Fig 4, Extended Data Fig.5)](6B.[Omics_revamped]GenerateOmicsFigures.ipynb)

## License

[MIT License](LICENSE)

## Citing

Hu, M., Alkhairy, S., Lee, I. et al. Evaluation of large language models for discovery of gene set function. Nat Methods (2024). https://doi.org/10.1038/s41592-024-02525-x


