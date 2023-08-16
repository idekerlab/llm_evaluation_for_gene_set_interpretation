# hypergeometric test for the top 10 hits gene sets and the true gene set
import pandas as pd
from scipy.stats import hypergeom
from statsmodels.stats.multitest import multipletests
from tqdm import tqdm
import os 
import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--input_file', type=str, help='input file path')

parser.add_argument('--topn', type=int, help='collect top n hits names and sim scores')
parser.add_argument('--output_file', type=str, help='output file path')

def calc_JI(set1, set2):
    return len(set1.intersection(set2)) / len(set1.union(set2))

args = parser.parse_args()

input_file = args.input_file
output_file = args.output_file

df = pd.read_csv(input_file, sep='\t')
df.set_index('GO', inplace=True)
all_go = pd.read_csv('data/go_terms.csv', index_col=0)

# set the top n hits
n_hit = args.topn

# placeholders for p-values
df['pvals'] = None
df['adj_pvals'] = None
df['random_pvals'] = None
df['random_adj_pvals'] = None


M = len(set(all_go['Genes'].str.split(' ').sum())) # total number of genes in all GO terms
all_pvals_dict = {}
pvals_index = {}
rand_pvals = []
for i, row in tqdm(df.iterrows(), total=df.shape[0]):
    current_gene_set = row['Genes'].split(' ')
    # print(current_gene_set)
    top_n_hits = row[f'top_{n_hit}_hits'].split('|')
    # print(len(top_n_hits))
    pvals_list = []
    ji = []
    for j, term in enumerate(top_n_hits):
        genes = all_go[all_go['Term_Description'] == term]['Genes'].tolist()[0].split(' ')
        # print(genes)
        x = len(set(current_gene_set).intersection(set(genes)))  # number of genes in the intersection
        
        n = len(set(current_gene_set)) # total number of genes in the true gene set
        N = len(set(genes)) # total number of genes in this query gene set
        # hypergeometric test of the gene set 
        pval = hypergeom.sf(x-1, M, n, N)

        pvals_list.append(pval)
        
        # Store the p-values by j
        if j in all_pvals_dict:
            all_pvals_dict[j].append(pval)
        else:
            all_pvals_dict[j] = [pval]

        # check nan in p 
        if np.isnan(pval):
            print(f"NaN p-value for M={M}, n={n}, N={N}, x={x}")
            print(i, j, term)

        # Store the position of each p-value by j for later reference
        if j in pvals_index:
            pvals_index[j].append((i, j))
        else:
            pvals_index[j] = [(i, j)]
    # hypergeomatric test for the random
    random_go_term = row['random_GO_name']
    # get the genes in the random GO term
    random_row_genes = all_go.loc[all_go['Term_Description']==random_go_term, 'Genes'].values[0].split(' ')
    x_rand = len(set(current_gene_set).intersection(set(random_row_genes))) 
    N_rand = len(random_row_genes)

    p_val_rand = hypergeom.sf(x_rand-1, M, n, N_rand)
    rand_pvals.append(p_val_rand)
    df.loc[i, 'random_pvals'] = p_val_rand
    
    df.loc[i, 'pvals'] = '|'.join(str(pval) for pval in pvals_list)


# Adjust the p-values for each j separately
for j in all_pvals_dict:
    adj_pvals = multipletests(np.array(all_pvals_dict[j]), method='fdr_bh')[1]

# print(adj_pvals)
    # Assign adjusted p-values back to the data frame
    for adj_pval, (i, _) in zip(adj_pvals, pvals_index[j]):
        if df.loc[i, 'adj_pvals']:
            df.loc[i, 'adj_pvals'] += '|' + str(adj_pval)
        else:
            df.loc[i, 'adj_pvals'] = str(adj_pval)
rand_adj_pvals = multipletests(np.array(rand_pvals), method='fdr_bh')[1]
df['random_adj_pvals'] = rand_adj_pvals
            

df.to_csv(output_file, sep='\t', index=True)