from typing import Dict, List
import streamlit as st
import pandas as pd
from io import StringIO
import re

import numpy

from dnachisel import *
from Bio import Seq, SeqIO
from streamlit_searchbox import st_searchbox
from thefuzz import process
from functools import reduce


# Note that this, which is gitignored, is also excluded from gcloud builds.
# For that reason, and cleanliness, that DB has been copied to a data/ directory.
# COCOPUTS_DB_FNAME = '220916_codon_analysis/o537-Refseq_species.tsv'
COCOPUTS_DB_FNAME = "data/cocoput_table.tsv"


# @st.experimental_memo
@st.experimental_singleton
def get_cocoput_organism_series():
    # df = pd.read_csv('220916_codon_analysis/220926_genome_codons.tsv', sep='\t', index_col=False)
    df = pd.read_csv(COCOPUTS_DB_FNAME, sep="\t", index_col=False)
    # df = pd.read_csv('220916_codon_analysis/o537-genbank_species.tsv', sep='\t', index_col=False)
    return pd.Series(
        df.apply(lambda r: f"{r['Species']} (TaxID: {r['Taxid']})", axis=1)
        .unique()
    )


@st.experimental_singleton
def get_cocoput_organism_list():
    return get_cocoput_organism_series().tolist()


def search_organisms(searchterm) -> List[str]:
    # print(f'search term: {searchterm}', flush=True)
    matches = get_cocoput_organism_series()
    matches = matches[reduce((lambda a, b: a & b), [matches.str.lower().str.contains(t.lower()) for t in searchterm.split()])]
    # for term in [t.lower() for t in searchterm.split()]:
    #     matches = matches[matches.str.contains(term)]
    if matches.shape[0] > 100:
        matches = matches.iloc[:100]
    # def matches_filter(item):
    #     item_lower = item.lower()
    #     for term in terms:
    #         if not term.contains(item_lower):
    #             return False
    #     return True
    # matches = [t for t in get_cocoput_organism_list() if matches_filter(t)]
    # matches = process.extract(searchterm, get_cocoput_organism_list(), 50)
    # matches = get_close_matches(searchterm, get_cocoput_organism_list(), 50)
    # print(matches, flush=True)
    return matches.tolist() #[match[0] for match in matches]


def get_taxid_from_cocoput_name(cocoput_name):
    rematch = re.match(r".*\(TaxID: (\d+)\)", cocoput_name)
    assert rematch, f"Somehow the cocoput name was poorly formatted, {cocoput_name}"
    return int(rematch.groups()[0])


AA_TO_CODON: Dict[str, List[str]] = {
    "*": ["TAA", "TAG", "TGA"],
    "A": ["GCA", "GCC", "GCG", "GCT"],
    "C": ["TGC", "TGT"],
    "D": ["GAC", "GAT"],
    "E": ["GAA", "GAG"],
    "F": ["TTC", "TTT"],
    "G": ["GGA", "GGC", "GGG", "GGT"],
    "H": ["CAC", "CAT"],
    "I": ["ATA", "ATC", "ATT"],
    "K": ["AAA", "AAG"],
    "L": ["CTA", "CTC", "CTG", "CTT", "TTA", "TTG"],
    "M": ["ATG"],
    "N": ["AAC", "AAT"],
    "P": ["CCA", "CCC", "CCG", "CCT"],
    "Q": ["CAA", "CAG"],
    "R": ["AGA", "AGG", "CGA", "CGC", "CGG", "CGT"],
    "S": ["AGC", "AGT", "TCA", "TCC", "TCG", "TCT"],
    "T": ["ACA", "ACC", "ACG", "ACT"],
    "V": ["GTA", "GTC", "GTG", "GTT"],
    "W": ["TGG"],
    "Y": ["TAC", "TAT"],
}


def convert_cocoputs_table_to_dnachisel(
    codon_table_counts: dict,
) -> Dict[str, Dict[str, float]]:
    new_codon_table: Dict[str, Dict[str, float]] = {}
    for aa in AA_TO_CODON:
        new_codon_table[aa] = {}
        codon_sum: int = sum([codon_table_counts[codon] for codon in AA_TO_CODON[aa]])
        for codon in AA_TO_CODON[aa]:
            new_codon_table[aa][codon] = round(codon_table_counts[codon] / codon_sum, 3)
    return new_codon_table


@st.experimental_memo
def get_codon_table_for_taxid(taxid):
    df = pd.read_csv(COCOPUTS_DB_FNAME, sep="\t", index_col=False)
    subset = df[df.Taxid == taxid]
    row = subset[subset["# CDS"] == subset["# CDS"].max()].iloc[0]
    codons = [a + b + c for a in "ATCG" for b in "ATCG" for c in "ATCG"]
    codon_table = {k: v for k, v in row.to_dict().items() if k in codons}
    return convert_cocoputs_table_to_dnachisel(codon_table)


st.set_page_config(page_title="BaseBuddy")
# st.header('''BaseBuddy''')

c1, c2, c3 = st.columns((1, 5, 1))
with c2:
    st.image("resources/logo/png/logo-no-background.png")  # , width=500

st.write(
    """
Recode genes for your target organism.

Enter your native coding sequence below.
"""
)


footer = """
<style>
  a:link , a:visited {
    color: blue;
    background-color: transparent;
    text-decoration: underline;
  }

  a:hover,  a:active {
    color: red;
    background-color: transparent;
    text-decoration: underline;
  }

  .footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: white;
    color: black;
    text-align: center;
  }
</style>
<div class="footer">
  <i>Powered by <a href="https://edinburgh-genome-foundry.github.io/DnaChisel/">DNA Chisel</a> and <a href="https://dnahive.fda.gov/dna.cgi?cmd=cuts_main">CoCoPUTs</a>.</i>
</div>
"""
st.markdown(footer, unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    optimization_method = st.radio(
        "Optimization Method",
        ["use_best_codon", "match_codon_usage", "harmonize_rca"],
        key="visibility",
        # help='Choose the optimization method, harmonize_rca is recommended.'
        # label_visibility=st.session_state.visibility,
        # disabled=st.session_state.disabled,
        # horizontal=st.session_state.horizontal,
    )

with col2:
    st.caption('target organism')
    # target_organism = st.selectbox("target organism", get_cocoput_organism_list())
    target_organism = (st_searchbox(
        search_organisms,
        key="target_searchbox",
    ) or "")
    # print(f'TARGET: {target_organism}', flush=True)

    target_taxid = get_taxid_from_cocoput_name(target_organism) if target_organism else None
    target_coding_table = get_codon_table_for_taxid(target_taxid) if target_taxid else None

    if optimization_method == "harmonize_rca":
        source_organism = st.selectbox("source organism", get_cocoput_organism_list())
        source_taxid = get_taxid_from_cocoput_name(source_organism)
        source_coding_table = get_codon_table_for_taxid(source_taxid)
    else:
        source_coding_table = None


original_fasta_str = st.text_area(
    "native coding sequence",
    ">gene\nATGAGTAGT",
    help=f"Input the native coding sequence.",
)
with StringIO(original_fasta_str) as fio:
    records = list(SeqIO.parse(fio, "fasta"))
if len(records) == 0:
    st.warning(f"Found zero valid records in text box, should have one.")
    st.stop()


with st.expander("Advanced Settings"):
    homopolycols = st.columns(4)
    with homopolycols[0]:
        poly_a_maxlength = st.number_input(
            "Poly As",
            value=9,
            min_value=1,
            max_value=15,
            step=1,
            help="TODO: write help text",
        )
    with homopolycols[1]:
        poly_t_maxlength = st.number_input(
            "Poly Ts",
            value=9,
            min_value=1,
            max_value=15,
            step=1,
            help="TODO: write help text",
        )
    with homopolycols[2]:
        poly_c_maxlength = st.number_input(
            "Poly Cs",
            value=6,
            min_value=1,
            max_value=15,
            step=1,
            help="TODO: write help text",
        )
    with homopolycols[3]:
        poly_g_maxlength = st.number_input(
            "Poly Gs",
            value=6,
            min_value=1,
            max_value=15,
            step=1,
            help="TODO: write help text",
        )

    hairpin_c1, hairpin_c2 = st.columns((1, 1))
    with hairpin_c1:
        hairpin_stem_size = st.number_input(
            "Hairpin Stem Size",
            value=10,
            min_value=1,
            max_value=100,
            step=1,
            help="TODO: write help text",
        )
    with hairpin_c2:
        hairpin_window = st.number_input(
            "Hairpin Window",
            value=100,
            min_value=50,
            max_value=500,
            step=1,
            help="TODO: write help text",
        )

# Do some input validation.
if not target_coding_table:
    st.warning("Must specify a target organism.")
    st.stop()
if optimization_method == "harmonize_rca":
    if not source_coding_table:
        st.warning("Must specify a source organism if using harmonize_rca method.")
        st.stop()
    codon_optimize_kwargs = {"original_codon_usage_table": source_coding_table}
else:
    codon_optimize_kwargs = {}

constraints_logs = []
objectives_logs = []
recodings = []
try:
    for record in records:
        numpy.random.seed(
            123
        )  # This will ensure that the result of the optimization is always the same
        problem = DnaOptimizationProblem(
            sequence=record,
            constraints=[
                UniquifyAllKmers(10, include_reverse_complement=True),
                AvoidHairpins(
                    stem_size=hairpin_stem_size, hairpin_window=hairpin_window
                ),
                AvoidPattern(str(poly_a_maxlength) + "xA"),
                AvoidPattern(str(poly_t_maxlength) + "xT"),
                AvoidPattern(str(poly_c_maxlength) + "xC"),
                AvoidPattern(str(poly_g_maxlength) + "xG"),
                AvoidPattern("NdeI_site"),
                AvoidPattern("XhoI_site"),
                AvoidPattern("SpeI_site"),
                AvoidPattern("BamHI_site"),
                AvoidPattern("BsaI_site"),
                EnforceGCContent(mini=0.3, maxi=0.75, window=50),
                EnforceTranslation(),
            ],
            objectives=[
                CodonOptimize(
                    method=optimization_method,
                    codon_usage_table=target_coding_table,
                    **codon_optimize_kwargs,
                )
            ],
        )

        problem.max_random_iters = 10000
        problem.resolve_constraints()
        problem.optimize()

        constraints_logs.append(problem.constraints_text_summary())
        objectives_logs.append(problem.objectives_text_summary())
        recodings.append(problem.sequence)

except Exception as e:
    st.warning(e)
    st.stop()


with st.expander("DNA Chisel Logs"):
    for log in constraints_logs + objectives_logs:
        st.text(log)

for record, recoding in zip(records, recodings):
    if optimization_method == 'harmonize_rca':
        notes = f'method: {optimization_method}, source_taxid: {source_taxid}, target_taxid: {target_taxid}'  
    else:
        notes = f'method: {optimization_method}, target_taxid: {target_taxid}'  
    st.text(f">{record.id} ({notes})\n{recoding}")
