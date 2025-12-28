Offline MVP Runbook

Goal
- Run the full pipeline without live search using local HTML/PDF/TXT sources.
- Produce: run report, provenance.json, and populated SQLite tables (sources, propositions, claim_groups, annotations).

Quick Start (Offline)
1) Gather sources (see Notebook TODOs below) and save them under a folder, e.g. ./offline_sources/.
2) Run the pipeline using local files:
   research-agent run --config agent.yaml --input-dir offline_sources "<your question>"

Alternative: Use a source list file
- Create a newline-delimited list of local paths (or file:// URIs):
  offline_sources/sources.txt
- Example command:
  research-agent run --config agent.yaml --sources offline_sources/sources.txt "<your question>"

What to Check
- runs/<run_id>/report.md exists and includes claims + evidence matrix.
- runs/<run_id>/provenance.json references local file:// URLs and run sources.
- data/agent.db has rows in source_docs, propositions, annotations, claim_groups, run_sources.

Notebook TODOs (Manual Downloads)
- Save each URL as HTML or PDF with the suggested filename in offline_sources/.
- Goal: mix long HTML pages, tables, and multi-page PDFs.

[ ] ipcc_ar6_wgi_spm.pdf
    URL: https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_SPM_final.pdf
    Notes: Long PDF with quantitative claims and tables.

[ ] cdc_databrief_obesity.pdf
    URL: https://www.cdc.gov/nchs/data/databriefs/db472.pdf
    Notes: Short PDF with numeric claims and charts.

[ ] niddk_diabetes_stats.html
    URL: https://www.niddk.nih.gov/health-information/health-statistics/diabetes-statistics
    Notes: Long HTML with multiple numeric claims.

[ ] mmwr_antibiotic_resistance.html
    URL: https://www.cdc.gov/mmwr/volumes/72/wr/mm7206a3.htm
    Notes: HTML with summarized findings and numbers.

[ ] ema_comirnaty_product_info.pdf
    URL: https://www.ema.europa.eu/en/documents/product-information/comirnaty-epar-product-information_en.pdf
    Notes: Large PDF with dosage/effectiveness statements.

[ ] pmc_open_access_rct.html
    URL: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7158298/
    Notes: Open-access clinical trial article in HTML.

Suggested Question Prompts
- "What do these sources say about prevalence or risk trends?"
- "Summarize quantitative claims about effectiveness and safety."
- "Extract any statements about population-level outcomes and compare them."
