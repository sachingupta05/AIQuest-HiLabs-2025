# HiLabs Provider Data Quality Analytics Platform

**Repo Link:** https://github.com/sachingupta05/AIQuest-HiLabs-2025.git

## 🚀 Project Overview

[cite_start]This project is a submission for the HiLabs Hackathon (Sept 6-7, 2025)[cite: 291]. [cite_start]It's an intelligent analytics platform designed to identify, analyze, and present data quality issues within healthcare provider credentialing datasets. [cite: 301] The solution includes a powerful backend analytical engine built with Pandas and a user-friendly, interactive dashboard created with Streamlit.

The platform addresses four core data quality problems as specified in the hackathon challenge:
1.  [cite_start]**Provider Entity Resolution & Deduplication:** Identifies potential duplicate provider records. [cite: 304]
2.  [cite_start]**License Validation & Compliance Tracking:** Detects expired or invalid licenses by cross-referencing with state medical board data. [cite: 305]
3.  [cite_start]**Data Quality Assessment & Standardization:** Analyzes and flags missing NPIs and inconsistent phone number formats. [cite: 306]
4.  [cite_start]**Interactive Analytics Dashboard:** Provides a web-based UI for healthcare administrators to explore data quality issues visually and interactively. [cite: 308]

---

## 🛠️ Architecture & Approach

The platform is built as a monolithic Streamlit application for simplicity and rapid development.

1.  **Data Processing Layer (Backend):**
    * **Engine:** All data manipulation and analysis are performed using the `pandas` library for efficiency.
    * **Data Loading:** All datasets are loaded into memory and cached using Streamlit's `@st.cache_data` to ensure fast performance and responsiveness during user interactions.
    * **Deduplication:** A fuzzy logic approach using the `thefuzz` library identifies potential duplicates. It works by "blocking" records based on last name and primary specialty to reduce comparisons, then calculates a token set ratio score for full names to find close matches (e.g., "Dave Shah" vs. "David H Shah").
    * **Validation & Standardization:**
        * **Licenses:** The main provider roster is merged with CA and NY license databases. Expiration dates are parsed and compared against the hackathon date (Sept 7, 2025) to flag expired licenses.
        * **Phone Numbers:** A regex-based function standardizes phone numbers by stripping non-numeric characters and flags any that do not resolve to a standard 10-digit format.
        * **NPIs:** Checks for null or missing values in the NPI column.

2.  **Presentation Layer (Frontend):**
    * **Framework:** The user interface is built entirely with `Streamlit`.
    * **Structure:** The application uses a sidebar for navigation between four main pages: an Overview Dashboard, Duplicate Provider analysis, License Validation, and Formatting Issues.
    * **Interactivity:** The dashboard features KPI cards (`st.metric`), charts (`st.bar_chart`), and interactive, sortable tables for displaying problematic records. Users can download filtered lists of providers as CSV files for remediation.

---

## ⚙️ Setup and Installation

Follow these steps to get the platform running locally.

### Prerequisites
* Python 3.9+
* `pip` (Python package installer)

### Installation
1.  **Clone the repository (or create the files manually):**
    ```bash
    git clone https://github.com/sachingupta05/AIQuest-HiLabs-2025.git
    cd hilabs-hackathon-solution
    ```

2.  **Place Datasets:**
    Ensure the four provided CSV files are in the root of the project directory:
    * `provider_roster_with_errors.csv`
    * `ca_medical_license_database.csv`
    * `ny_medical_license_database.csv`
    * `mock_npi_registry.csv`

3.  **Install Dependencies:**
    Install all required Python libraries from the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

---

## ▶️ How to Run the Application

Once the setup is complete, run the following command in your terminal from the project's root directory:

```bash

python -m streamlit run app.py
