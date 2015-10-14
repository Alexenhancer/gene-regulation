"""Looking for parB sites in P.aeruginosa.

Usage: 
    snakemake -p  -c "qsub {params.qsub}" -j 12 \
        -s scripts/snakefiles/workflows/Scerevisiae-Pho4.py \
        [targets]

Flowcharts:
    snakemake -p -s scripts/snakefiles/workflows/Paeruginosa.py \
        --force flowcharts

Organism: 		Pseudomonas aeruginosa
Reference genome:	-
Sequencing type: 	single end

Author: 		Claire Rioualen, Jacques van Helden
Contact: 		claire.rioualen@inserm.fr
"""

#================================================================#
#                        Imports                                 #
#================================================================#

from snakemake.utils import R
import os
import sys
import time#rm?
import datetime
import pandas as pd

## Config
configfile: "scripts/snakefiles/workflows/Paeruginosa_local.json"
workdir: config["dir"]["base"]
verbosity = int(config["verbosity"])

#================================================================#
#                         Includes                               #
#================================================================#

FG_LIB = os.path.abspath(config["dir"]["fg_lib"])
RULES = os.path.join(FG_LIB, "scripts/snakefiles/rules")
PYTHON = os.path.join(FG_LIB, "scripts/snakefiles/python_lib")

include: os.path.join(PYTHON, "util.py")
include: os.path.join(RULES, "util.rules")
include: os.path.join(RULES, "count_reads.rules")
include: os.path.join(RULES, "bwa_index.rules")
include: os.path.join(RULES, "bwa_se.rules")
include: os.path.join(RULES, "convert_bam_to_bed.rules")
include: os.path.join(RULES, "count_oligo.rules")
include: os.path.join(RULES, "fastqc.rules")
include: os.path.join(RULES, "flowcharts.rules")
include: os.path.join(RULES, "getfasta.rules")
include: os.path.join(RULES, "homer.rules")
include: os.path.join(RULES, "macs2.rules")
include: os.path.join(RULES, "peak_length.rules")
include: os.path.join(RULES, "peak_motifs.rules")
include: os.path.join(RULES, "purge_sequence.rules")
include: os.path.join(RULES, "sickle_se.rules")
include: os.path.join(RULES, "spp.rules")
include: os.path.join(RULES, "swembl.rules")

#================================================================#
#                      Data & config                             #
#================================================================#

# Raw data
READS = config["dir"]["reads_source"]

# Samples
SAMPLES = read_table(config["files"]["samples"], verbosity=verbosity)
SAMPLE_IDS = SAMPLES.iloc[:,0] ## First column MUST contain the sample ID

## Design
DESIGN = read_table(config["files"]["design"], verbosity=verbosity)
TREATMENT = DESIGN.iloc[:,0]
CONTROL = DESIGN.iloc[:,1]

## Ref genome
GENOME = config["genome"]["genome_version"]

## Results dir
RESULTS_DIR = config["dir"]["results"]
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

#================================================================#
#                         Workflow                               #
#================================================================#

## Data import & merging.

## À revoir, rsync output du texte -> plante flowcharts...
#os.system("rsync -rupltv --exclude '*.tab' " + READS + " " + RESULTS_DIR)

## Graphics & reports
GRAPHICS = expand(RESULTS_DIR + "dag.pdf")
REPORT = expand(RESULTS_DIR + "report.html")

## Suffixes (beta) (! implement several values for each param)

ALIGNER="bwa"
ALIGNMENT=expand("{samples}/{samples}_{aligner}", samples=SAMPLE_IDS, aligner=ALIGNER)

PEAKCALLER="homer_peaks swembl-R" + config["swembl"]["R"] # macs2_peaks spp-fdr" + config["spp"]["fdr"] + " 
PEAKCALLER=PEAKCALLER.split()
PEAKCALLING=expand(expand("{treat}_vs_{control}/{{peakcaller}}/{treat}_vs_{control}_{{aligner}}_{{peakcaller}}", zip, treat=TREATMENT, control=CONTROL), peakcaller=PEAKCALLER, aligner=ALIGNER)

MOTIFS=expand(expand("{treat}_vs_{control}/{{peakcaller}}/peak-motifs/{treat}_vs_{control}_{{aligner}}_{{peakcaller}}_purged", zip, treat=TREATMENT, control=CONTROL), peakcaller=PEAKCALLER, aligner=ALIGNER)

#----------------------------------------------------------------#
# Quality control
#----------------------------------------------------------------#

RAW_QC = expand(RESULTS_DIR + "{samples}/{samples}_fastqc/", samples=SAMPLE_IDS)
RAW_READNB = expand(RESULTS_DIR + "{samples}/{samples}_fastq_readnb.txt", samples=SAMPLE_IDS)

#----------------------------------------------------------------#
# Alignment
#----------------------------------------------------------------#

BWA_INDEX = expand(config["dir"]["genome"] + "{genome}/BWAIndex/{genome}.fa.bwt", genome=GENOME)

MAPPING = expand(RESULTS_DIR + "{alignment}.sam", alignment=ALIGNMENT)

# Sorted and converted reads (bam, bed)
SORTED_MAPPED_READS_BWA = expand(RESULTS_DIR + "{alignment}_sorted_pos.bam", alignment=ALIGNMENT)
BAM_READNB = expand(RESULTS_DIR + "{alignment}_sorted_pos_bam_readnb.txt", alignment=ALIGNMENT)
SORTED_READS_BED = expand(RESULTS_DIR + "{alignment}_sorted_pos.bed", alignment=ALIGNMENT)
BED_FEAT_COUNT = expand(RESULTS_DIR + "{alignment}_sorted_pos_bed_nb.txt", alignment=ALIGNMENT)

# ----------------------------------------------------------------
# Peak-calling
# ----------------------------------------------------------------

#BEDS = expand(RESULTS_DIR + "{alignment}.bed", alignment=ALIGNMENT)
PEAKS = expand(RESULTS_DIR + "{peakcalling}.bed", peakcalling=PEAKCALLING)

# ----------------------------------------------------------------
# Peak analysis
# ----------------------------------------------------------------

GET_FASTA = expand(RESULTS_DIR + "{peakcalling}.fasta", peakcalling=PEAKCALLING)

PURGE_PEAKS = expand(RESULTS_DIR + "{peakcalling}_purged.fasta", peakcalling=PEAKCALLING)

## Oligo analysis # ! missing f* input exception
OLIGO = config['oligo_analysis']['count_oligo'].split()
OLIGO_ANALYSIS = expand(RESULTS_DIR + "{peakcalling}_purged_oligo{oligo}.txt", peakcalling=PEAKCALLING, oligo=OLIGO)

PEAKS_LENGTH = expand(RESULTS_DIR + "{peakcalling}_purged_length.png", peakcalling=PEAKCALLING)

PEAK_MOTIFS = expand(RESULTS_DIR + "{motifs}_peak-motifs_synthesis.html", motifs=MOTIFS)

#================================================================#
#                        Rule all                                #
#================================================================#

rule all: 
	"""
	Run all the required analyses
	"""
	input: GRAPHICS, RAW_QC, BED_FEAT_COUNT, PURGE_PEAKS, PEAK_MOTIFS
	params: qsub=config["qsub"]
	shell: "echo Job done    `date '+%Y-%m-%d %H:%M'`"

#================================================================#
#                          Report                                #
#================================================================#

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

#rule report:
#    """
#    Generate a report with the list of datasets + summary of the results.
#    """
# see Scerevisiae report
