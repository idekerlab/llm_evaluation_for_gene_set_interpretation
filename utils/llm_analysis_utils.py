import pandas as pd
import json
 
def process_analysis(analysis):
    """
    Process the LLM response to extract the analysis.

    Args:
        analysis (str): LLM response to process.

    Returns:
        str: Processed LLM analysis.
    """

    llm_process = analysis.split("\n")[0].replace("Process: ", "")
        
    llm_score = llm_process.split(" ")[-1].strip("()")
    
    llm_name = llm_process.rsplit(" ", 1)[0]
    
    llm_analysis = analysis.split('\n', 2)[2]
    
    return llm_name, llm_score, llm_analysis

def save_progress(df, response_dict, out_file):
    """
    Save DataFrame and LLM response dictionary to file.
    """
    df.to_csv(f'{out_file}.tsv', sep='\t', index=True)
    with open(f'{out_file}.json', 'w') as fp:
        json.dump(response_dict, fp)