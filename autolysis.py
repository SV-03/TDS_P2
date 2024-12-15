import os
import sys
import subprocess
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
import chardet

# Install dependencies if not present
# Ensure required dependencies are installed
dependencies = ["pandas", "seaborn", "matplotlib", "httpx", "chardet"]
subprocess.check_call([sys.executable, "-m", "pip", "install", *dependencies])

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
AIPROXY_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIxZjEwMDQxNjNAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.oFdFuJvtdZ0LiL45INOQ4MLlF8yR_0E-EDAyk0C1tU8"  # Use environment variable for token

if not AIPROXY_TOKEN:
    print("Error: AIPROXY_TOKEN is not set in environment variables.")
    sys.exit(1)


def load_data(file_path):
    """Load CSV data with encoding detection."""
    try:
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read())
        encoding = result['encoding']
        return pd.read_csv(file_path, encoding=encoding)
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

def analyze_data(df):
    """Perform basic data analysis."""
    numeric_df = df.select_dtypes(include=['number'])
    analysis = {
        'shape': df.shape,
        'columns': df.columns.tolist(),
        'dtypes': df.dtypes.apply(lambda x: str(x)).to_dict(),
        'missing_values': df.isnull().sum().to_dict(),
        'summary_statistics': df.describe(include='all').to_dict(),
        'correlation': numeric_df.corr().to_dict(),
    }
    return analysis

def visualize_data(df):
    """Generate and save visualizations."""
    sns.set(style="whitegrid")
    png_files = []

    # Correlation Matrix
    numeric_columns = df.select_dtypes(include=['number']).columns
    if len(numeric_columns) > 1:
        plt.figure(figsize=(10, 8))
        corr_matrix = df[numeric_columns].corr()
        sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", fmt=".2f")
        heatmap_file = "correlation_matrix.png"
        plt.title("Correlation Matrix")
        plt.savefig(heatmap_file, bbox_inches="tight")
        png_files.append(heatmap_file)
        plt.close()

    # Histograms
    for column in numeric_columns:
        plt.figure()
        sns.histplot(df[column].dropna(), kde=True)
        plt.title(f'Distribution of {column}')
        hist_file = f'{column}_distribution.png'
        plt.savefig(hist_file, bbox_inches="tight")
        png_files.append(hist_file)
        plt.close()

    return png_files

def generate_narrative(analysis, png_files):
    """Generate narrative using LLM."""
    headers = {
        'Authorization': f'Bearer {AIPROXY_TOKEN}',
        'Content-Type': 'application/json'
    }
    prompt = f"""
    You are a data analyst. Write a README.md file describing the analysis performed on a dataset.

    Data Overview:
    - Shape: {analysis['shape']}
    - Columns: {analysis['columns']}
    - Data Types: {analysis['dtypes']}
    - Missing Values: {analysis['missing_values']}

    Analysis:
    - Summary Statistics: {analysis['summary_statistics']}
    - Correlation Matrix: {analysis['correlation']}

    Visualizations:
    - Include the following images: {png_files}
    """

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a Markdown generator."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = httpx.post(API_URL, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        response_json = response.json()  # Get the raw JSON response

        # Print the response to see its structure
        print("API Response:", response_json)

        # Check if 'choices' key exists
        if 'choices' in response_json and len(response_json['choices']) > 0:
            return response_json['choices'][0]['message']['content']
        else:
            print("Error: 'choices' key not found in API response")
            return f"API response structure unexpected: {response_json}"

    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
    except httpx.RequestError as e:
        print(f"Request error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return "Narrative generation failed due to an error."


def main(file_path):
    df = load_data(file_path)
    analysis = analyze_data(df)
    png_files = visualize_data(df)
    narrative = generate_narrative(analysis, png_files)

    # Save README.md
    with open('README.md', 'w') as f:
        f.write(narrative)

    print("Analysis completed. Files generated:")
    print("README.md")
    print(", ".join(png_files))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)
    main(sys.argv[1])
