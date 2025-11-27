import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import re
import warnings

warnings.filterwarnings('ignore')

# --- APP CONFIGURATION ---
st.set_page_config(page_title="MEE Graph Tool", page_icon="📈", layout="centered")

st.title("📈 Smart CT Report Generator")
st.markdown("""
**Instructions:**
1. Upload your daily report Excel/CSV file.
2. The system will **Detect Limits**, **Check Dates**, and **Flag Violations**.
3. Review the **Smart Analysis** dashboard below.
4. Download the PDF report.
""")
st.divider()

# --- LOGIC FUNCTIONS ---
def parse_limit_string(limit_str):
    if not isinstance(limit_str, str): return None, None
    clean = limit_str.strip().lower().replace("–", "-").replace("to", "-")
    
    # Range: "7.0-8.0"
    range_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', clean)
    if range_match: return float(range_match.group(1)), float(range_match.group(2))
    
    # Less than: "< 500"
    less_match = re.search(r'<\s*(\d+\.?\d*)', clean)
    if less_match: return 0.0, float(less_match.group(1))
    
    # More than: "> 50"
    more_match = re.search(r'>\s*(\d+\.?\d*)', clean)
    if more_match: return float(more_match.group(1)), None
    
    return None, None

def analyze_data_quality(df):
    report = {
        'date_gaps': [],
        'missing_values': {},
        'date_range': (None, None)
    }
    if df.empty or 'DATE' not in df.columns: return report

    df = df.sort_values('DATE')
    min_date, max_date = df['DATE'].min(), df['DATE'].max()
    report['date_range'] = (min_date, max_date)
    
    full_range = pd.date_range(start=min_date, end=max_date, freq='D')
    existing_dates = set(df['DATE'].dt.date)
    
    for date in full_range:
        if date.date() not in existing_dates:
            report['date_gaps'].append(date.date())

    for col in df.columns:
        if col == 'DATE': continue
        numeric_series = pd.to_numeric(df[col], errors='coerce')
        if numeric_series.isna().sum() > 0:
            report['missing_values'][col] = numeric_series.isna().sum()

    return report

def check_limit_violations(df, limits):
    violations = []
    
    for col in df.columns:
        if col not in limits or col == 'DATE': continue
        
        mn, mx = limits[col]['min'], limits[col]['max']
        series = pd.to_numeric(df[col], errors='coerce')
        
        # Check Max Violation
        if mx is not None:
            over = df[series > mx]
            for _, row in over.iterrows():
                violations.append({
                    "Date": row['DATE'].strftime('%d-%b-%Y'),
                    "Parameter": col,
                    "Value": row[col],
                    "Limit": f"Max {mx}",
                    "Status": "High 🔴"
                })

        # Check Min Violation
        if mn is not None:
            under = df[series < mn]
            for _, row in under.iterrows():
                violations.append({
                    "Date": row['DATE'].strftime('%d-%b-%Y'),
                    "Parameter": col,
                    "Value": row[col],
                    "Limit": f"Min {mn}",
                    "Status": "Low 🔵"
                })
                
    return pd.DataFrame(violations)

def process_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            raw = pd.read_csv(uploaded_file, header=None)
        else:
            raw = pd.read_excel(uploaded_file, header=None)
            
        # 1. Header Detection
        header_idx = 0
        keywords = ['parameters', 'date', 'ph', 'tds', 'hardness']
        for i in range(min(15, len(raw))):
            row_str = raw.iloc[i].astype(str).str.lower().tolist()
            if sum(1 for k in keywords if any(k in s for s in row_str)) >= 2:
                header_idx = i
                break
        
        # 2. Limit Detection
        extracted_limits = {}
        limit_idx = None
        for i in range(min(20, len(raw))):
            if 'control limit' in raw.iloc[i].astype(str).str.lower().values:
                limit_idx = i
                break
        
        if limit_idx is not None:
            raw_row = raw.iloc[limit_idx].tolist()
            header_row = raw.iloc[header_idx].tolist()
            for col, val in zip(header_row, raw_row):
                mn, mx = parse_limit_string(str(val))
                if mn is not None or mx is not None:
                    extracted_limits[str(col).strip()] = {'min': mn, 'max': mx}

        # 3. Load Data
        if uploaded_file.name.endswith('.csv'):
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=header_idx)
        else:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, header=header_idx)

        df.columns = [str(c).strip() for c in df.columns]

        # 4. Date Cleaning
        date_col = df.columns[0]
        for c in df.columns:
            if 'date' in c.lower() or 'parameters' in c.lower():
                date_col = c
                break
        
        df.rename(columns={date_col: 'DATE'}, inplace=True)
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
        df = df.dropna(subset=['DATE']).sort_values('DATE')
        return df, extracted_limits

    except Exception as e:
        st.error(f"Error: {e}")
        return None, None

def generate_pdf(df, limits):
    output_pdf = "Smart_Report.pdf"
    valid_cols = [c for c in df.columns if c != 'DATE' and not pd.to_numeric(df[c], errors='coerce').dropna().empty]

    if not valid_cols: return None

    with PdfPages(output_pdf) as pdf:
        chunks = [valid_cols[i:i+3] for i in range(0, len(valid_cols), 3)]

        for chunk in chunks:
            fig, axes = plt.subplots(3, 1, figsize=(11, 14))
            fig.subplots_adjust(hspace=0.5)
            if len(chunk) == 1: axes = [axes]

            for i, col in enumerate(chunk):
                ax = axes[i]
                series = pd.to_numeric(df[col], errors='coerce')
                plot_data = pd.DataFrame({'DATE': df['DATE'], 'VAL': series}).dropna()
                lim = limits.get(col, {'min': None, 'max': None})
                mn, mx = lim['min'], lim['max']

                ax.plot(plot_data['DATE'], plot_data['VAL'], marker='o', color='#1f77b4', linewidth=1.5, label='Data')
                if mn is not None: ax.axhline(mn, color='red', linestyle='--', label=f'Min {mn}')
                if mx is not None: ax.axhline(mx, color='green', linestyle='--', label=f'Max {mx}')
                
                lim_text = f"({mn} - {mx})" if (mn or mx) else ""
                ax.set_title(f"{col} {lim_text}", fontsize=12, fontweight='bold', pad=10)
                ax.grid(True, linestyle=':', alpha=0.6)
                ax.legend(loc='upper right')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

            if len(chunk) < 3:
                for k in range(len(chunk), 3): axes[k].axis('off')

            plt.tight_layout(rect=[0, 0, 1, 0.98])
            pdf.savefig(fig)
            plt.close(fig)
            
    return output_pdf

# --- MAIN INTERFACE ---
uploaded_file = st.file_uploader("📂 Upload CT Report File", type=['xlsx', 'csv'])

if uploaded_file is not None:
    with st.spinner('Analyzing Data...'):
        df, limits = process_file(uploaded_file)

    if df is not None and not df.empty:
        # Run Analyses
        quality = analyze_data_quality(df)
        violations_df = check_limit_violations(df, limits)

        # --- DASHBOARD UI ---
        st.subheader("📊 Smart Analysis Dashboard")
        
        # 1. Summary Metrics
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Days Found", len(df))
        with m2:
            st.metric("Missing Dates", len(quality['date_gaps']), delta_color="inverse")
        with m3:
            v_count = len(violations_df)
            st.metric("Limit Violations", v_count, delta_color="inverse" if v_count > 0 else "normal")

        # 2. Limit Violations Section
        if not violations_df.empty:
            st.error(f"⚠️ **Attention Needed:** {v_count} parameters crossed their limits.")
            
            # Find worst offender
            worst_param = violations_df['Parameter'].mode()[0]
            worst_count = violations_df[violations_df['Parameter'] == worst_param].shape[0]
            st.markdown(f"**Most Frequent Issue:** `{worst_param}` was out of spec **{worst_count} times**.")

            with st.expander("🔎 View Detailed Violation Report", expanded=True):
                st.dataframe(
                    violations_df.sort_values(['Parameter', 'Date']), 
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.success("✅ Excellent! All parameters are within control limits.")

        # 3. Data Quality Section
        with st.expander("🛠 Data Quality Checks"):
            if quality['date_gaps']:
                st.warning(f"Missing Dates: {', '.join([str(d) for d in quality['date_gaps']])}")
            else:
                st.write("Dates are continuous.")
                
            if quality['missing_values']:
                st.warning("Missing Values found in: " + ", ".join([f"{k} ({v})" for k,v in quality['missing_values'].items()]))
            else:
                st.write("No missing data values.")

        st.divider()
        
        # 4. Generate PDF Button
        if st.button("📄 Generate & Download PDF", type="primary"):
            with st.spinner('Rendering Graphs...'):
                pdf_path = generate_pdf(df, limits)
                if pdf_path:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="📥 Download Final Report",
                            data=f.read(),
                            file_name="Smart_CT_Report.pdf",
                            mime="application/pdf"
                        )
                    st.success("Report ready for download!")
