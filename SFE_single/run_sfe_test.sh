#!/bin/bash

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=50:00:00
#SBATCH --partition=blanca-shirts
#SBATCH --qos=blanca-shirts
#SBATCH --account=blanca-shirts
#SBATCH --gres=gpu
#SBATCH --job-name=sfe_test_alkynes
#SBATCH --output=slurm_codes/sfe_test_alkynes.log

module purge
module avail
ml anaconda
conda activate openff-sage

python sfe_test.py
echo "It finished"

sacct --format=jobid,jobname,cputime,elapsed