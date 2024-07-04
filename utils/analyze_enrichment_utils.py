import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
import seaborn as sns

#  functions to compute the Jaccard Index and coverage for the query gene list and the GO term genes
def get_JI(query_size: int, term_size: int, intersection_size: int) -> float:
    # Calculate JI
    JI = intersection_size / (query_size + term_size - intersection_size) if query_size + term_size - intersection_size != 0 else 0
    
    return JI

def get_coverage(query_size: int, intersection_size: int) -> float:
    # Calculate the coverage
    coverage = intersection_size / query_size if query_size != 0 else 0
    
    return coverage


def cal_JI_coverage(df) -> pd.DataFrame:
# Apply the get_JI and get_coverage functions to each row and add new columns to the DataFrame
    df['gprofiler_JI'] = df.apply(lambda row: get_JI(row['query_size'], row['term_size'], row['intersection_size']), axis=1)


    df['gprofiler_coverage'] = df.apply(lambda row: get_coverage(row['query_size'], row['intersection_size']), axis=1)
    return df


# Define a function to filter and select the appropriate row
def filter_and_select_coverage(df, adj_pval_thresh, coverageCol = 'gprofiler_coverage', thresh=0.2) -> pd.Series:
    # Filter rows that pass both apv and coverage requirements
    filtered = df[(df[coverageCol] >= thresh) & (df['Adjusted P-value'] <= adj_pval_thresh)]
    
    if not filtered.empty:
        # If there are rows that pass both requirements, select the one with the lowest adjusted p-value
        return filtered.loc[filtered['Adjusted P-value'].idxmin()]
    else:
        # If no rows pass both requirements, select the one with the lowest adjusted p-value in the original group
        return df.loc[df['Adjusted P-value'].idxmin()]
    
# Define a function to filter on pass both coverage/JI and adjusted p-value thresholds, and select the row with the highest coverage/JI
def filter_and_select_max_coverage(df, adj_pval_thresh, coverageCol = 'gprofiler_coverage', thresh=0.2) -> pd.Series:
    # sort by coverage
    df = df.sort_values(by=coverageCol, ascending=False).reset_index(drop=True)
    # Filter rows that pass both apv and coverage requirements
    filtered = df[(df[coverageCol] >= thresh) & (df['Adjusted P-value'] <= adj_pval_thresh)]
    
    if not filtered.empty:
        # If there are rows that pass both requirements, select the one with the highest coverage/JI
        return filtered.loc[filtered[coverageCol].idxmax()]
    else:
        # If no rows pass both requirements, select the one with the lowest adjusted p-value in the original group
        return df.loc[df['Adjusted P-value'].idxmin()]

# select the smallest p-value
def get_min_adj_p_value(df, sortCol = None):
    '''
    sortCol: if same p-value, select the row with the highest coverage/JI, specify the column name to sort the rows on. options: 'gprofiler_coverage', 'gprofiler_JI'
    '''
    if not sortCol:
        # if not specify a column to sort on, select the row with the min p-value
        return df.loc[df['Adjusted P-value'].idxmin()]
    else:
        # find the min p-value
        min_p = df['Adjusted P-value'].min()
        # select the row with the min p-value
        min_p_row = df[df['Adjusted P-value'] == min_p]
        if len(min_p_row) > 1:
            # if there are multiple rows with the same min p-value, select the one with the highest coverage
            return min_p_row.loc[min_p_row[sortCol].idxmax()]
        else:
            return min_p_row.iloc[0]
    

def create_success_contingency_table(df):
    # Make the LLM vs enrichr contingency table
    contingency_table = pd.crosstab(df['gprofiler_success_TF'], df['LLM_success_TF'], rownames=['gprofiler_success_TF'], colnames=['LLM_success_TF'])

    # Reorder the rows and columns
    contingency_table = contingency_table.reindex(index=[True, False], columns=[True, False])

    # Add the total column and row
    contingency_table['Total'] = contingency_table.sum(axis=1)
    contingency_table.loc['Total'] = contingency_table.sum(axis=0)

    return contingency_table
        

def select_rows_and_columns(df, number_of_rows=None):
    # Specify the ordered list of column names you want to return
    ordered_column_names = [
        'n_Genes', 'GeneList', 'LLM Name', 'Score', 'Term', 'GO ID',
        'Adjusted P-value', 'intersection_size', 'term_size', 'intersections',  'gprofiler_coverage', 'LLM_coverage','gprofiler_JI', 
        'LLM_success_TF', 'gprofiler_success_TF'
    ]
    
    # If number_of_rows is not specified, select all rows
    if number_of_rows is None:
        result_df = df.loc[:, ordered_column_names]
    else:
        result_df = df.loc[:, ordered_column_names].head(number_of_rows)
    
    return result_df



def coverage_thresholding(df, col, coverage_thresh_list = np.arange(0.0, 1.1, 0.1), term_type = 'enrich_terms', enrich_adj_pval_thresh = 0.05, LLM_score_thresh = 0.82) -> pd.DataFrame:
    '''
    df: DataFrame with LLM terms, LLM confidence, enriched terms, coverages and adjusted p-values
    col: Column name for the 'coverage' value to be thresholded
    coverage_thresh_list: List of coverage thresholds to evaluate (default: np.arange(0.0, 1.1, 0.1))
    term_type: Type of terms to evaluate ('enrich_terms' or 'LLM_terms')
    enrich_adj_pval_thresh: Adjusted p-value threshold for enriched terms (default: 0.05)
    LLM_score_thresh: Confidence score threshold for LLM terms (default: 0.82)
    return: DataFrame with the evaluation results for each coverage threshold
    '''

    # Initialize the result DataFrame with 0
    coverage_thresh_eval_DF = pd.DataFrame({
        'coverage_thresh': coverage_thresh_list,
        'num_success': np.zeros(len(coverage_thresh_list)), 
        'perc_success': np.zeros(len(coverage_thresh_list)),
        'perc_meetsThresh': np.zeros(len(coverage_thresh_list)),
        'perc_success_normed': 100
    })

    # Loop through each coverage threshold
    for i, coverage_thresh in enumerate(coverage_thresh_list):
        # Calculate perc_success: percentage of rows that meet both the coverage and adjusted p-value thresholds(enrich terms) or coverage and LLM confidence score thresholds(LLM terms)
        if term_type == 'enrich_terms':
            coverage_threshCol = ((df['Adjusted P-value'] <= enrich_adj_pval_thresh) & (df[col] >= coverage_thresh))
        elif term_type == 'LLM_terms':
            coverage_threshCol = ((df['Score'] >= LLM_score_thresh) & (df[col] >= coverage_thresh))
        
        coverage_thresh_eval_DF.loc[i, 'num_success'] = sum(coverage_threshCol)
        coverage_thresh_eval_DF.loc[i, 'perc_success'] = (sum(coverage_threshCol) / len(df)) * 100
        # Calculate perc_success_normed: percentage of rows that meet both the coverage and adjusted p-value thresholds, normalized by the number of rows that meet the adjusted p-value threshold
        pval_threshCol = (df['Adjusted P-value'] <= enrich_adj_pval_thresh)
        # print(sum(pval_threshCol))
        # print(sum(coverage_threshCol))
        coverage_thresh_eval_DF.loc[i, 'perc_success_normed'] = (sum(coverage_threshCol) / sum(pval_threshCol)) * 100
        
        # Calculate perc_meetsThresh: percentage of rows that meet the coverage threshold
        
        coverage_threshOnlyCol = (df[col] >= coverage_thresh)

        coverage_thresh_eval_DF.loc[i, 'num_meetsThresh'] = sum(coverage_threshOnlyCol)
        
        coverage_thresh_eval_DF.loc[i, 'perc_meetsThresh'] = (sum(coverage_threshOnlyCol) / len(df)) * 100
        
    return coverage_thresh_eval_DF


## function for plot the coverage thresholding results
def plot_coverage_threshold_curve(GO_thresh_eval_DF, LLM_thresh_eval_DF, go_label='g:Profiler', llm_label='GPT-4', highlight_coverage = [0.0, 0.2,0.5], figsize=(3, 2), save_file=None):
    plt.figure(figsize=figsize)
    
    # plot for enrichr coverage thresholding
    sns.scatterplot(data=GO_thresh_eval_DF, x='coverage_thresh', y='num_success', s=20, color='black')
    sns.lineplot(data=GO_thresh_eval_DF, x='coverage_thresh', y='num_success', color='black', label=go_label)
    
    # plot for LLM coverage thresholding
    sns.scatterplot(data=LLM_thresh_eval_DF, x='coverage_thresh', y='num_success', s=20, color='blue')
    sns.lineplot(data=LLM_thresh_eval_DF, x='coverage_thresh', y='num_success', color='blue', label=llm_label)

    # Setting the y-axis limits make sure all points are visible
    plt.ylim(-8, 300)
    
    # Adding vertical lines at specific thresholds
    coverage_thresh = highlight_coverage 
    for thresh in coverage_thresh:
        plt.axvline(x=thresh, color='red', linestyle='dotted')
        
        # label the line as the percentage/number of omics gene sets that meet the threshold
        enrich_meetsThresh = GO_thresh_eval_DF.loc[GO_thresh_eval_DF['coverage_thresh'] == thresh, 'num_success'].values[0]
        plt.text(thresh + 0.02, enrich_meetsThresh, f'{int(enrich_meetsThresh)}', color='black', ha='left')
        
        llm_meetsThresh = LLM_thresh_eval_DF.loc[LLM_thresh_eval_DF['coverage_thresh'] == thresh, 'num_success'].values[0]
        plt.text(thresh + 0.02, llm_meetsThresh, f'{int(llm_meetsThresh)}', color='blue', ha='left')
        
        print(f'coverage threshold: {thresh}, enrichment: {enrich_meetsThresh}, LLM: {llm_meetsThresh}')
    
    # Adding labels and title
    plt.xlabel('Required coverage threshold')
    plt.ylabel('Number of omics gene sets with\nrequired coverage and significance')
    plt.legend()
    sns.despine()
    if save_file :
        plt.savefig(save_file, format='svg', bbox_inches='tight')
    # Display the plot
    plt.show()

def plot_thresholding_res(df, enrich_coverage_col, llm_coverage_col, coverage_thresh_list = np.arange(0.0, 1.1, 0.1), enrich_adj_pval_thresh = 0.05, LLM_score_thresh = 0.01, go_label='g:Profiler', llm_label='GPT-4', highlight_coverage = [0.0, 0.2,0.5], figsize=(3, 2), save_file=None):
    '''
    df: DataFrame with LLM terms, LLM confidence, enriched terms, coverages and adjusted p-values
    enrich_coverage_col: Column name for the 'coverage' value of enriched terms (e.g., 'gprofiler_coverage' or 'gprofiler_JI')
    llm_coverage_col: Column name for the 'coverage' value of LLM terms (e.g., 'LLM_coverage' or 'LLM_JI')
    coverage_thresh_list: List of coverage thresholds to evaluate (default: np.arange(0.0, 1.1, 0.1))
    enrich_adj_pval_thresh: Adjusted p-value threshold for enriched terms (default: 0.05)
    LLM_score_thresh: Confidence score threshold for LLM terms (default: 0.01)
    go_label: Label for the enriched terms (default: 'g:Profiler')
    llm_label: Label for the LLM terms (default: 'GPT-4')
    figsize: Figure size for the plot (default: (3, 2))
    save_file: File path to save the plot (default: None)
    '''
    # Calculate the coverage thresholding results
    GO_thresh_eval_DF = coverage_thresholding(df, enrich_coverage_col, coverage_thresh_list, 'enrich_terms', enrich_adj_pval_thresh, LLM_score_thresh)
    LLM_thresh_eval_DF = coverage_thresholding(df, llm_coverage_col, coverage_thresh_list, 'LLM_terms', enrich_adj_pval_thresh, LLM_score_thresh)
    # Plot the coverage thresholding results
    plot_coverage_threshold_curve(GO_thresh_eval_DF, LLM_thresh_eval_DF, go_label=go_label, llm_label=llm_label,highlight_coverage = highlight_coverage, figsize=figsize, save_file=save_file)