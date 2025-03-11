document.addEventListener("DOMContentLoaded", async function () {
    const previewElement = document.getElementById("dataset-preview");
    console.log("Preview element:", previewElement);
    if (!previewElement) {
        return;
    }

    const fileUrl = previewElement.getAttribute("data-file-url");
    let fileType = previewElement.getAttribute("data-file-type");
    
    // If file type is not set in the data attribute, check if it's set in the window variable
    if (!fileType && window.__fileType) {
        fileType = window.__fileType;
        console.log("Using file type from window variable:", fileType);
        // Update the data attribute for consistency
        previewElement.setAttribute("data-file-type", fileType);
    }
    
    // As a last resort, try to determine the file type from the URL
    if (!fileType) {
        const urlLower = fileUrl.toLowerCase();
        if (urlLower.endsWith('.parquet')) {
            fileType = 'parquet';
        } else if (urlLower.endsWith('.csv')) {
            fileType = 'csv';
        } else if (urlLower.endsWith('.json')) {
            fileType = 'json';
        } else {
            fileType = 'unknown';
        }
        console.log("Detected file type from URL:", fileType);
        previewElement.setAttribute("data-file-type", fileType);
    }
    
    console.log("Dataset preview: fileUrl =", fileUrl, "fileType =", fileType);

    // Log available global objects for debugging
    console.log("Available global objects:", {
        duckdbLoaded: window.__duckdbLoaded,
        fileType: window.__fileType,
        parquetFilePath: window.__parquetFilePath
    });

            if (fileType === "csv") {
        await loadCSV(fileUrl);
            } else if (fileType === "json") {
        // For JSON files, just provide a download link for now
        const container = document.createElement("div");
        container.className = "ui segment";
        container.innerHTML = `
            <div class="ui info message">
                <div class="header">JSON File</div>
                <p>JSON files are not rendered directly. <a href="${fileUrl}" download>Click here to download</a></p>
            </div>
        `;
        previewElement.appendChild(container);
            } else if (fileType === "parquet") {
        await loadParquetFile(fileUrl);
    } else {
        // Show a generic message for unknown file types
        const container = document.createElement("div");
        container.className = "ui segment";
        container.innerHTML = `
            <div class="ui info message">
                <div class="header">File Preview</div>
                <p>No preview available for this file type. <a href="${fileUrl}" download>Click here to download</a></p>
            </div>
        `;
        previewElement.appendChild(container);
    }
});

// Main function to handle Parquet files
async function loadParquetFile(fileUrl) {
    console.log("Loading Parquet file from URL:", fileUrl);
    
    // Normalize the URL if needed (change /src/ to /raw/ if necessary)
    let normalizedUrl = fileUrl;
    if (normalizedUrl.includes("/src/")) {
        normalizedUrl = normalizedUrl.replace("/src/", "/raw/");
    }
    
    // Create a loading indicator
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "ui active dimmer";
    loadingDiv.innerHTML = '<div class="ui text loader">Loading Parquet file...</div>';
    
    const previewElement = document.getElementById("dataset-preview");
    previewElement.appendChild(loadingDiv);
    
    try {
        // Extract the filename for display
        const filename = getFilenameFromUrl(normalizedUrl);
        console.log("Filename extracted:", filename);
        
        // Check if user has defined a specific Parquet file path
        if (window.__parquetFilePath) {
            console.log("Using predefined Parquet file path:", window.__parquetFilePath);
            normalizedUrl = window.__parquetFilePath;
        }
        
        let success = false;
        
        // Check for the pre-instantiated DuckDB instance
        if (window.__duckdbLoaded && window.duckdbInstance) {
            console.log("DuckDB instance is available, using it for parsing");
            try {
                success = await readParquetWithDuckDB(normalizedUrl);
            } catch (err) {
                console.error("Error using DuckDB instance:", err);
            }
        } else {
            console.log("DuckDB instance not available - check the console for errors");
            // Add a small delay to allow DuckDB to load (in case it's still loading)
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Check again after delay
            if (window.__duckdbLoaded && window.duckdbInstance) {
                console.log("DuckDB instance became available after delay");
                try {
                    success = await readParquetWithDuckDB(normalizedUrl);
                } catch (err) {
                    console.error("Error using DuckDB instance after delay:", err);
                }
            }
        }
        
        // If DuckDB failed or is not available, fall back to basic info
        if (!success) {
            console.log("DuckDB parsing failed, falling back to basic info");
            await displayEnhancedParquetInfo(normalizedUrl);
        }
        
        // Clean up loading indicator
        loadingDiv.remove();
    } catch (error) {
        console.error("Error loading Parquet file:", error);
        
        // Show error message
        const errorMessage = error.message || "Unknown error";
        loadingDiv.remove();
        
        // Create detailed error message
        const errorDiv = document.createElement("div");
        errorDiv.className = "ui negative message";
        
        // Build a more helpful error message
        let errorDetails = `<div class="header">Error Loading Parquet File</div>
            <p>${escapeHTML(errorMessage)}</p>`;
            
        // Add troubleshooting info
        errorDetails += `
            <div class="ui segment">
                <h4>Troubleshooting Information:</h4>
                <ul>
                    <li>File URL: ${escapeHTML(normalizedUrl)}</li>
                    <li>Browser: ${escapeHTML(navigator.userAgent)}</li>
                    <li>DuckDB loaded: ${window.__duckdbLoaded ? 'Yes' : 'No'}</li>
                    <li>DuckDB instance available: ${window.duckdbInstance ? 'Yes' : 'No'}</li>
                </ul>
                
                <h4>Common Issues:</h4>
                <ul>
                    <li>The file might not be a valid Parquet file</li>
                    <li>The DuckDB library might not be loading correctly</li>
                    <li>The server might not be sending the correct content type for Parquet files</li>
                    <li>Your browser might be blocking WebAssembly execution</li>
                </ul>
            </div>
            <p><a href="${normalizedUrl}" download class="ui button small">Download File</a></p>
        `;
        
        errorDiv.innerHTML = errorDetails;
        previewElement.appendChild(errorDiv);
    }
}

// Helper function to read Parquet with the Worker API
async function readParquetWithWorker(fileUrl) {
    try {
        console.log("Reading Parquet with DuckDB Worker API");
        
        // Create a worker
        const db = await duckdb.createWorker();
        console.log("DuckDB worker created");
        
        const conn = await db.connect();
        console.log("DuckDB connection established");
        
        try {
            // Download the Parquet file
            const response = await fetch(fileUrl);
            if (!response.ok) {
                throw new Error(`Failed to fetch file: ${response.status} ${response.statusText}`);
            }
            
            // Get the Parquet data
            const arrayBuffer = await response.arrayBuffer();
            console.log("Parquet file fetched, size:", arrayBuffer.byteLength);
            
            // Register the Parquet file as a buffer
            await db.registerFileBuffer('data.parquet', new Uint8Array(arrayBuffer));
            console.log("Parquet file registered with DuckDB");
            
            // Get schema information
            const schemaResult = await conn.query(`
                DESCRIBE SELECT * FROM parquet_scan('data.parquet')
            `);
            console.log("Schema obtained:", schemaResult);
            
            // Get data preview (first 100 rows)
            const dataResult = await conn.query(`
                SELECT * FROM parquet_scan('data.parquet') LIMIT 100
            `);
            console.log("Data preview obtained:", dataResult);
            
            // Get row count
            const countResult = await conn.query(`
                SELECT COUNT(*) as row_count FROM parquet_scan('data.parquet')
            `);
            console.log("Row count obtained:", countResult);
            
            const rowCount = countResult.toArray()[0].row_count;
            
            // Display the results
            await displayDuckDBTable(schemaResult, dataResult, rowCount, fileUrl);
            
            return true;
        } finally {
            // Clean up
            await conn.close();
            await db.terminate();
        }
    } catch (error) {
        console.error("Error reading Parquet with Worker API:", error);
        return false;
    }
}

// Function to read Parquet with DuckDB-WASM
async function readParquetWithDuckDB(fileUrl) {
    try {
        console.log("Reading Parquet with DuckDB-WASM from:", fileUrl);
        
        // Check if DuckDB and the instantiated instance are available
        if (!window.__duckdbLoaded || !window.duckdbInstance) {
            throw new Error("DuckDB instance not available");
        }
        
        console.log("Using pre-instantiated DuckDB instance");
        
        // Use the global DuckDB instance
        const db = window.duckdbInstance;
        
        // Connect to the database
        const conn = await db.connect();
        console.log("DuckDB connection established");
        
        try {
            // Download the Parquet file
            const response = await fetch(fileUrl);
            if (!response.ok) {
                throw new Error(`Failed to fetch file: ${response.status} ${response.statusText}`);
            }
            
            // Get the Parquet data
            const arrayBuffer = await response.arrayBuffer();
            console.log("Parquet file fetched, size:", arrayBuffer.byteLength);
            
            // Register the Parquet file as a buffer
            await db.registerFileBuffer('data.parquet', new Uint8Array(arrayBuffer));
            console.log("Parquet file registered with DuckDB");
            
            // Get schema information
            const schemaResult = await conn.query(`
                DESCRIBE SELECT * FROM parquet_scan('data.parquet')
            `);
            console.log("Schema obtained:", schemaResult);
            
            // Get data preview (first 100 rows)
            const dataResult = await conn.query(`
                SELECT * FROM parquet_scan('data.parquet') LIMIT 100
            `);
            console.log("Data preview obtained:", dataResult);
            
            // Get row count
            const countResult = await conn.query(`
                SELECT COUNT(*) as row_count FROM parquet_scan('data.parquet')
            `);
            console.log("Row count obtained:", countResult);
            
            const rowCount = countResult.toArray()[0].row_count;
            
            // Display the results
            await displayDuckDBTable(schemaResult, dataResult, rowCount, fileUrl);
            
            return true;
        } finally {
            // Close the connection but don't terminate the DB
            // since we're using a shared instance
            await conn.close();
        }
    } catch (error) {
        console.error("Error reading Parquet with DuckDB:", error);
        return false;
    }
}

// Function to display a DuckDB table
async function displayDuckDBTable(schemaResult, dataResult, rowCount, fileUrl) {
    const previewElement = document.getElementById("dataset-preview");
    const filename = getFilenameFromUrl(fileUrl);
    
    // Create container for the table
    const container = document.createElement("div");
    container.className = "ui segment";
    
    // Extract schema information
    const schemaArray = schemaResult.toArray();
    const schema = schemaArray.map(row => ({
        name: row.column_name,
        type: row.column_type,
        nullable: true  // DuckDB doesn't provide this directly
    }));
    
    const numCols = schema.length;
    
    // Add header with file info
    container.innerHTML = `
        <h3 class="ui header">
            <i class="table icon"></i>
            <div class="content">
                Parquet Dataset: ${escapeHTML(filename)}
                <div class="sub header">${rowCount} rows × ${numCols} columns</div>
            </div>
        </h3>
    `;
    
    // Add schema information
    const schemaSection = document.createElement("div");
    schemaSection.className = "ui message";
    schemaSection.innerHTML = `
        <div class="header">Schema Information</div>
        <table class="ui compact table">
            <thead>
                <tr>
                    <th>Column Name</th>
                    <th>Data Type</th>
                </tr>
            </thead>
            <tbody>
                ${schema.map(col => `
                    <tr>
                        <td>${escapeHTML(col.name)}</td>
                        <td>${escapeHTML(col.type)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    container.appendChild(schemaSection);
    
    // Create table for data preview
    const dataTable = document.createElement("table");
    dataTable.className = "ui celled striped table";
    
    // Get the data rows
    const dataRows = dataResult.toArray();
    
    // Create header row
    let tableHTML = '<thead><tr>';
    for (const field of schema) {
        tableHTML += `<th>${escapeHTML(field.name)}</th>`;
    }
    tableHTML += '</tr></thead><tbody>';
    
    // Create data rows
    const maxRows = Math.min(dataRows.length, 100);
    
    try {
        for (let rowIdx = 0; rowIdx < maxRows; rowIdx++) {
            tableHTML += '<tr>';
            const row = dataRows[rowIdx];
            for (const field of schema) {
                let value = row[field.name];
                // Format the value for display
                if (value === null || value === undefined) {
                    value = 'null';
                } else if (typeof value === 'object') {
                    value = JSON.stringify(value);
                }
                tableHTML += `<td>${escapeHTML(String(value))}</td>`;
            }
            tableHTML += '</tr>';
        }
    } catch (error) {
        console.error('Error rendering table data:', error);
        tableHTML += `<tr><td colspan="${numCols}">Error rendering data: ${escapeHTML(error.message)}</td></tr>`;
    }
    
    tableHTML += '</tbody>';
    dataTable.innerHTML = tableHTML;
    
    // Add a title for the data preview
    const previewTitle = document.createElement("h4");
    previewTitle.className = "ui header";
    previewTitle.innerHTML = "Data Preview";
    container.appendChild(previewTitle);
    
    // Add the data table
    container.appendChild(dataTable);
    
    // Add a note if we're limiting the rows
    if (rowCount > 100) {
        const note = document.createElement('div');
        note.className = 'ui info message';
        note.innerHTML = `<p>Showing first 100 rows of ${rowCount} total rows</p>`;
        container.appendChild(note);
    }
    
    // Add download link
    const downloadDiv = document.createElement("div");
    downloadDiv.className = "ui basic segment";
    downloadDiv.innerHTML = `
        <a class="ui primary button" href="${fileUrl}" download>
            <i class="download icon"></i> Download Parquet File
        </a>
    `;
    container.appendChild(downloadDiv);
    
    // Add to preview element
    previewElement.appendChild(container);
}

// Function to read Parquet with Apache Arrow
async function readParquetWithArrow(fileUrl) {
    try {
        console.log("Reading Parquet with Apache Arrow from:", fileUrl);
        
        // Ensure we're using the raw URL to get the binary data directly
        let binaryUrl = fileUrl;
        if (binaryUrl.includes("/src/")) {
            binaryUrl = binaryUrl.replace("/src/", "/raw/");
        }
        
        console.log("Fetching binary data from:", binaryUrl);
        
        // Fetch the file with explicit binary type
        const response = await fetch(binaryUrl, {
            headers: {
                'Accept': 'application/octet-stream'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to fetch file: ${response.status} ${response.statusText}`);
        }
        
        // Get the array buffer
        const arrayBuffer = await response.arrayBuffer();
        console.log("File fetched, size:", arrayBuffer.byteLength);
        
        // Check if the file starts with PAR1 (Parquet magic number)
        const headerBytes = new Uint8Array(arrayBuffer.slice(0, 4));
        const headerString = new TextDecoder().decode(headerBytes);
        if (headerString !== 'PAR1') {
            throw new Error(`Not a valid Parquet file. Expected 'PAR1' magic number but found '${headerString}'`);
        }
        
        // Use Arrow to read the Parquet file
        const Arrow = window.Arrow;
        const Parquet = window.Parquet;
        
        console.log("Available modules:", {
            Arrow: Boolean(Arrow),
            Parquet: Boolean(Parquet),
            ArrowAPI: Arrow ? Object.keys(Arrow) : null,
            ParquetAPI: Parquet ? Object.keys(Parquet) : null
        });
        
        if (!Arrow || !Parquet) {
            throw new Error("Arrow or Parquet module not available");
        }
        
        // Convert ArrayBuffer to Uint8Array
        const uint8Array = new Uint8Array(arrayBuffer);
        
        // Try different approach based on what's available in the API
        let table;
        let success = false;
        
        // Try multiple methods to read the Parquet file
        const methods = [
            {
                name: 'Parquet.readParquet',
                available: () => Parquet && typeof Parquet.readParquet === 'function',
                execute: async () => await Parquet.readParquet(uint8Array)
            },
            {
                name: 'ParquetReader.fromUint8Array',
                available: () => Parquet && Parquet.ParquetReader && typeof Parquet.ParquetReader.fromUint8Array === 'function',
                execute: async () => {
                    const reader = await Parquet.ParquetReader.fromUint8Array(uint8Array);
                    return await reader.readRows();
                }
            },
            {
                name: 'Arrow.Table.from',
                available: () => Arrow && Arrow.Table && typeof Arrow.Table.from === 'function',
                execute: async () => await Arrow.Table.from(uint8Array)
            },
            {
                name: 'Arrow.RecordBatchReader.from',
                available: () => Arrow && Arrow.RecordBatchReader && typeof Arrow.RecordBatchReader.from === 'function',
                execute: async () => {
                    const reader = Arrow.RecordBatchReader.from(uint8Array);
                    return await reader.readAll();
                }
            }
        ];
        
        // Try each method in order
        for (const method of methods) {
            if (method.available()) {
                try {
                    console.log(`Trying ${method.name} method`);
                    table = await method.execute();
                    console.log(`${method.name} succeeded:`, table);
                    success = true;
                    break;
                } catch (err) {
                    console.warn(`${method.name} failed:`, err);
                }
            }
        }
        
        if (!success) {
            throw new Error("No compatible Parquet reading method succeeded");
        }
        
        console.log("Parquet table successfully read:", table);
        
        // Display the table
        await displayParquetTable(table, fileUrl);
        return true;
    } catch (error) {
        console.error("Error reading Parquet with Arrow:", error);
        return false;
    }
}

// Function to display a Parquet table
async function displayParquetTable(table, fileUrl) {
    const previewElement = document.getElementById("dataset-preview");
    const filename = getFilenameFromUrl(fileUrl);
    
    // Create container for the table
    const container = document.createElement("div");
    container.className = "ui segment";
    
    // Get table properties safely
    let numRows = 0;
    let numCols = 0;
    let schema = [];
    
    try {
        // Handle different table formats
        if (table.numRows !== undefined && table.numCols !== undefined) {
            // Standard arrow table
            numRows = table.numRows;
            numCols = table.numCols;
            
            // Extract schema
            for (let i = 0; i < numCols; i++) {
                const field = table.schema.fields[i];
                schema.push({
                    name: field.name,
                    type: field.type.toString(),
                    nullable: field.nullable
                });
            }
        } else if (table.schema && table.batches) {
            // RecordBatchReader result
            numRows = table.batches.reduce((sum, batch) => sum + batch.numRows, 0);
            numCols = table.schema.fields.length;
            
            // Extract schema
            for (let i = 0; i < numCols; i++) {
                const field = table.schema.fields[i];
                schema.push({
                    name: field.name,
                    type: field.type.toString(),
                    nullable: field.nullable
                });
            }
        } else if (Array.isArray(table) && table.length > 0) {
            // Array of records
            numRows = table.length;
            
            // Get columns from first row
            if (typeof table[0] === 'object') {
                const keys = Object.keys(table[0]);
                numCols = keys.length;
                
                // Create simple schema
                schema = keys.map(key => ({
                    name: key,
                    type: 'unknown',
                    nullable: true
                }));
            }
        } else {
            console.warn('Unknown table format:', table);
            numRows = 0;
            numCols = 0;
        }
    } catch (error) {
        console.error('Error extracting table properties:', error);
    }
    
    // Add header with file info
    container.innerHTML = `
        <h3 class="ui header">
            <i class="table icon"></i>
            <div class="content">
                Parquet Dataset: ${escapeHTML(filename)}
                <div class="sub header">${numRows} rows × ${numCols} columns</div>
            </div>
        </h3>
    `;
    
    // Add schema information
    const schemaSection = document.createElement("div");
    schemaSection.className = "ui message";
    schemaSection.innerHTML = `
        <div class="header">Schema Information</div>
        <table class="ui compact table">
            <thead>
                <tr>
                    <th>Column Name</th>
                    <th>Data Type</th>
                    <th>Nullable</th>
                </tr>
            </thead>
            <tbody>
                ${schema.map(col => `
                    <tr>
                        <td>${escapeHTML(col.name)}</td>
                        <td>${escapeHTML(col.type)}</td>
                        <td>${col.nullable ? 'Yes' : 'No'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    container.appendChild(schemaSection);
    
    // Create table for data preview (limit to 100 rows for performance)
    const dataTable = document.createElement("table");
    dataTable.className = "ui celled striped table";
    
    // Create header row
    let tableHTML = '<thead><tr>';
    for (const field of schema) {
        tableHTML += `<th>${escapeHTML(field.name)}</th>`;
    }
    tableHTML += '</tr></thead><tbody>';
    
    // Create data rows (limit to 100 rows)
    const maxRows = Math.min(numRows, 100);
    
    try {
        if (table.getChildAt && typeof table.getChildAt === 'function') {
            // Standard Arrow Table
            for (let rowIdx = 0; rowIdx < maxRows; rowIdx++) {
                tableHTML += '<tr>';
                for (let colIdx = 0; colIdx < numCols; colIdx++) {
                    // Try to get the value safely
                    let value;
                    try {
                        const col = table.getChildAt(colIdx);
                        value = col.get(rowIdx);
                        // Format the value for display
                        if (value === null || value === undefined) {
                            value = 'null';
                        } else if (typeof value === 'object') {
                            value = JSON.stringify(value);
                        }
                    } catch (e) {
                        value = '[error]';
                        console.error(`Error getting value at [${rowIdx},${colIdx}]:`, e);
                    }
                    tableHTML += `<td>${escapeHTML(String(value))}</td>`;
                }
                tableHTML += '</tr>';
            }
        } else if (table.batches && Array.isArray(table.batches)) {
            // RecordBatchReader result
            let currentRow = 0;
            for (const batch of table.batches) {
                if (currentRow >= maxRows) break;
                
                for (let rowIdx = 0; rowIdx < batch.numRows && currentRow < maxRows; rowIdx++, currentRow++) {
                    tableHTML += '<tr>';
                    for (let colIdx = 0; colIdx < numCols; colIdx++) {
                        let value;
                        try {
                            const col = batch.getChildAt(colIdx);
                            value = col.get(rowIdx);
                            if (value === null || value === undefined) {
                                value = 'null';
                            } else if (typeof value === 'object') {
                                value = JSON.stringify(value);
                            }
                        } catch (e) {
                            value = '[error]';
                        }
                        tableHTML += `<td>${escapeHTML(String(value))}</td>`;
                    }
                    tableHTML += '</tr>';
                }
            }
        } else if (Array.isArray(table)) {
            // Array of records
            for (let rowIdx = 0; rowIdx < maxRows; rowIdx++) {
                tableHTML += '<tr>';
                for (const field of schema) {
                    let value = table[rowIdx][field.name];
                    if (value === null || value === undefined) {
                        value = 'null';
                    } else if (typeof value === 'object') {
                        value = JSON.stringify(value);
                    }
                    tableHTML += `<td>${escapeHTML(String(value))}</td>`;
                }
                tableHTML += '</tr>';
            }
        } else {
            tableHTML += `<tr><td colspan="${numCols}">Unable to display data: unsupported table format</td></tr>`;
        }
    } catch (error) {
        console.error('Error rendering table data:', error);
        tableHTML += `<tr><td colspan="${numCols}">Error rendering data: ${escapeHTML(error.message)}</td></tr>`;
    }
    
    tableHTML += '</tbody>';
    dataTable.innerHTML = tableHTML;
    
    // Add a title for the data preview
    const previewTitle = document.createElement("h4");
    previewTitle.className = "ui header";
    previewTitle.innerHTML = "Data Preview";
    container.appendChild(previewTitle);
    
    // Add the data table
    container.appendChild(dataTable);
    
    // Add a note if we're limiting the rows
    if (numRows > 100) {
        const note = document.createElement('div');
        note.className = 'ui info message';
        note.innerHTML = `<p>Showing first 100 rows of ${numRows} total rows</p>`;
        container.appendChild(note);
    }
    
    // Add download link
    const downloadDiv = document.createElement("div");
    downloadDiv.className = "ui basic segment";
    downloadDiv.innerHTML = `
        <a class="ui primary button" href="${fileUrl}" download>
            <i class="download icon"></i> Download Parquet File
        </a>
    `;
    container.appendChild(downloadDiv);
    
    // Add to preview element
    previewElement.appendChild(container);
}

// Enhanced Parquet file viewer that tries to extract some metadata
async function displayEnhancedParquetInfo(fileUrl) {
    console.log("Displaying enhanced Parquet file info");
    
    try {
        // Get information about the file
        const headResponse = await fetch(fileUrl, { method: 'HEAD' });
        
        if (!headResponse.ok) {
            throw new Error(`Failed to fetch file information: ${headResponse.status} ${headResponse.statusText}`);
        }
        
        // Get content length and last modified date
        const contentLength = headResponse.headers.get("content-length");
        const lastModified = headResponse.headers.get("last-modified");
        const fileSize = contentLength ? formatFileSize(parseInt(contentLength, 10)) : "Unknown";
        
        // Fetch the entire file for small files, or just the first 100KB for larger files
        const response = await fetch(fileUrl);
        if (!response.ok) {
            throw new Error(`Failed to fetch file: ${response.status} ${response.statusText}`);
        }
        
        // Read the file data
        const arrayBuffer = await response.arrayBuffer();
        const bytes = new Uint8Array(arrayBuffer);
        
        // Check if the file starts with the Parquet magic number "PAR1"
        const magicNumber = new TextDecoder().decode(bytes.slice(0, 4));
        if (magicNumber !== "PAR1") {
            throw new Error("Not a valid Parquet file (missing PAR1 magic number)");
        }
        
        // Check for the end magic number too (should also be "PAR1")
        const endMagic = contentLength && contentLength > 4 ? 
            new TextDecoder().decode(bytes.slice(bytes.length - 4)) : '';
        
        // Try to extract more metadata from the file
        const hasEndMagic = endMagic === "PAR1";
        
        // Try to find the footer metadata (very simplified approach)
        let metadataInfo = "Not available - load DuckDB for full metadata";
        let detectedColumns = 0;
        let detectedFormat = "Parquet";
        
        // Look for some common metadata markers
        const utf8Decoder = new TextDecoder('utf-8');
        const fileStr = utf8Decoder.decode(bytes);
        
        // Try to estimate columns by looking for "schema" and "name" strings in metadata
        const schemaMatches = fileStr.match(/schema/g);
        const nameMatches = fileStr.match(/name/g);
        if (schemaMatches && nameMatches) {
            detectedColumns = Math.min(schemaMatches.length, nameMatches.length);
        }
        
        // Look for compression info
        if (fileStr.includes("SNAPPY")) {
            detectedFormat = "Parquet (SNAPPY compression)";
        } else if (fileStr.includes("GZIP")) {
            detectedFormat = "Parquet (GZIP compression)";
        } else if (fileStr.includes("LZ4")) {
            detectedFormat = "Parquet (LZ4 compression)";
        } else if (fileStr.includes("ZSTD")) {
            detectedFormat = "Parquet (ZSTD compression)";
        }
        
        // Create a container to display the file info
        const previewElement = document.getElementById("dataset-preview");
        
        // Create content
        const container = document.createElement("div");
        container.className = "ui segment";
        container.innerHTML = `
            <h3 class="ui header">
                <i class="file icon"></i>
                <div class="content">
                    Parquet File: ${escapeHTML(getFilenameFromUrl(fileUrl))}
                    <div class="sub header">Apache Parquet Format</div>
                </div>
            </h3>
            
            <div class="ui info message">
                <div class="header">File Information</div>
                <ul class="list">
                    <li><strong>Size:</strong> ${fileSize}</li>
                    ${lastModified ? `<li><strong>Last Modified:</strong> ${new Date(lastModified).toLocaleString()}</li>` : ''}
                    <li><strong>Format:</strong> ${detectedFormat}</li>
                    <li><strong>Validity:</strong> ${magicNumber === "PAR1" ? "✅ Valid Parquet header detected" : "❌ Invalid Parquet header"} ${hasEndMagic ? "/ ✅ Valid Parquet footer detected" : ""}</li>
                    <li><strong>Estimated columns:</strong> ${detectedColumns > 0 ? detectedColumns : "Unknown"}</li>
                </ul>
            </div>
            
            <div class="ui warning message">
                <div class="header">Load Error</div>
                <p><strong>DuckDB could not be loaded to view this Parquet file properly.</strong></p>
                <p>Possible reasons:</p>
                <ul>
                    <li>The DuckDB WebAssembly module failed to load</li>
                    <li>CORS restrictions prevented loading the WASM file</li>
                    <li>Browser restrictions on WebAssembly</li>
                </ul>
                <p><strong>Solutions:</strong></p>
                <ul>
                    <li>Try refreshing the page</li>
                    <li>Try a different browser (Chrome or Firefox recommended)</li>
                    <li>Download the file and use a desktop Parquet viewer</li>
                </ul>
            </div>
            
            <div class="ui info message">
                <div class="header">About Apache Parquet</div>
                <p>Apache Parquet is a columnar storage format that offers efficient compression and encoding schemes with enhanced performance to handle complex data in bulk.</p>
                <p>Key features include:</p>
                <ul>
                    <li>Efficient column-wise compression</li>
                    <li>Designed for distributed processing systems</li>
                    <li>Efficient encoding schemes for better performance on queries</li>
                    <li>Compatible with data processing frameworks in the Hadoop ecosystem</li>
                </ul>
            </div>
            
            <div class="ui message">
                <p>To view the contents of this Parquet file, you need specialized tools such as:</p>
                <ul>
                    <li><a href="https://pandas.pydata.org/" target="_blank">Python Pandas</a> with <a href="https://arrow.apache.org/docs/python/parquet.html" target="_blank">PyArrow</a></li>
                    <li><a href="https://spark.apache.org/" target="_blank">Apache Spark</a></li>
                    <li><a href="https://arrow.apache.org/" target="_blank">Apache Arrow</a></li>
                    <li><a href="https://cloud.google.com/bigquery" target="_blank">Google BigQuery</a></li>
                </ul>
                <p>Example Python code to read this file:</p>
                <pre>import pandas as pd
df = pd.read_parquet('${getFilenameFromUrl(fileUrl)}')
print(df.head())</pre>
            </div>
            
            <div class="ui basic segment">
                <a class="ui primary button" href="${fileUrl}" download>
                    <i class="download icon"></i> Download Parquet File
                </a>
            </div>
        `;
        
        previewElement.appendChild(container);
        return true;
    } catch (error) {
        console.error("Error in enhanced Parquet info:", error);
        
        // Use the correct variable name (previewElement, not previewEl)
        const previewElement = document.getElementById("dataset-preview");
        if (previewElement) {
            const errorDiv = document.createElement("div");
            errorDiv.className = "ui negative message";
            errorDiv.innerHTML = `
                <div class="header">Error Displaying Parquet Information</div>
                <p>${escapeHTML(error.message)}</p>
                <p><a href="${fileUrl}" download class="ui button small">Download File</a></p>
            `;
            previewElement.appendChild(errorDiv);
        }
        
        throw error;
    }
}

// Helper function to extract filename from URL
function getFilenameFromUrl(url) {
    if (!url) return "unknown";
    const parts = url.split('/');
    return parts[parts.length - 1] || "unknown";
}

// Helper function to format file size
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " bytes";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + " MB";
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
}

// Helper function to safely escape HTML
function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    if (typeof str !== 'string') str = String(str);
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
function renderTable(result, fileUrl) {
    if (!result || result.numRows === 0) {
      return `<p>No rows found or table is empty.</p>
              <p><a href="${fileUrl}" download>Download Parquet</a></p>`;
    }
  
    // Grab column names
    const columns = result.columns;
    // Convert to array of rows
    const rows = [];
    for (let i = 0; i < result.numRows; i++) {
      const row = {};
      for (const colName of columns) {
        row[colName] = result.getValue(colName, i);
      }
      rows.push(row);
    }
  
    let html = `
      <p><strong>Rows:</strong> ${result.numRows} (showing 100 max)</p>
      <table border="1" cellpadding="5" style="border-collapse: collapse;">
        <thead>
          <tr>
    `;
    for (const colName of columns) {
      html += `<th>${escapeHTML(colName)}</th>`;
    }
    html += `</tr></thead><tbody>`;
  
    for (const row of rows) {
      html += `<tr>`;
      for (const colName of columns) {
        const val = row[colName];
        html += `<td>${escapeHTML(String(val ?? ""))}</td>`;
      }
      html += `</tr>`;
    }
    html += `</tbody></table>`;
  
    html += `
      <p><a href="${fileUrl}" download>Download Parquet File</a></p>
    `;
  
    return html;
  }
  
// Function for CSV files
async function loadCSV(fileUrl) {
    console.log("Loading CSV file from URL:", fileUrl);
    
    try {
        const response = await fetch(fileUrl);
        if (!response.ok) {
            throw new Error(`Failed to fetch CSV: ${response.status} ${response.statusText}`);
        }
        
        const csvText = await response.text();
        const lines = csvText.split(/\r?\n/).filter(line => line.trim() !== '');
        
        if (lines.length === 0) {
            throw new Error("CSV file is empty");
        }
        
        // Parse the header row
        const headers = parseCSVRow(lines[0]);
        
        // Parse the data rows (limit to 100 rows for performance)
        const maxRows = Math.min(lines.length - 1, 100);
        const rows = [];
        
        for (let i = 1; i <= maxRows; i++) {
            if (lines[i].trim() !== '') {
                rows.push(parseCSVRow(lines[i]));
            }
        }
        
        // Create the table UI
        const previewElement = document.getElementById("dataset-preview");
        
        // Create a container
        const container = document.createElement("div");
        container.className = "ui segment";
        container.innerHTML = `
            <h3 class="ui header">
                <i class="table icon"></i>
                <div class="content">
                    CSV Dataset: ${escapeHTML(getFilenameFromUrl(fileUrl))}
                    <div class="sub header">${rows.length} rows × ${headers.length} columns</div>
                </div>
            </h3>
        `;
        
        // Create a table
        const table = document.createElement("table");
        table.className = "ui celled table";
        
        // Create header
        let tableHTML = '<thead><tr>';
        for (const header of headers) {
            tableHTML += `<th>${escapeHTML(header)}</th>`;
        }
        tableHTML += '</tr></thead><tbody>';
        
        // Create rows
        for (const row of rows) {
            tableHTML += '<tr>';
            for (let i = 0; i < headers.length; i++) {
                const value = i < row.length ? row[i] : '';
                tableHTML += `<td>${escapeHTML(value)}</td>`;
            }
            tableHTML += '</tr>';
        }
        
        tableHTML += '</tbody>';
        table.innerHTML = tableHTML;
        
        // Add the table to the container
        container.appendChild(table);
        
        // Add a note if we're limiting the rows
        if (lines.length > 101) {
            const note = document.createElement('div');
            note.className = 'ui message';
            note.innerHTML = `<p>Showing first 100 rows of ${lines.length - 1} total rows</p>`;
            container.appendChild(note);
        }
        
        // Add a download link
        const downloadDiv = document.createElement("div");
        downloadDiv.className = "ui basic segment";
        downloadDiv.innerHTML = `
            <a class="ui button small" href="${fileUrl}" download>
                <i class="download icon"></i> Download CSV File
            </a>
        `;
        container.appendChild(downloadDiv);
        
        // Add to preview element
        previewElement.appendChild(container);
        
    } catch (error) {
        console.error("Error loading CSV:", error);
        
        const previewElement = document.getElementById("dataset-preview");
        const errorDiv = document.createElement("div");
        errorDiv.className = "ui negative message";
        errorDiv.innerHTML = `
            <div class="header">Error Loading CSV File</div>
            <p>${escapeHTML(error.message)}</p>
            <p><a href="${fileUrl}" download class="ui button small">Download File</a></p>
        `;
        previewElement.appendChild(errorDiv);
    }
}


function parseCSVRow(row) {
    const result = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < row.length; i++) {
        const char = row[i];
        
        if (char === '"' && (i === 0 || row[i-1] !== '\\')) {
            inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
            result.push(current);
            current = '';
        } else {
            current += char;
        }
    }
    
    result.push(current);
    return result;
}

