# Bioinformatics

## Pick-the-tool cheat sheet
- Short-read DNA alignment to reference: **BWA-MEM** (bwa mem ref.fa r1.fq r2.fq) or **Bowtie2**. Long reads (ONT/PacBio): **minimap2**.
- Search unknown sequence vs database: **BLAST** (blastn nucleotide, blastp protein, blastx translated). Fast/large-scale: **DIAMOND**, **MMseqs2**.
- Variant calling from BAM: **GATK HaplotypeCaller** (germline), **bcftools mpileup+call**, **DeepVariant**; somatic: **Mutect2**.
- Manipulate alignments: **samtools** (sort/index/view/flagstat). Manipulate variants: **bcftools**. BED/interval ops: **bedtools**.
- Assembly: short-read **SPAdes** (bacteria), **MEGAHIT** (metagenomes); long-read **Flye**, **hifiasm**.
- Scripting: **Biopython** (SeqIO, Entrez), **pysam** (BAM/VCF), **scikit-bio**. Pipelines: **Snakemake** / **Nextflow**.

## Sequences
- DNA alphabet `ACGT` (+ `N` ambiguous, IUPAC codes R/Y/S/W/K/M for ambiguity). RNA `ACGU`. Protein 20 aa single-letter + `*` stop, `X` unknown.
- **Reverse complement**: reverse then A<->T, C<->G. Strand matters — reads map to +/- strand.
- Central dogma: DNA -> (transcription) mRNA -> (translation) protein. Codons = 3 nt -> 1 aa; 64 codons, degenerate; start `AUG`(Met), stops `UAA/UAG/UGA`. 6 reading frames (3 per strand).
- GC content, k-mers (substrings length k) underpin assembly (de Bruijn graphs), sketching (MinHash/Mash), classification.

## File formats
- **FASTA** `.fa/.fasta`: `>header` line + sequence lines. Reference genomes, protein sets. Index with `samtools faidx` -> `.fai`.
- **FASTQ** `.fq/.fastq`: 4 lines/read — `@id`, seq, `+`, **quality string**. Phred quality `Q = -10*log10(P_error)`; ASCII = Q+33 (Phred+33/Sanger; old Illumina was +64). Q30 = 1 error/1000.
- **SAM/BAM/CRAM**: alignments. SAM text, BAM binary (bgzip), CRAM reference-compressed. Columns: QNAME, **FLAG** (bitwise: 0x4 unmapped, 0x10 reverse, 0x40/0x80 read1/2, 0x400 dup), RNAME, **POS (1-based)**, MAPQ, **CIGAR** (M/I/D/S/N…), etc. MAPQ = -10log10(P wrong map).
- **VCF/BCF**: variants. `#CHROM POS ID REF ALT QUAL FILTER INFO FORMAT` + per-sample GT. POS **1-based**. GT `0/1` het, `1/1` hom-alt, `./.` missing. Must be bgzipped + tabix-indexed (`.tbi`) for random access.
- **GFF3/GTF**: gene annotations (features, coords **1-based inclusive**). **BED**: intervals, **0-based half-open** `[start,end)` — coordinate systems differ, a constant off-by-one source.

## Alignment
- **Pairwise, global — Needleman-Wunsch**: DP, fill matrix with match/mismatch + gap penalty, traceback; aligns full length. O(nm).
- **Pairwise, local — Smith-Waterman**: DP with 0-floor (no negative), finds best subsequence; optimal but slow -> heuristics for search.
- **Affine gaps**: gap open + gap extend (Gotoh) — biologically realistic (one indel event). Substitution matrices: **BLOSUM62** (default protein), **PAM**; nucleotide match/mismatch scores.
- **BLAST heuristic**: seed with exact **words** (k-mers) -> extend to HSPs -> score. **E-value** = expected hits by chance (lower = better; depends on DB size). Bit score DB-independent. Not guaranteed optimal (unlike SW). Variants: blastn/megablast (nt), blastp (aa), blastx (translated nt query vs aa DB), tblastn (aa query vs translated nt), psiblast (iterative profile). `%identity` + `query coverage` + E-value together judge a hit — high identity over a short span can still be spurious.
- **MSA (multiple)**: MUSCLE, MAFFT, Clustal Omega — progressive/iterative. Output FASTA/`.aln`/Stockholm; drives phylogenetics, conservation, HMM profiles (HMMER, Pfam).

## Read mapping + variant pipeline
```
QC (FastQC/fastp) -> trim adapters -> bwa mem -> samtools sort -> markdup (Picard/samtools markdup)
 -> BQSR (GATK, optional) -> HaplotypeCaller -> joint genotyping (GenotypeGVCFs) -> filter (VQSR/hard) -> annotate (VEP/SnpEff)
```
- Mark (not remove) PCR duplicates; they inflate coverage/false confidence. Coverage/depth (`samtools depth`) — 30x typical WGS.
- Variant types: SNV, indel, MNV, SV/CNV (need split/discordant reads — Manta, Delly). Filter by QUAL, depth, strand bias, allele balance.

## Assembly + phylogenetics
- **De Bruijn graph** assembly: break reads into k-mers, nodes = k-1-mers, resolve paths -> contigs -> scaffolds. Repeats & errors fragment graphs; long reads/Hi-C scaffold. Metrics: **N50** (contig length at 50% of assembly), total size vs expected, BUSCO completeness.
- **Phylogenetics**: distance (NJ/UPGMA), parsimony, **maximum likelihood** (RAxML, IQ-TREE), Bayesian (MrBayes, BEAST). Substitution models (JC69, GTR+G). Bootstrap support (>70/95). Newick format `((A,B),C);`. Root vs unrooted.

## RNA-seq & functional genomics
- **RNA-seq pipeline**: QC/trim -> splice-aware align (**STAR**/**HISAT2**) or pseudo-align/quantify (**salmon**/**kallisto**, transcript-level, fast) -> counts per gene (`featureCounts`, `HTSeq`) -> **differential expression** (**DESeq2**/**edgeR** in R, negative-binomial model) -> report log2 fold-change + adjusted p-value.
- Normalize for library size + composition: **TPM/FPKM** (within-sample, for browsing) vs DESeq2 median-of-ratios / edgeR TMM (between-sample, for DE). Raw counts (not TPM) go into DESeq2/edgeR.
- Downstream: GO/pathway enrichment (GSEA, DAVID, clusterProfiler), clustering/heatmaps, single-cell (Seurat, Scanpy — `.h5ad` AnnData). Design matrix must model condition + batch.
- Other assays: ChIP-seq/ATAC-seq (peaks via **MACS2**, `.narrowPeak`), bisulfite (methylation), Hi-C (3D contacts).

## Sequence analysis tools & tasks
- **ORF finding**, translation (`Bio.Seq.translate`), motif search (regex, PWM/PSSM, MEME), restriction sites. Codon usage / GC skew.
- **HMMER** + **Pfam** for protein domain/family search (profile HMMs vs single-sequence BLAST). **InterProScan** aggregates domain databases.
- **Structure**: PDB (`.pdb`/`.cif`), AlphaFold predicted structures (pLDDT confidence), structural alignment (TM-align, DALI). Sequence != structure conservation.
- k-mer/alignment-free: **Mash/sourmash** (MinHash sketches) for fast genome distance; **Kraken2**/**Centrifuge** for metagenomic taxonomic classification.

## Statistics & experimental design
- **Multiple testing** across genes/variants -> control **FDR** (Benjamini-Hochberg, report q-values), not raw p. Bonferroni for strict family-wise error.
- **Power & replication**: biological replicates (not just technical) determine DE power; n=3 minimum, more for small effects. Confounds (batch, sex, RIN quality) must be balanced or modeled.
- Count models: RNA-seq counts are overdispersed -> negative binomial (DESeq2/edgeR), not Poisson/t-test on raw counts.
- **GWAS**: association test per variant vs phenotype; genome-wide significance `p < 5e-8`; correct for population structure (PCA/mixed models), Manhattan/QQ plots, LD.

## Databases + reproducibility
- **NCBI**: GenBank/RefSeq, SRA (raw reads), dbSNP, ClinVar; access via **Entrez** (Biopython `Bio.Entrez`) or `datasets`/`sra-toolkit`. **Ensembl** (annotations, BioMart, VEP). **UniProt** (protein), **PDB** (structure), **Pfam/InterPro** (domains).
- Reference builds: human **GRCh37/hg19** vs **GRCh38/hg38** — coordinates differ; **never mix**. `liftOver`/CrossMap to convert. Chromosome naming `chr1` vs `1` mismatches break joins.
- Reproducibility: pin tools with **conda/mamba (bioconda)** or **containers (Docker/Singularity)**; workflow managers **Snakemake**/**Nextflow (nf-core)** for DAG, resume, provenance. Version reference + tools in outputs.

## Pitfalls -> Fix
- **0- vs 1-based coordinates** (BED 0-based half-open; VCF/GFF/SAM 1-based inclusive) -> off-by-one when comparing/intersecting -> track format per file; use `bedtools`/pysam which handle conventions; test with a known interval.
- **Reference build mismatch** (hg19 vs hg38, `chr` prefix) -> silent wrong annotations -> verify build + contig names before any cross-file op; liftOver deliberately.
- **Phred encoding wrong** (+33 vs +64) -> garbage quality filtering -> autodetect with `fastp`/FastQC; modern data is +33.
- **Not indexing** BAM/VCF/FASTA -> random-access tools fail -> `samtools index`, `tabix -p vcf`, `samtools faidx`.
- **Ignoring PCR/optical duplicates** -> inflated variant confidence -> markdup before calling.
- **Reverse-strand / RC errors** -> primers/reads on wrong strand -> always reverse-complement, check FLAG 0x10.
- **Batch effects** (sequencing run, library prep) confound biology -> randomize samples across batches; include batch covariate; check PCA for clustering by batch.
- **BLAST E-value misread** — E-value grows with DB size; low identity high E can be spurious -> filter by identity + coverage + E-value together.
- **Multiple testing** across thousands of genes/variants -> false positives -> Bonferroni/**Benjamini-Hochberg FDR**, report q-values.
- **Aligning across splice junctions with DNA aligner** for RNA-seq -> spurious clips -> use splice-aware **STAR**/**HISAT2** for RNA.
- **Trusting a single caller** -> caller-specific artifacts -> intersect callers or use truth sets (GIAB) to benchmark.
- **VCF multiallelic / non-normalized indels** break comparison -> `bcftools norm -m- -f ref.fa` (split + left-align) before merging/annotating.
- **Using TPM/FPKM as DE input** -> wrong statistics -> feed raw counts to DESeq2/edgeR; TPM only for visualization.
- **Low mapping rate / unexpected contamination** -> spurious results -> FastQC/screen against contaminant genomes; check adapter, species, rRNA.
- **Ignoring ploidy / heterozygosity** in calling or assembly -> collapsed/false variants -> set correct ploidy; use het-aware assemblers.
- **Reading FASTA line-wrapped seq naively** -> broken records -> parse with Biopython/pysam, never `readline` per base.
- **Confusing transcript vs gene IDs** (ENST vs ENSG) or version suffixes (`.3`) -> failed joins -> map IDs deliberately (biomaRt), strip/track versions consistently.
