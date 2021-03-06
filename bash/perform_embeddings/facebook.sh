#!/bin/bash

#SBATCH --job-name=HEATFB
#SBATCH --output=HEATFB_%A_%a.out
#SBATCH --error=HEATFB_%A_%a.err
#SBATCH --array=0-1439
#SBATCH --time=10-00:00:00
#SBATCH --ntasks=2
#SBATCH --mem=10G

e=5

datasets=(facebook)
dims=(5 10 25 50)
seeds=({0..29})
alphas=(00 05 10 20 50 100)
exps=(lp_experiment nc_experiment)

num_datasets=${#datasets[@]}
num_dims=${#dims[@]}
num_seeds=${#seeds[@]}
num_alphas=${#alphas[@]}
num_exps=${#exps[@]}

dataset_id=$((SLURM_ARRAY_TASK_ID / (num_exps * num_alphas * num_seeds * num_dims) % num_datasets))
dim_id=$((SLURM_ARRAY_TASK_ID / (num_exps * num_alphas * num_seeds) % num_dims))
seed_id=$((SLURM_ARRAY_TASK_ID / (num_exps * num_alphas) % num_seeds ))
alpha_id=$((SLURM_ARRAY_TASK_ID / num_exps % num_alphas ))
exp_id=$((SLURM_ARRAY_TASK_ID % num_exps ))

dataset=${datasets[$dataset_id]}
dim=${dims[$dim_id]}
seed=${seeds[$seed_id]}
alpha=${alphas[$alpha_id]}
exp=${exps[$exp_id]}

if [ $alpha -eq 100 ];
then
	alpha=1.00
else
	alpha=0.$alpha
fi

exp=nc_experiment

echo $dataset $dim $seed $alpha $exp

data_dir=datasets/${dataset}
features=${data_dir}/feats.csv.gz 

if [ $exp == "lp_experiment" ]
then
	training_dir=$(printf "edgelists/${dataset}/seed=%03d/training_edges" ${seed})
	edgelist=${training_dir}/edgelist.tsv
else
	edgelist=${data_dir}/edgelist.tsv.gz
fi
dir=$(printf "${dataset}/${exp}/alpha=${alpha}/seed=%03d" ${seed})
embedding_dir=$(printf "embeddings/${dir}/dim=%03d" ${dim} )
walks_dir=walks/${dir}

embedding_f=$(printf "${embedding_dir}/%05d_embedding.csv.gz" ${e})
if [ ! -f $embedding_f ]
then
	module purge
	module load bluebear
	module load apps/python3/3.5.2
	module load apps/keras/2.0.8-python-3.5.2

	args=$(echo --edgelist ${edgelist} --features ${features} \
	--embedding ${embedding_dir} --walks ${walks_dir} \
	--num-walks 10 --walk-length 80 \
	--use-generator --workers 1 \
	--context-size 10 --all-negs \
	--seed ${seed} --dim ${dim} \
	--alpha ${alpha} -e ${e})

	ulimit -c 0
	python main.py ${args}

else 
	echo $embedding_f already exists
fi