# 📈 Google Search Console CTR Opportunity Finder

This Python tool audits Google Search Console (GSC) export data to uncover high-impact traffic opportunities. Unlike generic tools, it calculates a custom **"Opportunity Score"** to prioritize pages based on potential traffic recovery, not just raw volume.

## 🚀 Features
1. **Custom Opportunity Algorithm:** Identifies "low-hanging fruit" by calculating missed clicks based on impressions vs. expected CTR.
2. **Benchmark Comparison:** Compares your actual CTR against a conservative SERP curve (Top 1 = 28%, Top 10 = 2.5%) to find underperforming pages.
3. **Dual Actionable Reporting:** Generates **two detailed CSVs** (`_pages_opportunities.csv` and `_queries_opportunities.csv`) to pinpoint issues at both the URL and Keyword level.
4. **Smart Filtering:** Automatically ignores queries with low statistical significance to prevent noise.

## 🛠️ How to use
1. **Export your data** from Google Search Console (Performance > Pages & Queries) as CSV files.
2. Install dependencies:
   `pip install pandas`
3. Run the script:
   `python ctr_optimizer.py --pages gsc_pages.csv --queries gsc_queries.csv`

### ⚡ Execution Example
```bash
python ctr_optimizer.py --pages "gsc_pages.csv" --queries "gsc_queries.csv" --out_prefix report
