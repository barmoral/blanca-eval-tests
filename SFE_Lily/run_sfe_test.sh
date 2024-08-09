#!/bin/bash

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=50:00:00
#SBATCH --partition=blanca-shirts
#SBATCH --qos=blanca-shirts
#SBATCH --account=blanca-shirts
#SBATCH --gres=gpu
#SBATCH --job-name=sfe_test_Lily
#SBATCH --output=slurm_codes/sfe_test_lily.log

module purge
module avail
ml anaconda
ml openmpi
conda activate openff-sage

python sfes.py
echo "It finished"

sacct --format=jobid,jobname,cputime,elapsed