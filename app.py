import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# Function to fetch the first image link for a given search query
def fetch_image_link(search_query, retries=3, backoff=1.0):
    search_url = "https://www.bing.com/images/search"
    params = {
        'q': search_query,
        'form': 'HDRSC2',
        'first': 1,
        'tsc': 'ImageHoverTitle'
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    for attempt in range(retries):
        try:
            response = requests.get(search_url, params=params, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                image_elements = soup.find_all('img', {'class': 'mimg'})
                if image_elements:
                    return image_elements[0]['src']
            else:
                time.sleep(backoff)
                backoff *= 2
        except Exception as e:
            time.sleep(backoff)
            backoff *= 2
    return None

# Initialize session state
if 'output_df' not in st.session_state:
    st.session_state.output_df = None
if 'progress' not in st.session_state:
    st.session_state.progress = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'elapsed_time' not in st.session_state:
    st.session_state.elapsed_time = 0

# Streamlit interface
st.title('Product Image Link Fetcher')

uploaded_file = st.file_uploader("Upload a CSV file", type="csv")

if uploaded_file is not None:
    # Read the uploaded file
    input_csv = pd.read_csv(uploaded_file)
    
    # Show initial dataset details
    st.write("### Initial Dataset")
    st.write(f"Number of rows: {input_csv.shape[0]}")
    st.write(f"Number of columns: {input_csv.shape[1]}")
    st.write("#### Preview of the dataset:")
    st.write(input_csv)
    
    # Check if images are already fetched
    if 'ImageLink' not in input_csv.columns or input_csv['ImageLink'].isnull().all():
        # Set default selection based on column existence
        default_selection = ['Name'] if 'Name' in input_csv.columns else []
        
        # Allow user to select columns for image search
        selected_columns = st.multiselect(
            'Select columns to fetch images for:', 
            options=input_csv.columns.tolist(),
            default=default_selection
        )
        
        if selected_columns:
            # Display start button
            start_button = st.button("Start Fetching Images")
            
            if start_button or st.session_state.output_df is not None:
                if start_button:
                    # Initialize session state variables
                    st.session_state.output_df = input_csv.copy()
                    st.session_state.output_df['ImageLink'] = None
                    st.session_state.progress = 0
                    st.session_state.start_time = time.time()
                    st.session_state.elapsed_time = 0

                # Display progress bar and status text
                progress_bar = st.progress(st.session_state.progress / len(st.session_state.output_df))
                status_text = st.empty()
                total_rows = len(st.session_state.output_df)
                
                for idx in range(st.session_state.progress, total_rows):
                    row = st.session_state.output_df.iloc[idx]
                    search_query = ' '.join(str(row[col]) for col in selected_columns)
                    
                    # Fetch image link
                    image_link = fetch_image_link(search_query)
                    if not image_link:
                        image_link = fetch_image_link(f"{search_query} product")
                    if not image_link:
                        image_link = fetch_image_link(f"{search_query} image")
                    
                    st.session_state.output_df.at[idx, 'ImageLink'] = image_link
                    
                    # Update progress bar and status text
                    st.session_state.progress = idx + 1
                    progress_bar.progress(st.session_state.progress / total_rows)
                    status_text.text(f"Processing {idx + 1}/{total_rows}")
                    
                    # Delay to avoid hitting request limits
                    time.sleep(1)  # Add a short delay between requests
                    
                    # Save state and exit the loop to prevent timeout
                    st.experimental_rerun()
                
                # Calculate elapsed time
                st.session_state.elapsed_time = time.time() - st.session_state.start_time
            
                # Count products with and without images
                products_with_images = st.session_state.output_df['ImageLink'].notna().sum()
                products_without_images = st.session_state.output_df['ImageLink'].isna().sum()
                
                st.success("Image links have been added to the dataset.")
                
                # Show results including elapsed time
                st.write("### Results")
                st.write(f"Products with images: {products_with_images}")
                st.write(f"Products without images: {products_without_images}")
                st.write(f"Time elapsed: {st.session_state.elapsed_time:.2f} seconds")
                st.write("#### Preview of the modified dataset:")
                st.write(st.session_state.output_df)
                
                # Convert DataFrame to CSV for download
                output_csv = st.session_state.output_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV with Image Links",
                    data=output_csv,
                    file_name='products_with_images.csv',
                    mime='text/csv'
                )
                
                st.write("Upload another CSV file to process a new dataset.")
    else:
        st.warning("Image links have already been added to the dataset. Download the CSV file or upload a new one to start again.")
else:
    st.write("Please upload a CSV file to begin.")
