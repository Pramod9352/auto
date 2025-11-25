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

st.title("📈 MEE CT Report Generator")
st.markdown("""
**Instructions:**
1. Upload your daily report Excel file.
2. The system automatically detects limits and parameters.
3. Download the professional PDF report below.
""")
st.divider()

# --- LOGIC FUNCTIONS ---
def parse_limit_string(limit_str):
    if not isinstance(limit_str, str): return None, None
    clean = limit_str.strip().lower().replace("–", "-").replace("to", "-")
    range_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', clean)
    if range_match: return float(range_match.group(1)), float(range_match.group(2))
    less_match = re.search(r'<\s*(\d+\.?\d*)', clean)
    if less_match: return 0.0, float(less_match.group(1))
    more_match = re.search(r'>\s*(\d+\.?\d*)', clean)
    if more_match: return float(more_match.group(1)), None
    return None, None

def process_file(uploaded_file):
    try:
        # Load File
        if uploaded_file.name.endswith('.csv'):
            raw = pd.read_csv(uploaded_file, header=None)
        else:
            raw = pd.read_excel(uploaded_file, header=None)
            
        # Detect Header
        header_idx = 0
        keywords = ['parameters', 'date', 'ph', 'tds', 'hardness', 'alkalinity']
        for i in range(min(15, len(raw))):
            row_str = raw.iloc[i].astype(str).str.lower().tolist()
            if sum(1 for k in keywords if any(k in s for s in row_str)) >= 2:
                header_idx = i
                break
        
        # Detect Limits
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

        # Reload Data
        if uploaded_file.name.endswith('.csv'):
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, header=header_idx)
        else:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, header=header_idx)

        df.columns = [str(c).strip() for c in df.columns]

        # Clean Dates
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
        st.error(f"Error reading file. Please make sure it is a standard MEE CT Excel file. Error: {e}")
        return None, None

def generate_pdf(df, limits):
    output_pdf = "Report.pdf"
    
    # Filter Valid Columns
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

                # Format
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=12))
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
                
                # Scale
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
    with st.spinner('Generating Report...'):
        df, limits = process_file(uploaded_file)
        
        if df is not None:
            pdf_path = generate_pdf(df, limits)
            
            if pdf_path:
                st.success("✅ Report Ready!")
                
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                    
                st.download_button(
                    label="📥 Click to Download PDF",
                    data=pdf_bytes,
                    file_name="MEE_Final_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )