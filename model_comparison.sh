#!/bin/bash -l
#SBATCH --output=./outfile/gpt_go_analysis.%A_%a.out
#SBATCH --error=./errfile/gpt_go_analysis.%A_%a.err
#SBATCH --job-name=llm_go_analysis
#SBATCH --partition="nrnb-compute" # replace with your partition name
#SBATCH --array=13 # run specific array task
#SBATCH --time=3:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1

hostname
date
echo "My SLURM_ARRAY_TASK_ID: " $SLURM_ARRAY_TASK_ID


PARAMFILE=model_compare_params.txt

PARAM=$(awk "NR==$SLURM_ARRAY_TASK_ID" $PARAMFILE)
echo $P
sbaARAM

source activate llm_eval
# run llm query
eval python query_llm_for_analysis.py $PARAM
# awk "NR==$SLURM_ARRAY_TASK_ID" $PARAMFILE | xargs python query_llm_for_analysis.py


date