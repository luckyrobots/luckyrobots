# Gitea Parquet Viewer Implementation Guide

## Overview

This guide explains the implementation of the Parquet file viewer for Gitea. The solution allows users to view and interact with Parquet files directly in the Gitea web interface.

## Implementation Details

### 1. File Type Detection

The system detects Parquet files by:
- Checking the file extension (.parquet)
- Setting a global JavaScript variable `window.__fileType` 
- Adding a data attribute to the dataset preview element

This ensures reliable file type detection across different parts of the application.

### 2. DuckDB Integration

We use DuckDB WASM for Parquet file parsing:
- Loaded as an ES module from a CDN
- Initialized early in the page load process
- Made available globally via `window.duckdbInstance`

DuckDB provides efficient, browser-based Parquet parsing without requiring server-side processing.

### 3. UI Components

The viewer consists of:
- A container div with the ID "dataset-preview"
- Dynamic table rendering for displaying Parquet data
- Error handling with informative messages
- Metadata display showing file details

### 4. Fallback Mechanism

When DuckDB cannot be loaded, the system:
- Displays basic file information
- Shows file size and metadata
- Provides useful error messages with troubleshooting steps

### 5. Key Files

- `templates/repo/view_file.tmpl`: Template with DuckDB loading and initialization
- `custom/public/assets/js/dataset-preview.js`: JavaScript for Parquet file handling

## Docker Deployment

The solution is packaged in a Docker image for easy deployment:
- Based on the official Gitea Docker image
- Includes all custom files for Parquet viewing
- Configured for easy deployment via Docker Compose

## Usage Instructions

After deploying the Docker image:
1. Access Gitea via `http://localhost:3000`
2. Create a repository and upload a Parquet file
3. Click on the Parquet file to view its contents
4. The viewer will display the data and metadata

## Troubleshooting

If you encounter issues:
- Check browser console for error messages
- Verify that the browser supports WebAssembly
- Ensure the Parquet file is valid
- Check network connectivity for loading DuckDB from CDN

## Future Improvements

Potential enhancements for future versions:
- Adding column filtering options
- Supporting larger Parquet files with pagination
- Implementing data visualization features
- Adding search functionality within Parquet data 