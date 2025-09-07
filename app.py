import streamlit as st
import pandas as pd
from datetime import datetime
from collections import defaultdict
from thefuzz import fuzz

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="HiLabs Provider Data Quality Dashboard",
    page_icon="⚕️"
)

# --- Constants ---
HACKATHON_DATE = datetime(2025, 9, 7).date()

# --- Caching Data Loading ---
@st.cache_data
def load_data():
    """
    Loads all necessary CSV files into pandas DataFrames.
    This function is cached to improve performance.
    """
    try:
        roster = pd.read_csv('provider_roster_with_errors.csv')
        ca_licenses = pd.read_csv('ca_medical_license_database.csv', low_memory=False)
        ny_licenses = pd.read_csv('ny_medical_license_database.csv', low_memory=False)
        npi_registry = pd.read_csv('mock_npi_registry.csv', low_memory=False)
        return roster, ca_licenses, ny_licenses, npi_registry
    except FileNotFoundError as e:
        st.error(f"Error: {e}. Please make sure all required CSV files are in the same directory as the app.")
        return None, None, None, None

# --- Analytical Functions ---

# 1. Data Quality Assessment & Standardization
def analyze_phone_numbers(df):
    """
    Standardizes and validates phone numbers.
    Returns a DataFrame of providers with formatting issues.
    """
    # Remove all non-numeric characters
    df['standardized_phone'] = df['practice_phone'].astype(str).str.replace(r'\D', '', regex=True)
    # Flag issues: not 10 digits or contains non-digit characters after cleaning
    df['phone_issue'] = df['standardized_phone'].apply(lambda x: len(x) != 10)
    phone_issues_df = df[df['phone_issue']][['provider_id', 'full_name', 'practice_phone', 'primary_specialty']]
    return phone_issues_df

def find_missing_npi(df):
    """
    Finds providers with missing NPI numbers.
    Returns a DataFrame of providers missing NPIs.
    """
    missing_npi_df = df[df['npi'].isnull()][['provider_id', 'full_name', 'primary_specialty']]
    return missing_npi_df

# 2. License Validation
def validate_licenses(roster_df, ca_df, ny_df):
    """
    Cross-references provider licenses with state databases.
    Returns a DataFrame of providers with expired licenses.
    """
    # Clean license numbers for merging
    roster_df['license_number_clean'] = roster_df['license_number'].astype(str).str.strip()
    ca_df['license_number_clean'] = ca_df['license_number'].astype(str).str.strip()
    ny_df['license_number_clean'] = ny_df['license_number'].astype(str).str.strip()

    # Merge with CA licenses
    ca_merged = pd.merge(
        roster_df[roster_df['license_state'] == 'CA'],
        ca_df[['license_number_clean', 'status', 'expiration_date']],
        on='license_number_clean',
        how='left',
        suffixes=('_roster', '_state')
    )

    # Merge with NY licenses
    ny_merged = pd.merge(
        roster_df[roster_df['license_state'] == 'NY'],
        ny_df[['license_number_clean', 'status', 'expiration_date']],
        on='license_number_clean',
        how='left',
        suffixes=('_roster', '_state')
    )

    # Combine results
    all_licensed = pd.concat([ca_merged, ny_merged], ignore_index=True)

    # Identify expired licenses
    all_licensed['expiration_date'] = pd.to_datetime(all_licensed['expiration_date'], errors='coerce').dt.date
    expired_mask = (all_licensed['expiration_date'] < HACKATHON_DATE) | (all_licensed['status'].str.lower() == 'expired')
    
    expired_df = all_licensed[expired_mask]
    
    # Select relevant columns for display
    expired_display = expired_df[[
        'provider_id', 'full_name', 'license_number', 'license_state', 'status', 'expiration_date'
    ]].rename(columns={'status': 'State DB Status', 'expiration_date': 'State DB Expiration'})
    
    return expired_display.drop_duplicates()


# 3. Provider Deduplication
def find_duplicates(df, score_cutoff=90):
    """
    Identifies potential duplicate provider records using fuzzy name matching.
    Blocks on last name and specialty, then scores on full name.
    """
    df['last_name_norm'] = df['last_name'].str.lower().str.strip()
    df['full_name_norm'] = df['full_name'].str.lower().str.strip()
    
    potential_duplicates = defaultdict(list)
    
    # Group by last name and specialty to create blocks for comparison
    grouped = df.groupby(['last_name_norm', 'primary_specialty'])
    
    duplicate_clusters = []
    
    for _, group in grouped:
        if len(group) > 1:
            indices = group.index.tolist()
            matched_indices = set()
            
            for i in range(len(indices)):
                if indices[i] in matched_indices:
                    continue
                
                current_cluster = [indices[i]]
                for j in range(i + 1, len(indices)):
                    if indices[j] in matched_indices:
                        continue
                    
                    name1 = df.loc[indices[i], 'full_name_norm']
                    name2 = df.loc[indices[j], 'full_name_norm']
                    
                    # Use token_set_ratio for better matching on names with initials
                    score = fuzz.token_set_ratio(name1, name2)
                    
                    if score >= score_cutoff:
                        current_cluster.append(indices[j])
                        matched_indices.add(indices[j])
                
                if len(current_cluster) > 1:
                    duplicate_clusters.append(current_cluster)
                    matched_indices.update(current_cluster)
                        
    return duplicate_clusters

# --- Helper Functions ---
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- Streamlit UI ---

# Main Title
st.title("⚕️ HiLabs Provider Data Quality Analytics Dashboard")
st.markdown(f"Analysis performed relative to **{HACKATHON_DATE.strftime('%B %d, %Y')}**.")

import re
# Load data and show a spinner
with st.spinner('Loading and analyzing provider data...'):
    roster, ca_licenses, ny_licenses, npi_registry = load_data()

missing_npi = roster[roster['npi'].isna()]

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def find_phone_number_formatting_issues(roster_df):
    try:
        phone_regex = re.compile(r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$')
        df_copy = roster_df.copy()
        df_copy['practice_phone_str'] = df_copy['practice_phone'].astype(str)
        formatting_issues = df_copy[
            ~df_copy['practice_phone_str'].str.match(phone_regex, na=False) &
            df_copy['practice_phone'].notna()
        ]
        return formatting_issues[['provider_id', 'full_name', 'practice_phone']]
    except Exception as e:
        st.error(f"Error in find_phone_number_formatting_issues: {e}")
        return pd.DataFrame()
    
# Check if data loading was successful
if roster is not None:
    # --- Perform all analyses ---
    phone_issues = find_phone_number_formatting_issues(roster.copy())
    missing_npi = find_missing_npi(roster.copy())
    expired_licenses = validate_licenses(roster.copy(), ca_licenses.copy(), ny_licenses.copy())
    duplicate_clusters = find_duplicates(roster.copy())
    
    # --- Sidebar Navigation ---
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard Overview", "Duplicate Providers", "License Validation", "Data Formatting Issues"])

    # --- Page 1: Dashboard Overview ---
    if page == "Dashboard Overview":
        st.header("📊 Dashboard Overview")
        st.markdown("This dashboard provides a high-level summary of the data quality issues found in the provider roster.")
        
        # --- Metrics Calculation ---
        total_providers = len(roster)
        num_phone_issues = len(phone_issues)
        num_missing_npi = len(missing_npi)
        num_expired_licenses = len(expired_licenses)
        num_duplicates = sum(len(cluster) for cluster in duplicate_clusters)

        total_issues = num_phone_issues + num_missing_npi + num_expired_licenses + num_duplicates
        
        # Calculate Data Quality Score
        fields_checked = total_providers * 4  # Checking 4 aspects: phone, npi, license, uniqueness
        quality_score = ((fields_checked - total_issues) / fields_checked) * 100 if fields_checked > 0 else 0

        # Display KPIs
        st.subheader("Key Performance Indicators (KPIs)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Overall Data Quality Score", f"{quality_score:.2f}%", delta_color="inverse")
        col2.metric("Total Providers Analyzed", f"{total_providers}")
        col3.metric("Total Data Issues Found", f"{total_issues}", help="Sum of all identified data quality problems.")
        
        st.divider()

        st.subheader("Breakdown of Data Quality Issues")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.metric("Providers with Expired Licenses", f"{num_expired_licenses}")
            st.metric("Potential Duplicate Records", f"{num_duplicates}")
        
        with col2:
            st.metric("Providers with Phone Format Issues", f"{num_phone_issues}")
            st.metric("Providers with Missing NPI", f"{num_missing_npi}")

        # Visualization
        issues_data = pd.DataFrame({
            'Issue Type': ['Expired Licenses', 'Duplicate Records', 'Phone Format Issues', 'Missing NPIs'],
            'Number of Records': [num_expired_licenses, num_duplicates, num_phone_issues, num_missing_npi]
        })
        
        st.subheader("Visual Summary of Issues")
        st.bar_chart(issues_data.set_index('Issue Type'))

    # --- Page 2: Duplicate Providers ---
    elif page == "Duplicate Providers":
        st.header("👥 Potential Duplicate Provider Records")
        st.markdown(f"Found **{len(duplicate_clusters)}** potential sets of duplicate records based on fuzzy matching of names within the same specialty.")
        st.info("Each section below shows a cluster of records identified as potential duplicates. Review them to confirm.", icon="ℹ️")

        if not duplicate_clusters:
            st.success("No potential duplicates found with the current criteria.")
        else:
            for i, cluster in enumerate(duplicate_clusters):
                with st.expander(f"**Cluster {i+1}:** {roster.loc[cluster[0], 'full_name']} ({len(cluster)} records)"):
                    st.dataframe(roster.loc[cluster][['provider_id', 'full_name', 'primary_specialty', 'practice_address_line1', 'practice_city']])
    
    # --- Page 3: License Validation ---
    elif page == "License Validation":
        st.header("📜 License Validation & Compliance")
        st.markdown(f"Found **{len(expired_licenses)}** providers with licenses that are expired or have a non-active status in the state databases as of **{HACKATHON_DATE}**.")
        
        st.dataframe(expired_licenses, use_container_width=True)
        
        csv = convert_df_to_csv(expired_licenses)
        st.download_button(
            label="📥 Download Expired Licenses Report",
            data=csv,
            file_name='expired_licenses_report.csv',
            mime='text/csv',
        )

    # --- Page 4: Data Formatting ---
    # elif page == "Data Formatting Issues":
    #     st.header("📝 Data Formatting and Completeness Issues")
        
    #     tab1, tab2 = st.tabs(["Phone Number Issues", "Missing NPIs"])

    #     with tab1:
    #         st.subheader(f"📞 Providers with Phone Number Formatting Issues ({len(phone_issues)})")
    #         st.markdown("These providers have phone numbers that are not in a standard 10-digit format.")
    #         st.dataframe(phone_issues, use_container_width=True)
    #         csv = convert_df_to_csv(phone_issues)
    #         st.download_button(
    #             label="📥 Download Phone Issues Report",
    #             data=csv,
    #             file_name='phone_format_issues.csv',
    #             mime='text/csv',
    #             key='phone_csv'
    #         )

    #     with tab2:
    #         st.subheader(f"🆔 Providers with Missing NPI Numbers ({len(missing_npi)})")
    #         st.markdown("These providers do not have a National Provider Identifier (NPI) listed in the roster.")
    #         st.dataframe(missing_npi, use_container_width=True)
    #         csv = convert_df_to_csv(missing_npi)
    #         st.download_button(
    #             label="📥 Download Missing NPI Report",
    #             data=csv,
    #             file_name='missing_npi_report.csv',
    #             mime='text/csv',
    #             key='npi_csv'
    #         )
    elif page == "Data Formatting Issues":
        st.header("📝 Data Formatting and Completeness Issues")

        tab1, tab2 = st.tabs(["Phone Number Issues", "Missing NPIs"])

        with tab1:
            st.subheader(f"📞 Providers with Phone Number Formatting Issues ({len(phone_issues)})")
            st.markdown("These providers have phone numbers that are not in a standard 10-digit format.")
            st.dataframe(phone_issues, use_container_width=True)
            csv = convert_df_to_csv(phone_issues)
            st.download_button(
                label="📥 Download Phone Issues Report",
                data=csv,
                file_name='phone_format_issues.csv',
                mime='text/csv',
                key='phone_csv'
            )

        with tab2:
            st.subheader(f"🆔 Providers with Missing NPI Numbers ({len(missing_npi)})")
            st.markdown("These providers do not have a National Provider Identifier (NPI) listed in the roster.")
            st.dataframe(missing_npi, use_container_width=True)
            csv = convert_df_to_csv(missing_npi)
            st.download_button(
                label="📥 Download Missing NPI Report",
                data=csv,
                file_name='missing_npi_report.csv',
                mime='text/csv',
                key='npi_csv'
            )
else:
    st.warning("Data could not be loaded. Please check the file paths and try again.")