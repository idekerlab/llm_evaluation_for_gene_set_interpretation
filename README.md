# Evaluation of large language models for discovery of gene set function


## Description
Code associated with paper "Evaluation of large language models for discovery of gene set function" 

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
git clone git@github.com:idekerlab/llm_go_evaluation.git

cd llm_go_evaluation

pip install -r requirements.txt
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
### R requirements:
The code was developed using R 4.2.2.
To install the R packages required, please run R_requirements.R

```
Rscript R_requirements.R
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
	

	If need to download MSigDB, run [notebook](0.[omics%20set]ProcessMSigDB.ipynb). The notebook reads in the hallmark gene sets and saves them as individual .yaml files.
   

2. Query GPT-4 for names and supporting analysis 

    [GO gene set GPT-4 analysis](1.[GO%20set]Run_LLM_analysis.ipynb)

    [batch run 1000 GO terms using slurm](run_thousand_GO_llm_query.sh)

    [omic gene set GPT-4 analysis](1.[omics%20data]GenerateLLM_analysis.ipynb) and [omics gene set Enrichr](1B.[omics%20data]run_Enrichr.ipynb)

    ``` 
    ## will process from 1st to 5th terms
    START= 0
    END= 4 

    # Define input file and configuration
    INPUT = 'data/GO_term_analysis/toy_example.csv'
    CONFIG = './jsonFiles/GOLLMrun_config.json'

    source activate llm_eval
    # Run the Python script for the given range
    python query_llm_for_analysis.py --input $INPUT --start $START --end $END --config $CONFIG
    ```

3. Semantic Similarity evaluation of names

    [GO gene set analysis evalution](2.[GO%20set]Rank_LLM_GO_term_pair_sim.ipynb)

    [omic gene set analysis evaluation](2.[omics%20data]RunSemanticSimEval.ipynb)

    ```
    # get the ranking of similarities from the GO gene set analysis

    python rank_GOterm_LLM_sim_rand.py --input_file data/GO_term_analysis/LLM_processed_selected_1000_go_terms.tsv --emb_file data/all_go_terms_embeddings_dict.pkl --topn 50 --output_file data/GO_term_analysis/simrank_LLM_processed_selected_1000_go_terms.tsv --background_file data/GO_term_analysis/all_go_sim_scores.txt

    ```

4. Further evaluation of the performance: including gene set enrichment(GO set), and gene coverage in the analysis 

    [GO gene set enrichment analysis](3.[GO%20set]Evaluate_gene_set_similarity.ipynb) and counting [gene coverage](3B.[GO%20set]Count_genes_in_analysis.ipynb)


    ```
    # run hypergeometric test for p value and adjust p by BH

    hypergeometric_GO.py --input_file data/GO_term_analysis/simrank_LLM_processed_selected_1000_go_terms.tsv --topn 50 --output_file data/GO_term_analysis/simrank_pval_LLM_processed_selected_1000_go_terms.tsv

    ```

5. Development and assessment of the [citation module](4.Reference%20search%20and%20validation.ipynb)

6. Blinded study and data processing [Omics processing](5.[omics%20data]Analyse_Winner_Task2.ipynb)

7. Visualization of results 
    [extended data fig.1 + Fig.2](6.[GO%20set]Plot_GO_analysis_figs.ipynb)
    [extract sub hierarchy](6.[GO%20set]%20subhierarchy_GO_example.ipynb)
    [Fig.3 + extended data fig. 3](6.[omics%20set]GenerateOmicsFigures.ipynb)

## License

[MIT License](LICENSE)

## Citing

*Information to be provided.*


