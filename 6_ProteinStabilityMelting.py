#%% Imports
from utils import *
from Bio import SeqIO
import seaborn as sbn
plt.rcParams['pdf.fonttype'], plt.rcParams['ps.fonttype'] = 42, 42 #Make PDF text readable

#%% Import the genes names we're analyzing
def ccd_gene_names(id_list_like):
    '''Convert gene ID list to gene name list'''
    gene_info = pd.read_csv("input/processed/python/IdsToNames.csv", index_col=False, header=None, names=["gene_id", "name", "biotype", "description"])
    return gene_info[(gene_info["gene_id"].isin(id_list_like))]["name"]

def ccd_gene_lists(adata):
    '''Read in the published CCD genes / Diana's CCD / Non-CCD genes'''
    gene_info = pd.read_csv("input/processed/python/IdsToNames.csv", index_col=False, header=None, names=["gene_id", "name", "biotype", "description"])
    ccd_regev=pd.read_csv("input/processed/manual/ccd_regev.txt")    
    ccd=pd.read_csv("output/picklestxt/ccd_compartment_ensg.txt")#"input/processed/manual/ccd_genes.txt")
    nonccd=pd.read_csv("output/picklestxt/nonccd_compartment_ensg.txt")#("input/processed/manual/nonccd_genes.txt")
    ccd_regev_filtered = list(gene_info[(gene_info["name"].isin(ccd_regev["gene"])) & (gene_info["gene_id"].isin(adata.var_names))]["gene_id"])
    ccd_filtered = list(gene_info[(gene_info["name"].isin(ccd["gene"])) & (gene_info["gene_id"].isin(adata.var_names))]["gene_id"])
    nonccd_filtered = list(gene_info[(gene_info["name"].isin(nonccd["gene"])) & (gene_info["gene_id"].isin(adata.var_names))]["gene_id"])
    return ccd_regev_filtered, ccd_filtered, nonccd_filtered

ccdtranscript = np.load("output/pickles/ccdtranscript.npy", allow_pickle=True)
ccdprotein_transcript_regulated = np.load("output/pickles/ccdprotein_transcript_regulated.npy", allow_pickle=True)
ccdprotein_nontranscript_regulated = np.load("output/pickles/ccdprotein_nontranscript_regulated.npy", allow_pickle=True)
wp_ensg = np.load("output/pickles/wp_ensg.npy", allow_pickle=True)
ccd_comp = np.load("output/pickles/ccd_comp.npy", allow_pickle=True)
nonccd_comp = np.load("output/pickles/nonccd_comp.npy", allow_pickle=True)
bioccd = np.genfromtxt("input/processed/manual/biologically_defined_ccd.txt", dtype='str') # from mitotic structures
nonccd_comp_ensg = wp_ensg[nonccd_comp]
genes_analyzed = np.array(pd.read_csv("output/gene_names.csv")["gene"])
genes_analyzed = set(ccd_gene_names(genes_analyzed))

# Read in RNA-Seq data again and the CCD gene lists
dd = "All"
count_or_rpkm = "Tpms"
biotype_to_use="protein_coding"
adata, phases = read_counts_and_phases(dd, count_or_rpkm, False, biotype_to_use)
adata, phasesfilt = qc_filtering(adata, do_log_normalize= True, do_remove_blob=True)
ccd_regev_filtered, ccd_filtered, nonccd_filtered = ccd_gene_lists(adata)

genes_analyzed = set(ccd_gene_names(genes_analyzed))
nonccdtranscript = set(ccd_gene_names(adata.var_names[~ccdtranscript]))
ccdtranscript = set(ccd_gene_names(adata.var_names[ccdtranscript]))
ccdprotein_transcript_regulated = set(ccd_gene_names(adata.var_names[ccdprotein_transcript_regulated]))
ccdprotein_nontranscript_regulated = set(ccd_gene_names(adata.var_names[ccdprotein_nontranscript_regulated]))
ccd_regev_filtered = set(ccd_gene_names(ccd_regev_filtered))
nonccdprotein = set(ccd_gene_names(nonccd_comp_ensg))

#%% Let's take a look at protein stability
# Idea: Is there a difference in protein stability or turnover for the proteins that are
# transcriptionally regulated CCD vs non-transcriptionally regulated?
# Execution: Aggregate the results per protein, and then make a boxplot for each category
# Output: Boxplot for aggregated melting point results
all_temps, allnonccdtranscript, allccdtranscript, transcript_reg, nontranscr_reg, nonccd_temps = [],[],[],[],[],[]
atp, ant, att, trp, ntp, nnp = [],[], [], [], [],[]

def add_temps_and_names(filename, title, splitname):
    '''Adds melting temperature measurements from supp info files to lists'''
    df = pd.read_csv(filename, delimiter="\t")
    df["ProteinName"] = df["Protein ID"].str.extract("[A-Z0-9]+_(.+)") if splitname else df["Protein ID"]
    ccd_at_stab = df[df["ProteinName"].isin(ccdtranscript)]
    ccd_nt_stab = df[df["ProteinName"].isin(nonccdtranscript)]
    ccd_t_stab = df[df["ProteinName"].isin(ccdprotein_transcript_regulated)]
    ccd_n_stab = df[df["ProteinName"].isin(ccdprotein_nontranscript_regulated)]
    nonccd_stab = df[df["ProteinName"].isin(nonccdprotein)]

    notna = pd.notna(df["Melting point [°C]"])
    all_temps.extend(df[notna]["Melting point [°C]"])
    allccdtranscript.extend(ccd_at_stab[notna]["Melting point [°C]"])
    allnonccdtranscript.extend(ccd_nt_stab[notna]["Melting point [°C]"])
    transcript_reg.extend(ccd_t_stab[notna]["Melting point [°C]"])
    nontranscr_reg.extend(ccd_n_stab[notna]["Melting point [°C]"])
    nonccd_temps.extend(nonccd_stab[notna]["Melting point [°C]"])

    atp.extend(df[notna]["ProteinName"])
    att.extend(ccd_at_stab[notna]["ProteinName"])
    ant.extend(ccd_nt_stab[notna]["ProteinName"])
    trp.extend(ccd_t_stab[notna]["ProteinName"])
    ntp.extend(ccd_n_stab[notna]["ProteinName"])
    nnp.extend(nonccd_stab[notna]["ProteinName"])

def avg_prot_temps(temps, proteinNames):
    '''Finds median of the measurements from the same protein'''
    aaa = []
    ppp = []
    for i in range(len(temps)):
        df = pd.DataFrame({"name" : proteinNames[i], "temps": temps[i]})
        med = df.groupby("name")["temps"].median()
        aaa.append(list(med))
        ppp.append(list(med.index))
    result = aaa
    result.extend(ppp)
    return result

def stat_tests(title):
    results = ""
    results += f"{title} statistical tests\n"
    results += "Testing whether transcript reg. CCD melting points are different than non-transcript reg. CCD\n"
    results += f"{np.mean(transcript_reg)} +/- {np.std(transcript_reg)}: Transcript Reg. CCD (mean, std)\n"
    results += f"{np.mean(nontranscr_reg)} +/- {np.std(nontranscr_reg)}: Non-Transcript Reg. CCD (mean, std)\n"
    results += f"{np.median(transcript_reg)}: Transcript Reg. CCD (median)\n"
    results += f"{np.median(nontranscr_reg)}: Non-Transcript Reg. CCD (median)\n"
    results += f"{scipy.stats.ttest_ind(transcript_reg, nontranscr_reg)}: two sided t-test\n"
    results += f"{scipy.stats.kruskal(transcript_reg, nontranscr_reg)}: two sided kruskal\n"
    results += "\n"
    results += "Testing whether non-transcript reg. CCD is different than all proteins\n"
    results += f"{np.mean(all_temps)} +/- {np.std(all_temps)}: All Proteins (mean, std)\n"
    results += f"{np.mean(nontranscr_reg)} +/- {np.std(nontranscr_reg)}: Non-Transcript Reg. CCD (mean, std)\n"
    results += f"{np.median(all_temps)}: All Proteins (median)\n"
    results += f"{np.median(nontranscr_reg)}: Non-Transcript Reg. CCD (median)\n"
    results += f"{scipy.stats.ttest_ind(all_temps, nontranscr_reg)}: two sided t-test\n"
    results += f"{scipy.stats.kruskal(all_temps, nontranscr_reg)}: two sided kruskal\n"
    results += "\n"
    results += "Testing whether transcript reg. CCD is different than all proteins\n"
    results += f"{np.mean(all_temps)} +/- {np.std(all_temps)}: All Proteins (mean, std)\n"
    results += f"{np.mean(transcript_reg)} +/- {np.std(transcript_reg)}: Transcript Reg. CCD (mean, std)\n"
    results += f"{np.median(all_temps)}: All Proteins (median)\n"
    results += f"{np.median(transcript_reg)}: Transcript Reg. CCD (median)\n"
    results += f"{scipy.stats.ttest_ind(all_temps, transcript_reg)}: two sided t-test\n"
    results += f"{scipy.stats.kruskal(all_temps, transcript_reg)}: two sided kruskal\n"
    results += "\n"
    results += "Testing whether transcript reg. CCD is different than all transcript CCD\n"
    results += f"{np.mean(allccdtranscript)} +/- {np.std(allccdtranscript)}: all transcript CCD Proteins (mean, std)\n"
    results += f"{np.mean(transcript_reg)} +/- {np.std(transcript_reg)}: Transcript Reg. CCD (mean, std)\n"
    results += f"{np.median(allccdtranscript)}: all transcript CCD Proteins (median)\n"
    results += f"{np.median(transcript_reg)}: Transcript Reg. CCD (median)\n"
    results += f"{scipy.stats.ttest_ind(allccdtranscript, transcript_reg)}: two sided t-test\n"
    results += f"{scipy.stats.kruskal(allccdtranscript, transcript_reg)}: two sided kruskal\n"
    results += "\n"
    results += "Testing whether non-transcript reg. CCD is different than all transcript CCD\n"
    results += f"{np.mean(allccdtranscript)} +/- {np.std(allccdtranscript)}: all transcript CCD Proteins (mean, std)\n"
    results += f"{np.mean(nontranscr_reg)} +/- {np.std(nontranscr_reg)}: Non-Transcript Reg. CCD (mean, std)\n"
    results += f"{np.median(allccdtranscript)}: all transcript CCD Proteins (median)\n"
    results += f"{np.median(nontranscr_reg)}: Non-Transcript Reg. CCD (median)\n"
    results += f"{scipy.stats.ttest_ind(allccdtranscript, nontranscr_reg)}: two sided t-test\n"
    results += f"{scipy.stats.kruskal(allccdtranscript, nontranscr_reg)}: two sided kruskal\n"
    results += "\n"
    results += "Testing whether transcript reg. CCD is different than non-CCD\n"
    results += f"{np.mean(nonccd_temps)} +/- {np.std(nonccd_temps)}: Non-CCD Proteins (mean, std)\n"
    results += f"{np.mean(transcript_reg)} +/- {np.std(transcript_reg)}: Transcript Reg. CCD (mean, std)\n"
    results += f"{np.median(nonccd_temps)}: Non-CCD Proteins (median)\n"
    results += f"{np.median(transcript_reg)}: Transcript Reg. CCD (median)\n"
    results += f"{scipy.stats.ttest_ind(nonccd_temps, transcript_reg)}: two sided t-test\n"
    results += f"{scipy.stats.kruskal(nonccd_temps, transcript_reg)}: two sided kruskal\n"
    results += "\n"
    results += "Testing whether nontranscript reg. CCD is different than non-CCD\n"
    results += f"{np.mean(nonccd_temps)} +/- {np.std(nonccd_temps)}: Non-CCD Proteins (mean, std)\n"
    results += f"{np.mean(nontranscr_reg)} +/- {np.std(nontranscr_reg)}: Non-Transcript Reg. CCD (mean, std)\n"
    results += f"{np.median(nonccd_temps)}: Non-CCD Proteins (median)\n"
    results += f"{np.median(nontranscr_reg)}: Non-Transcript Reg. CCD (median)\n"
    results += f"{scipy.stats.ttest_ind(nonccd_temps, nontranscr_reg)}: two sided t-test\n"
    results += f"{scipy.stats.kruskal(nonccd_temps, nontranscr_reg)}: two sided kruskal\n"
    results += "\n"
    return results

def temp_hist(title):
    '''Generates a histogram of melting points with bins normalized to 1'''
    bins=np.histogram(np.hstack((all_temps, transcript_reg, nontranscr_reg, nonccd_temps)), bins=40)[1] #get the bin edges
    plt.hist(all_temps, bins=bins, weights=weights(all_temps), color="#3753A4", alpha=0.5, label="All Proteins")
    plt.hist(transcript_reg, bins=bins, weights=weights(transcript_reg), color="#FF0000", alpha=0.5, label="Transcript Reg. CCD")
    plt.hist(nontranscr_reg, bins=bins, weights=weights(nontranscr_reg), color="#2CE100", alpha=0.6, label="Non-Transcript Reg. CCD")
    plt.hist(nonccd_temps, bins=bins, weights=weights(nonccd_temps), color="#2CE100", alpha=0.6, label="Non-CCD")
    plt.legend(loc="upper right")
    plt.xlabel("Melting Point (°C)")
    plt.title(title)
    return stat_tests(title)
  

# Aggregate histogram
all_temps, transcript_reg, nontranscr_reg, nonccd_temps = [],[],[], []
atp, trp, ntp, nnp = [], [], [], []
add_temps_and_names("C:\\Users\\antho\\Dropbox\\ProjectData\\ProteinStability\\A549_R1.tsv", "A549_R1", True)
add_temps_and_names("C:\\Users\\antho\\Dropbox\\ProjectData\\ProteinStability\\A549_R2.tsv", "A549_R2", True)
add_temps_and_names("C:\\Users\\antho\\Dropbox\\ProjectData\\ProteinStability\\HEK293_R1.tsv", "HEK293_R1", True)
add_temps_and_names("C:\\Users\\antho\\Dropbox\\ProjectData\\ProteinStability\\HEK293_R2.tsv", "HEK293_R2", True)
add_temps_and_names("C:\\Users\\antho\\Dropbox\\ProjectData\\ProteinStability\\HepG2_R1.tsv", "HepG2_R1", False)
add_temps_and_names("C:\\Users\\antho\\Dropbox\\ProjectData\\ProteinStability\\HepG2_R2.tsv", "HepG2_R2", False)
add_temps_and_names("C:\\Users\\antho\\Dropbox\\ProjectData\\ProteinStability\\HepG2_R3.tsv", "HepG2_R3", False)
all_temps, transcript_reg, nontranscr_reg, nonccd_temps, atp, trp, ntp, nnp = avg_prot_temps([all_temps, transcript_reg, nontranscr_reg, nonccd_temps], [atp, trp, ntp, nnp])
statsresults = temp_hist("Aggregated Melting Points")
plt.savefig("figures/ProteinMeltingPointsMedianed.png")
plt.show()
plt.close()

pd.DataFrame({
    "protein_name":atp,
    "median_melting_point":all_temps,
    "transcript_reg":np.isin(atp, trp),
    "nontranscr_reg":np.isin(atp, ntp)}).to_csv("output/MedianMeltingPoints.csv",index=False)

# Boxplots
plt.figure(figsize=(10,10))
mmmm = np.concatenate((all_temps, transcript_reg, nontranscr_reg, nonccd_temps))
cccc = (["All Proteins"] * len(all_temps))
cccc.extend(["Transcript's\nReg\nCCD"] * len(transcript_reg))
cccc.extend(["Non-Transcript\nReg\nCCD"] * len(nontranscr_reg))
cccc.extend(["Non-CCD"] * len(nonccd_temps))
boxplot = sbn.boxplot(x=cccc, y=mmmm, showfliers=True)
boxplot.set_xlabel("Protein Set", size=36,fontname='Arial')
boxplot.set_ylabel("Melting Point (°C)", size=36,fontname='Arial')
boxplot.tick_params(axis="both", which="major", labelsize=16) 
plt.savefig("figures/ProteinMeltingPointBox.pdf")
plt.show()
plt.close()

plt.figure(figsize=(10,10))
mmmm = np.concatenate((all_temps, allccdtranscript, allnonccdtranscript, transcript_reg, nontranscr_reg, nonccd_temps))
cccc = (["All Proteins"] * len(all_temps))
cccc.extend(["All\nTranscript\nCCD"] * len(allccdtranscript))
cccc.extend(["All\nTranscript\nNon-CCD"] * len(allnonccdtranscript))
cccc.extend(["Transcript\nReg\nCCD"] * len(transcript_reg))
cccc.extend(["Non-Transcript\nReg\nCCD"] * len(nontranscr_reg))
cccc.extend(["Non-CCD"] * len(nonccd_temps))
boxplot = sbn.boxplot(x=cccc, y=mmmm, showfliers=False)
boxplot = sbn.stripplot(x=cccc, y=mmmm)#, showfliers=False)
boxplot.set_ylabel("Melting Point (°C)", size=36,fontname='Arial')
boxplot.tick_params(axis="both", which="major", labelsize=18) 
plt.savefig("figures/ProteinMeltingPointBoxSelect.pdf")
plt.show()
plt.close()

plt.figure(figsize=(10,10))
mmmm = np.concatenate((all_temps, transcript_reg, nontranscr_reg))
cccc = (["All Proteins"] * len(all_temps))
cccc.extend(["Transcript\nRegulated\nCCD Proteins"] * len(transcript_reg))
cccc.extend(["Non-Transcript\nRegulated\nCCD Proteins"] * len(nontranscr_reg))
boxplot = sbn.boxplot(x=cccc, y=mmmm, showfliers=False)
# boxplot = sbn.stripplot(x=cccc, y=mmmm, alpha=0.2, color=".3", size=7, jitter=0.25)#, showfliers=False)
boxplot.set_ylabel("Melting Point (°C)", size=36,fontname='Arial')
boxplot.tick_params(axis="both", which="major", labelsize=22) 
plt.savefig("figures/ProteinMeltingPointBoxSelect2.pdf")
plt.show()
plt.close()

print(statsresults)
with open("output/meltingpointresults.txt", 'w') as file:
    file.write(statsresults)

#%% Pickle the results
np_save_overwriting("output/temperatures.all_temps.npy",all_temps)
np_save_overwriting("output/temperatures.all_temp_prot.npy",atp)
np_save_overwriting("output/temperatures.transcript_reg.npy",transcript_reg)
np_save_overwriting("output/temperatures.transcript_reg_prot.npy",trp)
np_save_overwriting("output/temperatures.nontranscr_reg.npy",nontranscr_reg)
np_save_overwriting("output/temperatures.nontranscript_reg_prot.npy",ntp)
np_save_overwriting("output/temperatures.nonccd_temps.npy",nonccd_temps)
np_save_overwriting("output/temperatures.nonccd_temps_prot.npy",nnp)

#%% [markdown]
# The replicates do look better with the melting points, and the difference is
# significant between transcript reg CCD and non-transcript reg CCD. However, the
# non-transcript regulated CCD proteins are more similar to all proteins on average,
# and that difference is not significant.
