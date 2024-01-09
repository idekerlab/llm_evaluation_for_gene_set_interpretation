import argparse
import pandas as pd
import json 
from utils.openai_query import openai_chat
from utils.prompt_factory import make_user_prompt_with_score
from utils.server_model_query import server_model_chat
from utils.llm_analysis_utils import process_analysis, save_progress
from utils.genai_query import query_genai_model
from tqdm import tqdm
import constant
import openai
import os
import logging
import re


# handle the logger so it create a new one for each model run
def get_logger(filename):
    logger = logging.getLogger(filename)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        file_handler = logging.FileHandler(filename)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


# Add argument parsing
parser = argparse.ArgumentParser(description='Process range of gene sets.')
parser.add_argument('--config', type=str, required=True, help='Config file for LLM')
parser.add_argument('--initialize', action='store_true', help='If provided, initializes the input file with llm names, analysis and score to None. By default, this is not done.')
parser.add_argument('--input', type=str, required=True, help='Path to input csv with gene sets')
parser.add_argument('--input_sep', type=str, required=True, help='Separator for input csv')
parser.add_argument('--set_index', type=str, default = 0, help='Column name for gene set index, default would be first column')
parser.add_argument('--gene_column', type=str, required=True, help='Column name for gene set')
parser.add_argument('--gene_sep', type=str, required=True, help='Separator for gene set')
parser.add_argument('--start', type=int, required=True, help='Start index for gene set range')
parser.add_argument('--end', type=int, required=True, help='End index for gene set range')
parser.add_argument('--gene_features', type=str, default=None, help='Path to csv with gene features if need to be included in prompt')
parser.add_argument('--direct', action='store_true', default=None, help='Whether to use direct prompt or not, default is None')

parser.add_argument('--customized_prompt', type=str, default=None, help='If using customized prompt then use the path to the customized prompt, default is None')
parser.add_argument('--output_file', type=str, required=True, help='Path to output with LLM analysis, no need to include file extension, will be saved as .tsv and .json')

args = parser.parse_args()

config_file = args.config
input_file = args.input
ind_start = args.start
ind_end = args.end
gene_column = args.gene_column
gene_sep = args.gene_sep
set_index = args.set_index
input_sep = args.input_sep
gene_features = args.gene_features
direct = args.direct
customized_prompt = args.customized_prompt
out_file = args.output_file


with open(config_file) as json_file:
    config = json.load(json_file)
    
if customized_prompt:
    # make sure the file exist 
    if os.path.isfile(config['CUSTOM_PROMPT_FILE']):
        with open(config['CUSTOM_PROMPT_FILE'], 'r') as f: # replace with your actual customized prompt file
            customized_prompt = f.read()
            assert len(customized_prompt) > 1, "Customized prompt is empty"
    else:
        print("Customized prompt file does not exist")
        customized_prompt = None
else:
    customized_prompt = None
    
    
#load openai key, context, and model used 
openai.api_key = os.environ['OPENAI_API_KEY']

context = config['CONTEXT']
model = config['MODEL']
temperature = config['TEMP']
max_tokens = config['MAX_TOKENS']
if model.startswith('gpt'):
    rate_per_token = config['RATE_PER_TOKEN']
    DOLLAR_LIMIT = config['DOLLAR_LIMIT']
LOG_FILE = config['LOG_NAME']+f'_{ind_start}_{ind_end}.log'

seed = constant.SEED
#################define the main function#################
def main(df):
    analysis_dict  = {}

    logger = get_logger(f'{out_file}.log')

    i = 0 #used for track progress and saving the file
    for idx, row in tqdm(df.iterrows(), total=df.shape[0]):
        #only process None rows 
        if pd.notna(row[f'{column_prefix} Analysis']):
            continue
        
        gene_data = row[gene_column]
        # if gene_data is not a string, then skip
        if type(gene_data) != str:
            
            logger.warning(f'Gene set {idx} is not a string, skipping')
            continue
        genes = gene_data.split(gene_sep)
        
        if len(genes) >1000:
            logger.warning(f'Gene set {idx} is too big, skipping')
            continue

        try:
            prompt = make_user_prompt_with_score(genes)
            # print(prompt)
            finger_print = None
            if model.startswith('gpt'):
                print("Accessing OpenAI API")
                analysis, finger_print = openai_chat(context, prompt, model, temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT, seed)
            elif model.startswith('gemini'):
                print("Using Google Gemini API")
                analysis, error_message = query_genai_model(f"{context}\n{prompt}", model, temperature, max_tokens, LOG_FILE) 
            else:
                print("Using server model")
                analysis, error_message= server_model_chat(context, prompt, model, temperature, max_tokens,LOG_FILE, seed)

            
            if analysis:
                # print(analysis)
                llm_name, llm_score, llm_analysis = process_analysis(analysis)
                # clean up the score and return float
                try:
                    llm_score_value =  float(re.sub("[^0-9.-]", "", llm_score))
                except ValueError:
                    llm_score_value = llm_score
                
                df.loc[idx, f'{column_prefix} Name'] = llm_name
                df.loc[idx, f'{column_prefix} Analysis'] = llm_analysis
                df.loc[idx, f'{column_prefix} Score'] = llm_score_value
                analysis_dict[f'{idx}_{column_prefix}'] = analysis
                # Log success with fingerprint
                logger.info(f'Success for {idx} {column_prefix}.')
                if finger_print:
                    logger.info(f'GPT_Fingerprint for {idx}: {finger_print}')
                    
            else:
                if error_message:
                    logger.error(f'Error for query gene set {idx}: {error_message}')
                else:
                    logger.error(f'Error for query gene set {idx}: No analysis returned')
                    
        except Exception as e:
            logger.error(f'Error for {idx}: {e}')
            continue
        i += 1
        if i % 10 == 0:
            save_progress(df, analysis_dict, out_file)
            # df.to_csv(f'{out_file}.tsv', sep='\t', index=True)
            print(f"Saved progress for {i} genesets")
    # save the final file
    save_progress(df, analysis_dict, out_file)


if __name__ == "__main__":
    if input_sep == '\\t':
        input_sep = '\t'
    # print(repr(input_sep))
    raw_df = pd.read_csv(input_file, sep=input_sep, index_col=set_index)
    print(raw_df.columns)

    # Only process the specified range of genes
    df = raw_df.iloc[ind_start:ind_end]
    
    if '-' in model:
        name_fix = '_'.join(model.split('-')[:2])
    else:
        name_fix = model.replace(':', '_')
    column_prefix = name_fix + '_default' #start from default gene set
    
    if args.initialize:
        # initialize the input file with llm names, analysis and score to None
        df[f'{column_prefix} Name'] = None
        df[f'{column_prefix} Analysis'] = None
        df[f'{column_prefix} Score'] = None
    print(df[f'{column_prefix} Analysis'].isna().sum())
    main(df)  ## run with the real set 
    
     ## run the pipeline for contaiminated gene sets 
    contaminated_columns = [col for col in df.columns if col.endswith('contaminated_Genes')]
    # print(contaminated_columns)
    for col in contaminated_columns:
        gene_column = col ## Note need to change the gene_column to the contaminated column
        contam_prefix = '_'.join(col.split('_')[0:2])
        
        column_prefix = name_fix + '_' +contam_prefix
        print(column_prefix)
        
        
        if args.initialize:
            # initialize the input file with llm names, analysis and score to None
            df[f'{column_prefix} Name'] = None
            df[f'{column_prefix} Analysis'] = None
            df[f'{column_prefix} Score'] = None
        print(df[f'{column_prefix} Analysis'].isna().sum())
        main(df)

print("Done")