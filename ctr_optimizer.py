import argparse
import pandas as pd

# Simple target CTR benchmarks by average position bucket (conservative)
# You can tweak these later based on your niche and SERP type.
def target_ctr_for_position(pos: float) -> float:
    if pos <= 1.0: return 0.28
    if pos <= 2.0: return 0.15
    if pos <= 3.0: return 0.10
    if pos <= 4.0: return 0.07
    if pos <= 5.0: return 0.055
    if pos <= 6.0: return 0.045
    if pos <= 7.0: return 0.040
    if pos <= 8.0: return 0.035
    if pos <= 9.0: return 0.030
    if pos <= 10.0: return 0.025
    if pos <= 15.0: return 0.020
    return 0.015

def clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize common GSC export column names
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # Common variants:
    # "Clicks", "Impressions", "CTR", "Position"
    # Sometimes "ctr" is already decimal or percent string.
    rename_map = {}
    if "clicks" not in df.columns:
        for c in df.columns:
            if "click" in c:
                rename_map[c] = "clicks"
                break
    if "impressions" not in df.columns:
        for c in df.columns:
            if "impression" in c:
                rename_map[c] = "impressions"
                break
    if "ctr" not in df.columns:
        for c in df.columns:
            if c == "click through rate" or "ctr" in c:
                rename_map[c] = "ctr"
                break
    if "position" not in df.columns:
        for c in df.columns:
            if "position" in c:
                rename_map[c] = "position"
                break

    df = df.rename(columns=rename_map)

    # Convert to numeric
    for col in ["clicks", "impressions", "position"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "ctr" in df.columns:
        # Handle "12.3%" or "0.123"
        def parse_ctr(x):
            if pd.isna(x): return 0.0
            s = str(x).strip()
            if s.endswith("%"):
                try: return float(s[:-1]) / 100.0
                except: return 0.0
            try:
                v = float(s)
                # If it looks like percent (12.3) not decimal, convert
                if v > 1.0: return v / 100.0
                return v
            except:
                return 0.0
        df["ctr"] = df["ctr"].apply(parse_ctr).fillna(0.0)

    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="GSC Pages export CSV (ex: gsc_pages.csv)")
    ap.add_argument("--queries", required=True, help="GSC Queries export CSV (ex: gsc_queries.csv)")
    ap.add_argument("--out_prefix", default="ctr", help="Output prefix")
    ap.add_argument("--min_impressions", type=int, default=100, help="Min impressions to consider")
    ap.add_argument("--max_ctr", type=float, default=0.02, help="Max CTR (decimal) to consider, ex 0.02 = 2%")
    ap.add_argument("--pos_min", type=float, default=5.0, help="Min position")
    ap.add_argument("--pos_max", type=float, default=15.0, help="Max position")
    args = ap.parse_args()

    pages = pd.read_csv(args.pages)
    queries = pd.read_csv(args.queries)

    pages = clean_cols(pages)
    queries = clean_cols(queries)

    # Detect dimension column for pages/queries
    # Pages export usually has "page" column, queries export has "query" column
    dim_page = None
    for c in pages.columns:
        if c in ("page", "pages", "url"):
            dim_page = c
            break
    if dim_page is None:
        # fallback: first non-metric column
        dim_page = next((c for c in pages.columns if c not in ("clicks","impressions","ctr","position")), None)

    dim_query = None
    for c in queries.columns:
        if c in ("query", "queries", "keyword"):
            dim_query = c
            break
    if dim_query is None:
        dim_query = next((c for c in queries.columns if c not in ("clicks","impressions","ctr","position")), None)

    if dim_page is None or dim_query is None:
        raise SystemExit("Could not detect dimension columns. Ensure exports include Page and Query columns.")

    pages[dim_page] = pages[dim_page].astype(str).str.strip()
    queries[dim_query] = queries[dim_query].astype(str).str.strip()

    # Filter pages for opportunity window
    p = pages[
        (pages["impressions"] >= args.min_impressions) &
        (pages["ctr"] <= args.max_ctr) &
        (pages["position"] >= args.pos_min) &
        (pages["position"] <= args.pos_max)
    ].copy()

    if p.empty:
        print("No pages matched the filters. Try lowering min_impressions or increasing max_ctr.")
        out_path = f"{args.out_prefix}_pages_opportunities.csv"
        p.to_csv(out_path, index=False)
        return

    # Add target CTR and opportunity metrics
    p["target_ctr"] = p["position"].apply(target_ctr_for_position)
    p["ctr_gap"] = (p["target_ctr"] - p["ctr"]).clip(lower=0.0)
    p["missed_clicks_est"] = (p["impressions"] * p["ctr_gap"]).round(2)

    # Opportunity score: missed clicks estimated, weighted by impressions
    p["opportunity_score"] = (p["missed_clicks_est"] * (1 + (p["impressions"] / 1000.0))).round(2)

    p = p.sort_values(["opportunity_score", "impressions"], ascending=False)

    # Best queries to review overall (not page specific due to export limitations)
    q = queries[
        (queries["impressions"] >= args.min_impressions) &
        (queries["ctr"] <= args.max_ctr) &
        (queries["position"] >= args.pos_min) &
        (queries["position"] <= args.pos_max)
    ].copy()

    q["target_ctr"] = q["position"].apply(target_ctr_for_position)
    q["ctr_gap"] = (q["target_ctr"] - q["ctr"]).clip(lower=0.0)
    q["missed_clicks_est"] = (q["impressions"] * q["ctr_gap"]).round(2)
    q["opportunity_score"] = (q["missed_clicks_est"] * (1 + (q["impressions"] / 1000.0))).round(2)
    q = q.sort_values(["opportunity_score", "impressions"], ascending=False)

    out_pages = f"{args.out_prefix}_pages_opportunities.csv"
    out_queries = f"{args.out_prefix}_queries_opportunities.csv"

    p.to_csv(out_pages, index=False)
    q.to_csv(out_queries, index=False)

    print("Done.")
    print("Outputs:")
    print(" -", out_pages)
    print(" -", out_queries)

if __name__ == "__main__":
    main()
