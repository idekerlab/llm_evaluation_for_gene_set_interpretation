
def add_gene_feature_summary(prompt_text, feature_dataframe, n_genes=2):
    for index, row in feature_dataframe.iterrows():
        number_of_genes = 0
        if row['Number of Genes'] is not None:
            number_of_genes = int(row['Number of Genes'])
        if number_of_genes >= n_genes:
            prompt_text += f"{row['Feature']}: {row['Number of Genes']} proteins: {row['Genes']}\n"
    return prompt_text
    
    
def make_user_prompt(genes, feature_df = [], direct = False, customized_prompt = None):
    """
    Create a ChatGPT prompt based on the list of genes
    :return: A string containing the ChatGPT prompt text
    """

    general_analysis_instructions = """
Be concise, do not use unneccesary words. Be specific, avoid overly general
statements such as 'the proteins are involved in various cellular processes'
Be factual, do not editorialize.
For each important point, describe your reasoning and supporting information. 
    """
    
    task_instructions = """
Write a critical analysis of the biological processes performed 
by this system of interacting proteins. Propose a brief name for
for the most prominant biological process performed by the system.
    """
    direct_instructions = """
Propose a name and provide analysis for the following gene set.
    """
    
    format_placeholder = """ 
Put the name at the top of the analysis as 'Process: <name>' 
    """
    
    if direct == True:
        prompt_text = direct_instructions
        prompt_text += format_placeholder
    elif customized_prompt:
        prompt_text = customized_prompt
        prompt_text += format_placeholder
    else:
        prompt_text = task_instructions
        prompt_text += format_placeholder
        prompt_text += general_analysis_instructions
        
    prompt_text += "\n\nHere are the interacting proteins:\n"
    prompt_text += f'\nProteins: '
    prompt_text += ", ".join(genes) + ".\n\n"

    if feature_df:
        prompt_text += "\n\nHere are the gene features:\n"
        prompt_text  = add_gene_feature_summary(prompt_text, feature_df)
    
    

    return prompt_text