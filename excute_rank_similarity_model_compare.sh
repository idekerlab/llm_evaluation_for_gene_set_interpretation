#!/bin/bash -l

source activate llm_eval

# Loop over files and process each within the same Slurm job
for file in data/GO_term_analysis/model_compare/LLM_processed_model_compare_100set*.tsv; do
    model=$(basename "$file" .tsv | awk -F'_' '{print $(NF-1)"_"$NF}')

    output_file="data/GO_term_analysis/model_compare/sim_rank_LLM_processed_model_compare_100set_${model}.tsv"

    # Run the Python script for each file

    echo "Processing $file"
    python rank_GOterm_LLM_sim_rand.py --input_file "$file" --emb_file data/all_go_terms_embeddings_dict.pkl --topn 3 --output_file "$output_file"

    date
done