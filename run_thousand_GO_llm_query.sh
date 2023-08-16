#!/bin/bash -l
#SBATCH --output=./outfile/gpt_go_analysis.%A_%a.out
#SBATCH --error=./errfile/gpt_go_analysis.%A_%a.err
#SBATCH --job-name=gpt_go_analysis
#SBATCH --partition="nrnb-compute" # replace with your partition name
#SBATCH --array=3-19%5 #run all: start from 0 to 19
#SBATCH --time=3:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1

hostname
date
echo "My SLURM_ARRAY_TASK_ID: " $SLURM_ARRAY_TASK_ID
# Calculate start and end index for each job (50 gene sets per job) NOTE: starting from 0
START=$(( $SLURM_ARRAY_TASK_ID * 50 ))
END=$(( ($SLURM_ARRAY_TASK_ID + 1) * 50 - 1 ))

# Define input file and configuration
INPUT="data/GO_term_analysis/1000_selected_go_terms.csv"
CONFIG="1000GOterm_config.json"

source activate llm
# Run the Python script for the given range
python query_llm_for_analysis.py --input $INPUT --start $START --end $END --config $CONFIG

date