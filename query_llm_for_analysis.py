import argparse
import pandas as pd
import json 
from utils.openai_query import openai_chat
from utils.prompt_factory import make_user_prompt
from tqdm import tqdm
import os
import openai


# Add argument parsing
parser = argparse.ArgumentParser(description='Process range of gene sets.')
parser.add_argument('--input', type=str, required=True, help='Path to input csv with gene sets')
parser.add_argument('--start', type=int, required=True, help='Start index for gene set range')
parser.add_argument('--end', type=int, required=True, help='End index for gene set range')
parser.add_argument('--config', type=str, required=True, help='Config file for LLM')
args = parser.parse_args()

config_file = args.config
input_file = args.input
ind_start = args.start
ind_end = args.end

with open(config_file) as json_file:
    config = json.load(json_file)

#load openai key, context, and model used 
openai.api_key = os.environ['OPENAI_API_KEY']

context = config['CONTEXT']
gpt_model = config['GPT_MODEL']
temperature = config['TEMP']
max_tokens = config['MAX_TOKENS']
rate_per_token = config['RATE_PER_TOKEN']
LOG_FILE = config['LOG_NAME'] +f'{ind_start}_{ind_end}_log.json'
DOLLAR_LIMIT = config['DOLLAR_LIMIT']


raw_df = pd.read_csv(input_file, sep = ',')

df = raw_df.iloc[ind_start:(ind_end+1)] # +1 because python indexing is exclusive
df.reset_index(drop=True, inplace=True)
# set the go term as the index
df.set_index('GO', inplace=True)
# Initialize columns for LLM name and analysis
df['LLM Name'] = None
df['LLM Analysis'] = None

llm_response_dict = {}
# Only process the specified range of genes
i = 0
for go_term, row in tqdm(df.iterrows(), total=df.shape[0]):
    term_genes = row['Genes']
    genes = term_genes.split()
    prompt = make_user_prompt(genes)
    analysis = openai_chat(context, prompt, gpt_model,temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT)
    
    if analysis:
        llm_name = analysis.split("\n")[0].replace("Process: ", "")
        df.loc[go_term, 'LLM Name'] = llm_name
        
        llm_analysis = analysis.split('\n', 2)[2]
        df.loc[go_term, 'LLM Analysis'] = llm_analysis

        llm_response_dict[go_term] = analysis
    else:
        print(f'No analysis for {go_term}')
        df.loc[go_term, 'LLM Name'] = None
        df.loc[go_term, 'LLM Analysis'] = None
        llm_response_dict[go_term] = 'NO ANALYSIS'
    i += 1
    if i % 10 == 0:
        print(f'Processed {i} terms, saving...')
        with open(f'data/GO_term_analysis/LLM_response_go_terms_{ind_start}_{ind_end}.json', 'w') as fp:
            json.dump(llm_response_dict, fp)
    
        df.to_csv(f'data/GO_term_analysis/LLM_processed_selected_go_terms_{ind_start}_{ind_end}.tsv', sep='\t', index=True) # need to keep the index because it is the GO term


with open(f'data/GO_term_analysis/LLM_response_go_terms_{ind_start}_{ind_end}.json', 'w') as fp:
    json.dump(llm_response_dict, fp)
    
df.to_csv(f'data/GO_term_analysis/LLM_processed_selected_go_terms_{ind_start}_{ind_end}.tsv', sep='\t', index=True) # need to keep the index because it is the GO term
