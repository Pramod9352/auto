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

st.title("📈 CT Report Generator")
st.markdown("""
**Instructions:**
1. Upload your daily report Excel/CSV file.
2. **Review the Data Quality Analysis** below to spot missing dates or values.
3. Download the professional PDF report.
""")
st.divider()

# --- LOGIC FUNCTIONS ---
def parse_limit_string(limit_str):
    if not isinstance(limit_str, str): return None, None
    # normalize dashes and spaces
    clean = limit_str.strip().lower().replace("–", "-").replace("to", "-")
    
    # Range: "7.0-8.0" or "6 to 10"
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
    """
    Analyzes the dataframe for missing daily records and missing parameter values.
    """
    report = {
        'date_gaps': [],
        'missing_values': {},
        'total_days': 0,
        'date_range': (None, None)
    }

    if df.empty or 'DATE' not in df.columns:
        return report

    # 1. Date Sequence Analysis
    df = df.sort_values('DATE')
    min_date = df['DATE'].min()
    max_date = df['DATE'].max()
    report['date_range'] = (min_date, max_date)
    
    # Create a full range of daily dates expected
    full_range = pd.date_range(start=min_date, end=max_date, freq='D')
    report['total_days'] = len(full_range)
    
    # Identify dates present in the file
    existing_dates = set(df['DATE'].dt.date)
    
    # Find gaps
    for date in full_range:
        if date.date() not in existing_dates:
            report['date_gaps'].append(date.date())

    # 2. Parameter Data Analysis
    # Check each column (except DATE) for missing or non-numeric values
    for col in df.columns:
        if col == 'DATE': continue
        
        # Convert to numeric, forcing errors to NaN (this handles '-', 'Nil', empty, etc.)
        numeric_series = pd.to_numeric(df[col], errors='coerce')
        missing_count = numeric_series.isna().sum()
        
        if missing_count > 0:
            report['missing_values'][col] = missing_count

    return report

def process_file(uploaded_file):
    try:
        # Load File
        if uploaded_file.name.endswith('.csv'):
            raw = pd.read_csv(uploaded_file, header=None)
        else:
            raw = pd.read_excel(uploaded_file, header=None)
            
        # Detect Header
        # Look for a row containing typical keywords
        header_idx = 0
        keywords = ['parameters', 'date', 'ph', 'tds', 'hardness', 'alkalinity']
        for i in range(min(15, len(raw))):
            row_str = raw.iloc[i].astype(str).str.lower().tolist()
            # If at least 2 keywords match in this row, assume it's the header
            if sum(1 for k in keywords if any(k in s for s in row_str)) >= 2:
                header_idx = i
                break
        
        # Detect Limits (row usually labeled "CONTROL LIMIT")
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

        # Reload Data with correct header
        if uploaded_file.name.endswith('.csv'):
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=header_idx)
        else:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, header=header_idx)

        # Clean Column Names
        df.columns = [str(c).strip() for c in df.columns]

        # Identify Date Column
        date_col = df.columns[0]
        for c in df.columns:
            if 'date' in c.lower() or 'parameters' in c.lower():
                date_col = c
                break
        
        df.rename(columns={date_col: 'DATE'}, inplace=True)
        
        # Convert Dates and Clean Invalid Rows (metadata, units, empty lines)
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
        df = df.dropna(subset=['DATE']).sort_values('DATE')
        
        return df, extracted_limits

    except Exception as e:
        st.error(f"Error reading file. Please make sure it is a standard MEE CT file. Error: {e}")
        return None, None

def generate_pdf(df, limits):
    output_pdf = "Report.pdf"
    
    # Filter Valid Numeric Columns for Plotting
    valid_cols = []
    for col in df.columns:
        if col == 'DATE': continue
        if not pd.to_numeric(df[col], errors='coerce').dropna().empty:
            valid_cols.append(col)

    if not valid_cols:
        st.warning("File loaded, but no numeric data found to plot.")
        return None

    # Generate PDF
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

                # Plot
                ax.plot(plot_data['DATE'], plot_data['VAL'], marker='o', linestyle='-', color='#1f77b4', linewidth=1.5, label='Data')
                
                # Limits
                if mn is not None: ax.axhline(mn, color='red', linestyle='--', linewidth=1.5, label=f'Min ({mn})')
                if mx is not None: ax.axhline(mx, color='green', linestyle='--', linewidth=1.5, label=f'Max ({mx})')
                
                # Style
                lim_text = f"({mn} - {mx})" if (mn or mx) else ""
                ax.set_title(f"{col} {lim_text}", fontsize=11, fontweight='bold', pad=15)
                ax.grid(True, linestyle=':', alpha=0.6)
                ax.legend(loc='upper right', fontsize=8)

                # Format X-Axis
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=12))
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
                
                # Dynamic Y-Axis Scaling
                if not plot_data.empty:
                    vals = plot_data['VAL']
                    v_min = min(vals.min(), mn) if mn is not None else vals.min()
                    v_max = max(vals.max(), mx) if mx is not None else vals.max()
                    pad = (v_max - v_min) * 0.20
                    if pad == 0: pad = 1.0
                    ax.set_ylim(v_min - pad, v_max + pad)

            if len(chunk) < 3:
                for k in range(len(chunk), 3): axes[k].axis('off')

            plt.tight_layout(rect=[0, 0, 1, 0.98])
            pdf.savefig(fig)
            plt.close(fig)
            
    return output_pdf

# --- MAIN INTERFACE ---
uploaded_file = st.file_uploader("📂 Choose your file", type=['xlsx', 'csv'])

if uploaded_file is not None:
    # 1. Process File
    with st.spinner('Reading file...'):
        df, limits = process_file(uploaded_file)

    if df is not None and not df.empty:
        # 2. Analyze Data Quality
        quality = analyze_data_quality(df)
        
        st.subheader("🧐 Data Quality Analysis")
        
        # Layout: Columns for Dates vs Data
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📅 Date Coverage")
            start_str = quality['date_range'][0].strftime('%d-%b-%Y')
            end_str = quality['date_range'][1].strftime('%d-%b-%Y')
            st.info(f"**Range:** {start_str} to {end_str}")
            
            if quality['date_gaps']:
                st.error(f"**Missing Dates Detected ({len(quality['date_gaps'])}):**")
                # Show list of missing dates
                gap_df = pd.DataFrame({'Missing Dates': quality['date_gaps']})
                st.dataframe(gap_df, height=150, hide_index=True)
            else:
                st.success("✅ No missing dates (Sequence is complete).")

        with col2:
            st.markdown("#### 🧪 Data Integrity")
            if quality['missing_values']:
                st.warning(f"**Missing Data in {len(quality['missing_values'])} Parameters:**")
                st.caption("Count of missing/empty entries per parameter:")
                # Create a clean little table for missing values
                miss_df = pd.DataFrame(list(quality['missing_values'].items()), columns=['Parameter', 'Missing Count'])
                st.dataframe(miss_df, height=150, hide_index=True)
            else:
                st.success("✅ All parameter data is complete.")

        st.divider()

        # 3. Generate Report
        if st.button("Generate & Download PDF Report", type="primary"):
            with st.spinner('Plotting graphs...'):
                pdf_path = generate_pdf(df, limits)
                
                if pdf_path:
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                        
                    st.success("✅ Report Generated Successfully!")
                    st.download_button(
                        label="📥 Click here to Download PDF",
                        data=pdf_bytes,
                        file_name="MEE_Final_Report.pdf",
                        mime="application/pdf"
                    )
    elif df is not None and df.empty:
        st.error("The file was read, but no valid data rows (with dates) were found.")
