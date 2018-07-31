#!/bin/bash 

# proximal result clipping
# python prelim_analysis.py --vtk --source AneurysmGeneration/models/SKD0050/SKD0050_baseline_model_modified_p2.vtp  --results Artificial/RCA/p2/all_results.vtp --mapping --post --suff p2 --clip
python prelim_analysis.py --vtk --source AneurysmGeneration/models/SKD0050/SKD0050_baseline_model_modified_p3.vtp  --results Artificial/RCA/p3/all_results.vtp --mapping --post --suff p3 --clip
python prelim_analysis.py --vtk --source AneurysmGeneration/models/SKD0050/SKD0050_baseline_model_modified_p4.vtp  --results Artificial/RCA/p4/all_results.vtp --mapping --post --suff p4 --clip
python prelim_analysis.py --vtk --source AneurysmGeneration/models/SKD0050/SKD0050_baseline_model_modified_p5.vtp  --results Artificial/RCA/p5/all_results.vtp --mapping --post --suff p5 --clip

# medial results
python prelim_analysis.py --vtk --source AneurysmGeneration/models/SKD0050/SKD0050_baseline_model_modified_m1.vtp  --results Artificial/RCA/m1/all_results.vtp --mapping --post --suff m1 --clip
python prelim_analysis.py --vtk --source AneurysmGeneration/models/SKD0050/SKD0050_baseline_model_modified_m2.vtp  --results Artificial/RCA/m2/all_results.vtp --mapping --post --suff m2 --clip
python prelim_analysis.py --vtk --source AneurysmGeneration/models/SKD0050/SKD0050_baseline_model_modified_m3.vtp  --results Artificial/RCA/m3/all_results.vtp --mapping --post --suff m3 --clip
python prelim_analysis.py --vtk --source AneurysmGeneration/models/SKD0050/SKD0050_baseline_model_modified_m4.vtp  --results Artificial/RCA/m4/all_results.vtp --mapping --post --suff m4 --clip
python prelim_analysis.py --vtk --source AneurysmGeneration/models/SKD0050/SKD0050_baseline_model_modified_m5.vtp  --results Artificial/RCA/m5/all_results.vtp --mapping --post --suff m5 --clip
