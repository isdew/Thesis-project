import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def plot_normalized_delays(file_path):
    """
    A focused script to normalize delay values and plot them by time step.
    
    Args:
        file_path (str): Path to the CSV file with delay data
    """
    # Read the CSV file
    df = pd.read_csv("/Users/fadil/Downloads/Actual_Delay_Results.csv")
    
    # Filter out rows with null time steps if any
    df = df.dropna(subset=['Time Step'])
    
    # Convert Time Step to integer for proper ordering
    df['Time Step'] = df['Time Step'].astype(int)
    
    # Sort by time step
    df = df.sort_values('Time Step')
    
    # Extract delay columns (both uplink and downlink)
    delay_cols = [col for col in df.columns if 'GHz' in col]
    
    # Create a DataFrame for normalized values
    normalized_df = pd.DataFrame()
    normalized_df['Time Step'] = df['Time Step']
    normalized_df['TEC'] = df['TEC']
    normalized_df['Rain Rate (mm/hr)'] = df['Rain Rate (mm/hr)']
    
    # Normalize each delay column using min-max normalization
    for col in delay_cols:
        min_val = df[col].min()
        max_val = df[col].max()
        if max_val > min_val:
            normalized_df[f'Normalized {col}'] = (df[col] - min_val) / (max_val - min_val)
        else:
            normalized_df[f'Normalized {col}'] = df[col]
    
    # Group frequencies into bands for better visualization
    # Extract frequency bands for each column
    frequency_bands = {}
    for col in delay_cols:
        parts = col.split(' ')
        freq = float(parts[0])
        direction = parts[2]  # 'Uplink' or 'Downlink'
        
        # Group by frequency range (e.g., 3-5 GHz, 10-15 GHz, etc.)
        if freq < 5:
            band = "3-5 GHz"
        elif freq < 10:
            band = "5-10 GHz"
        elif freq < 15:
            band = "10-15 GHz"
        elif freq < 20:
            band = "15-20 GHz"
        elif freq < 25:
            band = "20-25 GHz"
        else:
            band = "25-31 GHz"
        
        band_key = f"{band} {direction}"
        if band_key not in frequency_bands:
            frequency_bands[band_key] = []
        
        frequency_bands[band_key].append(col)
    
    # Calculate the mean normalized delay for each band
    band_means = {}
    for band, cols in frequency_bands.items():
        norm_cols = [f'Normalized {col}' for col in cols]
        band_means[band] = normalized_df[norm_cols].mean(axis=1)
    
    # Create a DataFrame for band means
    band_means_df = pd.DataFrame(band_means)
    band_means_df['Time Step'] = normalized_df['Time Step']
    
    # Create the plots
    plt.figure(figsize=(15, 10))
    
    # Plot 1: Line plot of normalized delays by time step for each frequency band
    plt.subplot(2, 1, 1)
    for band in band_means_df.columns:
        if band != 'Time Step':
            plt.plot(band_means_df['Time Step'], band_means_df[band], 
                     marker='o', linewidth=2, label=band)
    
    plt.title('Normalized Delay by Time Step for Different Frequency Bands', fontsize=14)
    plt.xlabel('Time Step', fontsize=12)
    plt.ylabel('Normalized Delay (0-1)', fontsize=12)
    plt.xticks(band_means_df['Time Step'])
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    
    # Plot 2: Heatmap of the normalized delays
    plt.subplot(2, 1, 2)
    
    # Prepare data for heatmap
    pivot_data = band_means_df.melt(id_vars='Time Step', var_name='Frequency Band', value_name='Normalized Delay')
    pivot_table = pivot_data.pivot(index='Frequency Band', columns='Time Step', values='Normalized Delay')
    
    # Create heatmap
    sns.heatmap(pivot_table, annot=True, cmap='Blues', fmt='.2f', linewidths=.5)
    plt.title('Heatmap of Normalized Delays by Frequency Band and Time Step', fontsize=14)
    
    plt.tight_layout()
    plt.savefig('normalized_delays.png')
    plt.show()
    
    return normalized_df, band_means_df

if __name__ == "__main__":
    df_normalized, df_bands = plot_normalized_delays("Actual_Delay_Results.csv")
    
    # Print summary information
    print("\nSummary of Normalized Delays by Time Step:")
    summary = df_bands.groupby('Time Step').mean().reset_index()
    print(summary)