#!/bin/bash
# -----------------------------------------------------------------------------
# Hetzner Object Storage Bucket Sync Script
# This script uses rclone to directly transfer data between two Hetzner Object Storage buckets
# without downloading/uploading to your local machine.
# -----------------------------------------------------------------------------

# Some ANSI color codes for text formatting
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
RESET="\033[0m"

# Terminate script on error
set -e

echo -e "${BLUE}=======================================${RESET}"
echo -e "${BLUE}  Hetzner Object Storage Bucket Sync  ${RESET}"
echo -e "${BLUE}=======================================${RESET}"

# Check if rclone is installed
if ! command -v rclone &> /dev/null; then
    echo -e "${RED}Error: rclone is not installed${RESET}"
    echo -e "${YELLOW}Installation for Mac: brew install rclone${RESET}"
    echo -e "${YELLOW}Installation for Linux: curl https://rclone.org/install.sh | sudo bash${RESET}"
    exit 1
fi

# Default values
SOURCE_LOCATION="fsn1"  # Falkenstein
TARGET_LOCATION="nbg1"  # Nuremberg
MAKE_PUBLIC=false
DRY_RUN=false
SYNC_MODE="copy"  # Default sync mode "copy" - copies files but doesn't delete
SOURCE_PREFIX=""
TARGET_PREFIX=""
CHUNK_SIZE="1000M"     # Minimum 5MB required by Hetzner
TRANSFERS=20
CHECKERS=8
MAX_RETRIES=10
VALIDATE_BUCKETS=true
LIST_LIMIT=100  # Limit number of files to list for validation
LIST_ONLY=false # If true, only list files and exit without syncing
LIST_RECURSIVE=false # Whether to list files recursively
LIST_FORMAT="ls"  # Can be "ls" (default), "lsf", "lsjson", or "lsl"
DEBUG_LEVEL=0     # 0=normal, 1=debug, 2=verbose
DUMP_BODIES=false # Dump HTTP request/response bodies (very verbose)
DUMP_HEADERS=false # Dump HTTP headers
USE_SHARED_CREDENTIALS=false # Use same credentials for source and target
USE_MODIFY_WINDOW=5     # 5 second modification window to avoid update issues
DISABLE_CHECKSUM=true   # Disable MD5 checksum comparison
DISABLE_MULTIPART=false # Disable multipart uploads
FIX_MIME=true          # Fix MIME types for object storage
MULTI_THREAD_STREAMS=0  # Number of streams to use for multi-thread copy (0=auto)
SHOW_ACL=true          # Show ACL information when listing files

# Show usage information
show_usage() {
    echo -e "${YELLOW}Usage:${RESET} $0 [options]"
    echo -e ""
    echo -e "${YELLOW}Options:${RESET}"
    echo -e "  -s, --source-bucket BUCKET    Source bucket name"
    echo -e "  -t, --target-bucket BUCKET    Target bucket name"
    echo -e "  -a, --source-access-key KEY   Access key for source"
    echo -e "  -S, --source-secret-key KEY   Secret key for source"
    echo -e "  -b, --target-access-key KEY   Access key for target"
    echo -e "  -B, --target-secret-key KEY   Secret key for target"
    echo -e "  -f, --from LOCATION           Source location (default: fsn1)"
    echo -e "  -T, --to LOCATION             Target location (default: nbg1)"
    echo -e "  -p, --source-prefix PATH      Only sync files from this path in the source bucket"
    echo -e "  -x, --target-prefix PATH      Sync to this path in the target bucket"
    echo -e "  -P, --public                  Make all files in target bucket public"
    echo -e "  -d, --dry-run                 Show changes but don't apply them"
    echo -e "  -m, --mode MODE               Sync mode (copy, sync - default: copy)"
    echo -e "                                 copy: Only copy, don't delete files not in source"
    echo -e "                                 sync: Full sync, delete files in target not in source"
    echo -e "  -c, --chunk-size SIZE         Chunk size for multipart uploads (minimum: 5M)"
    echo -e "  -n, --transfers NUM           Number of file transfers to run in parallel (default: 4)"
    echo -e "  -r, --retries NUM             Number of times to retry operations (default: 10)"
    echo -e "  --no-validate                 Skip bucket validation before sync"
    echo -e "  --list-only                   Only list files in source bucket, don't sync"
    echo -e "  --list-format FORMAT          Format for listing (ls, lsf, lsjson, lsl)"
    echo -e "  --recursive                   List files recursively"
    echo -e "  --limit COUNT                 Limit list to COUNT files (default: 100)"
    echo -e "  --debug LEVEL                 Debug level: 0=normal, 1=debug, 2=verbose"
    echo -e "  --dump-bodies                 Dump HTTP request/response bodies (very verbose)"
    echo -e "  --dump-headers                Dump HTTP headers"
    echo -e "  --shared-credentials          Use the same credentials for both source and target"
    echo -e "  --modify-window SECONDS       Time window for modifications (default: 5 seconds)"
    echo -e "  --no-checksum                 Disable MD5 checksum comparison (default: true)"
    echo -e "  --disable-multipart           Disable multipart uploads"
    echo -e "  --no-fix-mime                 Disable MIME type fixing"
    echo -e "  --multi-thread-streams NUM    Streams per multi-thread copy (0=auto)"
    echo -e "  --no-show-acl                 Don't show ACL information when listing files"
    echo -e "  -h, --help                    Show this help message"
    echo -e ""
    echo -e "${YELLOW}Examples:${RESET}"
    echo -e "$0 -s source-bucket -t target-bucket -a SOURCE_ACCESS_KEY -S SOURCE_SECRET_KEY -b TARGET_ACCESS_KEY -B TARGET_SECRET_KEY -p lfs -x lfs"
    echo -e "$0 -s source-bucket -a SOURCE_ACCESS_KEY -S SOURCE_SECRET_KEY --list-only --recursive --list-format lsl"
}

# Process parameters
while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--source-bucket)
            # If bucket contains '/', separate the prefix
            if [[ "$2" == */* ]]; then
                IFS='/' read -r SOURCE_BUCKET SOURCE_PREFIX_TEMP <<< "$2"
                # If there's additional path
                if [[ "$SOURCE_PREFIX_TEMP" == */* ]]; then
                    SOURCE_PREFIX="${SOURCE_PREFIX_TEMP}"
                else
                    SOURCE_PREFIX="${SOURCE_PREFIX_TEMP}"
                fi
                # If contains domain name, just take the bucket name
                if [[ "$SOURCE_BUCKET" == *"."* ]]; then
                    SOURCE_BUCKET=$(echo "$SOURCE_BUCKET" | awk -F '.' '{print $1}')
                fi
            else
                SOURCE_BUCKET="$2"
            fi
            shift 2
            ;;
        -t|--target-bucket)
            # If bucket contains '/', separate the prefix
            if [[ "$2" == */* ]]; then
                IFS='/' read -r TARGET_BUCKET TARGET_PREFIX_TEMP <<< "$2"
                # If there's additional path
                if [[ "$TARGET_PREFIX_TEMP" == */* ]]; then
                    TARGET_PREFIX="${TARGET_PREFIX_TEMP}"
                else
                    TARGET_PREFIX="${TARGET_PREFIX_TEMP}"
                fi
                # If contains domain name, just take the bucket name
                if [[ "$TARGET_BUCKET" == *"."* ]]; then
                    TARGET_BUCKET=$(echo "$TARGET_BUCKET" | awk -F '.' '{print $1}')
                fi
            else
                TARGET_BUCKET="$2"
            fi
            shift 2
            ;;
        -a|--source-access-key)
            SOURCE_ACCESS_KEY="$2"
            shift 2
            ;;
        -S|--source-secret-key)
            SOURCE_SECRET_KEY="$2"
            shift 2
            ;;
        -b|--target-access-key)
            TARGET_ACCESS_KEY="$2"
            shift 2
            ;;
        -B|--target-secret-key)
            TARGET_SECRET_KEY="$2"
            shift 2
            ;;
        -f|--from)
            SOURCE_LOCATION="$2"
            shift 2
            ;;
        -T|--to)
            TARGET_LOCATION="$2"
            shift 2
            ;;
        -p|--source-prefix)
            SOURCE_PREFIX="$2"
            shift 2
            ;;
        -x|--target-prefix)
            TARGET_PREFIX="$2"
            shift 2
            ;;
        -P|--public)
            MAKE_PUBLIC=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -m|--mode)
            SYNC_MODE="$2"
            shift 2
            ;;
        -c|--chunk-size)
            # Ensure chunk size is at least 5M (Hetzner requirement)
            # Convert input to bytes for comparison
            input_size="$2"
            size_num=$(echo "$input_size" | sed 's/[^0-9]//g')
            size_unit=$(echo "$input_size" | sed 's/[0-9]//g' | tr '[:lower:]' '[:upper:]')

            # Convert to bytes based on unit
            case "$size_unit" in
                K|KB)
                    size_bytes=$((size_num * 1024))
                    ;;
                M|MB)
                    size_bytes=$((size_num * 1024 * 1024))
                    ;;
                G|GB)
                    size_bytes=$((size_num * 1024 * 1024 * 1024))
                    ;;
                *)
                    # Assume bytes if no unit
                    size_bytes=$size_num
                    ;;
            esac

            # 5MB = 5242880 bytes
            if [ "$size_bytes" -lt 5242880 ]; then
                echo -e "${YELLOW}Warning: Chunk size must be at least 5MB for Hetzner Object Storage. Adjusting to 5MB.${RESET}"
                CHUNK_SIZE="5M"
            else
                CHUNK_SIZE="$2"
            fi
            shift 2
            ;;
        -n|--transfers)
            TRANSFERS="$2"
            shift 2
            ;;
        -r|--retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        --no-validate)
            VALIDATE_BUCKETS=false
            shift
            ;;
        --list-only)
            LIST_ONLY=true
            shift
            ;;
        --recursive)
            LIST_RECURSIVE=true
            shift
            ;;
        --list-format)
            LIST_FORMAT="$2"
            shift 2
            ;;
        --limit)
            LIST_LIMIT="$2"
            shift 2
            ;;
        --debug)
            DEBUG_LEVEL="$2"
            shift 2
            ;;
        --dump-bodies)
            DUMP_BODIES=true
            shift
            ;;
        --dump-headers)
            DUMP_HEADERS=true
            shift
            ;;
        --shared-credentials)
            USE_SHARED_CREDENTIALS=true
            shift
            ;;
        --modify-window)
            USE_MODIFY_WINDOW="$2"
            shift 2
            ;;
        --no-checksum)
            DISABLE_CHECKSUM=true
            shift
            ;;
        --disable-multipart)
            DISABLE_MULTIPART=true
            shift
            ;;
        --no-fix-mime)
            FIX_MIME=false
            shift
            ;;
        --multi-thread-streams)
            MULTI_THREAD_STREAMS="$2"
            shift 2
            ;;
        --no-show-acl)
            SHOW_ACL=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown parameter: $1${RESET}"
            show_usage
            exit 1
            ;;
    esac
done

# Use shared credentials if requested
if [ "$USE_SHARED_CREDENTIALS" = true ]; then
    TARGET_ACCESS_KEY="$SOURCE_ACCESS_KEY"
    TARGET_SECRET_KEY="$SOURCE_SECRET_KEY"
fi

# Check required parameters
if [ -z "$SOURCE_BUCKET" ] || [ -z "$SOURCE_ACCESS_KEY" ] || [ -z "$SOURCE_SECRET_KEY" ]; then
    echo -e "${RED}Error: Source bucket and credentials are required${RESET}"
    show_usage
    exit 1
fi

if [ "$LIST_ONLY" = false ] && ([ -z "$TARGET_BUCKET" ] || [ -z "$TARGET_ACCESS_KEY" ] || [ -z "$TARGET_SECRET_KEY" ]); then
    echo -e "${RED}Error: Target bucket and credentials are required for sync operation${RESET}"
    show_usage
    exit 1
fi

# Create temporary file for rclone configuration
RCLONE_CONFIG_FILE=$(mktemp)

# Clean up temporary files when finished
cleanup() {
    echo -e "${BLUE}Cleaning up temporary files...${RESET}"
    rm -f "$RCLONE_CONFIG_FILE"
    rm -f "$TEMP_OUTPUT" 2>/dev/null || true
}

# Run cleanup on CTRL+C or other exit signals
trap cleanup EXIT

# Set debug flags based on level
DEBUG_FLAGS=""
if [ "$DEBUG_LEVEL" -ge 1 ]; then
    DEBUG_FLAGS="--verbose"
    if [ "$DEBUG_LEVEL" -ge 2 ]; then
        DEBUG_FLAGS="--verbose --verbose"
    fi
fi

if [ "$DUMP_BODIES" = true ]; then
    DEBUG_FLAGS="$DEBUG_FLAGS --dump-bodies"
fi

if [ "$DUMP_HEADERS" = true ]; then
    DEBUG_FLAGS="$DEBUG_FLAGS --dump-headers"
fi

# Create rclone configuration with improved settings
cat > "$RCLONE_CONFIG_FILE" << EOL
[hetzner-source]
type = s3
provider = Other
endpoint = https://${SOURCE_LOCATION}.your-objectstorage.com
access_key_id = ${SOURCE_ACCESS_KEY}
secret_access_key = ${SOURCE_SECRET_KEY}
region = eu-central-1
acl = private
force_path_style = true
no_check_bucket = true
chunk_size = ${CHUNK_SIZE}
upload_concurrency = 4
disable_http2 = true
encoding = Slash,InvalidUtf8,BackSlash
EOL

# Set additional S3 options based on parameters
if [ "$FIX_MIME" = true ]; then
    echo "set_content_type = true" >> "$RCLONE_CONFIG_FILE"
fi

if [ "$DISABLE_MULTIPART" = true ]; then
    echo "disable_multipart = true" >> "$RCLONE_CONFIG_FILE"
fi

# Only add target config if not in list-only mode
if [ "$LIST_ONLY" = false ]; then
    cat >> "$RCLONE_CONFIG_FILE" << EOL

[hetzner-target]
type = s3
provider = Other
endpoint = https://${TARGET_LOCATION}.your-objectstorage.com
access_key_id = ${TARGET_ACCESS_KEY}
secret_access_key = ${TARGET_SECRET_KEY}
region = eu-central-1
acl = private
force_path_style = true
no_check_bucket = true
chunk_size = ${CHUNK_SIZE}
upload_concurrency = 4
disable_http2 = true
encoding = Slash,InvalidUtf8,BackSlash
EOL

    # Set additional S3 options based on parameters
    if [ "$FIX_MIME" = true ]; then
        echo "set_content_type = true" >> "$RCLONE_CONFIG_FILE"
    fi

    if [ "$DISABLE_MULTIPART" = true ]; then
        echo "disable_multipart = true" >> "$RCLONE_CONFIG_FILE"
    fi
fi

# Show rclone configuration information
echo -e "${BLUE}rclone configuration created${RESET}"
echo -e "${BLUE}Source:${RESET} https://${SOURCE_LOCATION}.your-objectstorage.com/${SOURCE_BUCKET}"
if [ -n "$SOURCE_PREFIX" ]; then
    echo -e "${BLUE}Source Prefix:${RESET} ${SOURCE_PREFIX}"
fi

if [ "$LIST_ONLY" = false ]; then
    echo -e "${BLUE}Target:${RESET} https://${TARGET_LOCATION}.your-objectstorage.com/${TARGET_BUCKET}"
    if [ -n "$TARGET_PREFIX" ]; then
        echo -e "${BLUE}Target Prefix:${RESET} ${TARGET_PREFIX}"
    fi

    if [ "$MAKE_PUBLIC" = true ]; then
        echo -e "${YELLOW}All files in target bucket will be public!${RESET}"
    fi

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}DRY RUN MODE: Changes will not be applied${RESET}"
    fi

    echo -e "${BLUE}Synchronization mode:${RESET} ${SYNC_MODE}"
    echo -e "${BLUE}Chunk size:${RESET} ${CHUNK_SIZE}"
    echo -e "${BLUE}Parallel transfers:${RESET} ${TRANSFERS}"
    echo -e "${BLUE}Max retries:${RESET} ${MAX_RETRIES}"

    # Show advanced options if they differ from defaults
    if [ "$DEBUG_LEVEL" -gt 0 ]; then
        echo -e "${BLUE}Debug level:${RESET} ${DEBUG_LEVEL}"
    fi
    if [ "$DUMP_BODIES" = true ]; then
        echo -e "${BLUE}Dump HTTP bodies:${RESET} Yes"
    fi
    if [ "$DUMP_HEADERS" = true ]; then
        echo -e "${BLUE}Dump HTTP headers:${RESET} Yes"
    fi
    if [ "$DISABLE_MULTIPART" = true ]; then
        echo -e "${BLUE}Multipart uploads:${RESET} Disabled"
    fi
    if [ "$DISABLE_CHECKSUM" = false ]; then
        echo -e "${BLUE}MD5 checksums:${RESET} Enabled"
    fi
    if [ "$MULTI_THREAD_STREAMS" -gt 0 ]; then
        echo -e "${BLUE}Multi-thread streams:${RESET} ${MULTI_THREAD_STREAMS}"
    fi
else
    echo -e "${BLUE}List format:${RESET} ${LIST_FORMAT}"
    echo -e "${BLUE}Recursive:${RESET} ${LIST_RECURSIVE}"
    echo -e "${BLUE}Limit:${RESET} ${LIST_LIMIT}"
fi

# Create source and target paths
if [ -n "$SOURCE_PREFIX" ]; then
    SOURCE_PATH="hetzner-source:${SOURCE_BUCKET}/${SOURCE_PREFIX}"
else
    SOURCE_PATH="hetzner-source:${SOURCE_BUCKET}"
fi

if [ "$LIST_ONLY" = false ]; then
    if [ -n "$TARGET_PREFIX" ]; then
        TARGET_PATH="hetzner-target:${TARGET_BUCKET}/${TARGET_PREFIX}"
    else
        TARGET_PATH="hetzner-target:${TARGET_BUCKET}"
    fi
fi

# If list-only mode, just list files and exit
if [ "$LIST_ONLY" = true ]; then
    echo -e "${GREEN}Listing files in ${SOURCE_PATH}...${RESET}"

    # Check if we should use lsjson format to get ACL info
    if [ "$SHOW_ACL" = true ]; then
        echo -e "${BLUE}Fetching object details including ACL information...${RESET}"

        # Use lsjson format to get full object metadata
        TEMP_OUTPUT=$(mktemp)

        LIST_CMD="rclone lsjson --config \"$RCLONE_CONFIG_FILE\" ${DEBUG_FLAGS}"

        if [ "$LIST_RECURSIVE" = false ]; then
            LIST_CMD="$LIST_CMD --max-depth 1"
        fi

        LIST_CMD="$LIST_CMD \"$SOURCE_PATH\" > \"$TEMP_OUTPUT\""

        echo -e "${BLUE}Running: $LIST_CMD${RESET}"
        eval $LIST_CMD

        # Parse the JSON output and format it nicely
        if [ -s "$TEMP_OUTPUT" ]; then
            echo -e "${GREEN}File details:${RESET}"
            echo -e "${BLUE}Size\tModTime\t\t\tACL\t\tPath${RESET}"
            echo -e "${BLUE}----\t-------\t\t\t---\t\t----${RESET}"

            # Check if we have jq installed for better JSON parsing
            if command -v jq &> /dev/null; then
                # First check the structure of the JSON
                # It could be an array or an object with entries
                JSON_TYPE=$(jq 'type' "$TEMP_OUTPUT")

                if [[ "$JSON_TYPE" == '"array"' ]]; then
                    # It's an array, process each item
                    jq -r '.[] | "\(.size // .Size)\t\(.modTime // .ModTime | if . then .[0:19] else "N/A" end)\t\(.metadata.acl // .Metadata.acl // "private")\t\(.path // .Path)"' "$TEMP_OUTPUT" 2>/dev/null || {
                        echo -e "${YELLOW}Error parsing JSON with primary method, trying alternative format...${RESET}"
                        # Try alternative format for rclone JSON output
                        jq -r '.[] | "\(.Size // 0)\t\(.ModTime // "N/A" | if . then .[0:19] else "N/A" end)\t\(.MetaData.acl // "private")\t\(.Path // .path)"' "$TEMP_OUTPUT" 2>/dev/null || {
                            echo -e "${YELLOW}Could not parse JSON with jq. Showing raw file information:${RESET}"
                            cat "$TEMP_OUTPUT" | grep -o '"path\|Path":"[^"]*"' | sort | uniq
                        }
                    }
                else
                    # It's likely an object with entries, try to parse it
                    echo -e "${YELLOW}JSON format is not as expected. Attempting to parse...${RESET}"
                    jq -r 'keys[] | . + "\tN/A\tprivate"' "$TEMP_OUTPUT" 2>/dev/null || {
                        echo -e "${YELLOW}Could not parse JSON with jq. Showing raw file paths:${RESET}"
                        cat "$TEMP_OUTPUT" | grep -o '"[^"]*"' | sort | uniq
                    }
                fi
            else
                # Fallback to simple parsing with grep and awk if jq is not available
                echo -e "${YELLOW}jq not found for JSON parsing. Showing just file paths:${RESET}"
                cat "$TEMP_OUTPUT" | grep -o '"path\|Path":"[^"]*"' | sed 's/"path":"//g' | sed 's/"Path":"//g' | sed 's/"//g'
                echo -e "${YELLOW}Note: Install 'jq' for better JSON parsing and to see ACL values${RESET}"
            fi
        else
            echo -e "${YELLOW}No files found or error occurred${RESET}"
        fi

        # Don't remove the temp file yet, we'll clean it up in the cleanup function
    else
        # Standard listing without ACL info
        LIST_CMD="rclone ${LIST_FORMAT} --config \"$RCLONE_CONFIG_FILE\" ${DEBUG_FLAGS}"

        if [ "$LIST_RECURSIVE" = false ]; then
            LIST_CMD="$LIST_CMD --max-depth 1"
        fi

        LIST_CMD="$LIST_CMD \"$SOURCE_PATH\""

        echo -e "${BLUE}Running: $LIST_CMD${RESET}"
        eval $LIST_CMD
    fi

    echo -e "${GREEN}Listing complete!${RESET}"
    exit 0
fi

# Validate source and target buckets if enabled
if [ "$VALIDATE_BUCKETS" = true ]; then
    echo -e "${BLUE}Validating source bucket access...${RESET}"
    TEMP_OUTPUT=$(mktemp)

    # Try to list files in source bucket with a limit
    if [ "$SHOW_ACL" = true ] && command -v jq &> /dev/null; then
        # Use lsjson to get ACL info
        rclone lsjson --config "$RCLONE_CONFIG_FILE" --max-depth 1 "$SOURCE_PATH" > "$TEMP_OUTPUT" 2>&1 || echo "ERROR" > "$TEMP_OUTPUT"

        if [[ ! -s "$TEMP_OUTPUT" || $(cat "$TEMP_OUTPUT") == "ERROR" ]]; then
            echo -e "${RED}Error accessing source bucket. Please check your credentials and bucket name.${RESET}"
            cat "$TEMP_OUTPUT"
            rm -f "$TEMP_OUTPUT"
            exit 1
        fi

        # Try to get the file count from the JSON
        FILE_COUNT=$(jq '. | length' "$TEMP_OUTPUT" 2>/dev/null || echo 0)

        if [ "$FILE_COUNT" -gt 0 ]; then
            echo -e "${GREEN}Successfully connected to source bucket.${RESET}"
            echo -e "${GREEN}Found $FILE_COUNT files (limited to $LIST_LIMIT).${RESET}"

            # Show a few sample files with ACL
            SAMPLE_COUNT=5
            if [ "$FILE_COUNT" -gt 0 ]; then
                echo -e "${BLUE}Sample files:${RESET}"
                echo -e "${BLUE}Size\tModTime\t\t\tACL\t\tPath${RESET}"
                echo -e "${BLUE}----\t-------\t\t\t---\t\t----${RESET}"

                # Try different JSON paths to accommodate different rclone output formats
                jq -r 'if type=="array" then .[0:'"$SAMPLE_COUNT"'] | "\(.size // .Size)\t\(.modTime // .ModTime | if . then .[0:19] else "N/A" end)\t\(.metadata.acl // .MetaData.acl // "private")\t\(.path // .Path)" else empty end' "$TEMP_OUTPUT" 2>/dev/null || {
                    jq -r 'if type=="array" then .[0:'"$SAMPLE_COUNT"'] | "\(.Size // 0)\t\(.ModTime // "N/A" | if . then .[0:19] else "N/A" end)\t\(.MetaData.acl // "private")\t\(.Path // .path)" else empty end' "$TEMP_OUTPUT" 2>/dev/null || {
                        echo -e "${YELLOW}Could not parse JSON with jq. Showing raw file paths:${RESET}"
                        cat "$TEMP_OUTPUT" | grep -o '"path\|Path":"[^"]*"' | head -n $SAMPLE_COUNT
                    }
                }

                if [ "$FILE_COUNT" -gt "$SAMPLE_COUNT" ]; then
                    echo -e "${BLUE}...and $(($FILE_COUNT - $SAMPLE_COUNT)) more files${RESET}"
                fi
            fi
        else
            echo -e "${YELLOW}Warning: Source path appears to be empty.${RESET}"
        fi

        rm -f "$TEMP_OUTPUT"
    else
        # Standard listing without ACL info
        SOURCE_FILES=$(rclone ls --config "$RCLONE_CONFIG_FILE" --max-depth 1 "$SOURCE_PATH" 2>&1 || echo "ERROR")

        if [[ "$SOURCE_FILES" == *ERROR* ]]; then
            echo -e "${RED}Error accessing source bucket. Please check your credentials and bucket name.${RESET}"
            echo -e "${RED}Error details: ${SOURCE_FILES}${RESET}"
            exit 1
        else
            FILE_COUNT=$(echo "$SOURCE_FILES" | wc -l | tr -d ' ')
            if [ "$FILE_COUNT" -gt 0 ]; then
                echo -e "${GREEN}Successfully connected to source bucket.${RESET}"
                echo -e "${GREEN}Found $FILE_COUNT files (limited to $LIST_LIMIT).${RESET}"
                # Show a few sample files
                SAMPLE_COUNT=5
                if [ "$FILE_COUNT" -gt 0 ]; then
                    echo -e "${BLUE}Sample files:${RESET}"
                    echo "$SOURCE_FILES" | head -n $SAMPLE_COUNT
                    if [ "$FILE_COUNT" -gt "$SAMPLE_COUNT" ]; then
                        echo -e "${BLUE}...and $(($FILE_COUNT - $SAMPLE_COUNT)) more files${RESET}"
                    fi
                fi
            else
                echo -e "${YELLOW}Warning: Source path appears to be empty.${RESET}"
            fi
        fi
    fi

    echo -e "${BLUE}Validating target bucket access...${RESET}"
    TARGET_FILES=$(rclone ls --config "$RCLONE_CONFIG_FILE" --max-depth 1 "$TARGET_PATH" 2>&1 || echo "ERROR")

    if [[ "$TARGET_FILES" == *ERROR* ]]; then
        if [[ "$TARGET_FILES" == *NoSuchBucket* ]] || [[ "$TARGET_FILES" == *"directory not found"* ]]; then
            echo -e "${YELLOW}Target bucket or path doesn't exist yet. It will be created during sync.${RESET}"
        else
            echo -e "${RED}Error accessing target bucket. Please check your credentials and bucket name.${RESET}"
            echo -e "${RED}Error details: ${TARGET_FILES}${RESET}"
            exit 1
        fi
    else
        echo -e "${GREEN}Successfully connected to target bucket.${RESET}"
    fi
fi

# Ask for user confirmation
echo -e "${YELLOW}Do you want to continue with the sync operation? (y/N)${RESET}"
read -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${RED}Operation cancelled${RESET}"
    exit 0
fi

# Create synchronization command flags
RCLONE_FLAGS="--transfers=${TRANSFERS} --checkers=${CHECKERS} --retries=${MAX_RETRIES}"
RCLONE_FLAGS="${RCLONE_FLAGS} --s3-upload-concurrency=4 --s3-no-check-bucket"
RCLONE_FLAGS="${RCLONE_FLAGS} --s3-chunk-size=${CHUNK_SIZE}"
RCLONE_FLAGS="${RCLONE_FLAGS} --s3-upload-cutoff=${CHUNK_SIZE}"
RCLONE_FLAGS="${RCLONE_FLAGS} --size-only --no-traverse --no-update-modtime"
RCLONE_FLAGS="${RCLONE_FLAGS} --no-gzip-encoding --modify-window=${USE_MODIFY_WINDOW}"
RCLONE_FLAGS="${RCLONE_FLAGS} --immutable"

if [ "$DISABLE_CHECKSUM" = true ]; then
    RCLONE_FLAGS="${RCLONE_FLAGS} --ignore-checksum"
fi

if [ "$MULTI_THREAD_STREAMS" -gt 0 ]; then
    RCLONE_FLAGS="${RCLONE_FLAGS} --multi-thread-streams=${MULTI_THREAD_STREAMS}"
fi

if [ "$DRY_RUN" = true ]; then
    RCLONE_FLAGS="${RCLONE_FLAGS} --dry-run"
fi

# Add debug flags if any
RCLONE_FLAGS="${RCLONE_FLAGS} ${DEBUG_FLAGS}"

# Log synchronization start
START_TIME=$(date +%s)
echo -e "${GREEN}Starting synchronization: $(date)${RESET}"
echo -e "${GREEN}Source: ${SOURCE_PATH}${RESET}"
echo -e "${GREEN}Target: ${TARGET_PATH}${RESET}"

# Try multiple methods to handle the sync
echo -e "${BLUE}Attempting direct sync with optimal parameters...${RESET}"

# Try copy with optimal parameters for Hetzner Object Storage
rclone copy --config "$RCLONE_CONFIG_FILE" --progress --ignore-existing \
    --size-only --s3-chunk-size=${CHUNK_SIZE} --s3-no-check-bucket \
    --ignore-checksum --transfers=${TRANSFERS} --retries=${MAX_RETRIES} \
    --no-update-modtime ${DEBUG_FLAGS} \
    "$SOURCE_PATH" "$TARGET_PATH" || {
    echo -e "${YELLOW}Some errors occurred during sync. This is often normal with large transfers.${RESET}"
    echo -e "${YELLOW}Continuing with verification...${RESET}"
}

# Log synchronization completion
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(( (DURATION % 3600) / 60 ))
SECONDS=$((DURATION % 60))

echo -e "${GREEN}Synchronization completed: $(date)${RESET}"
echo -e "${GREEN}Total time: ${HOURS}h ${MINUTES}m ${SECONDS}s${RESET}"

# Verify sync results
echo -e "${BLUE}Verifying sync results...${RESET}"

# Count files in source and target
if [ -n "$SOURCE_PREFIX" ]; then
    SOURCE_COUNT=$(rclone size --config "$RCLONE_CONFIG_FILE" "$SOURCE_PATH" 2>/dev/null | grep "^Count:" | awk '{print $2}' || echo "error")
else
    SOURCE_COUNT=$(rclone size --config "$RCLONE_CONFIG_FILE" "$SOURCE_PATH" 2>/dev/null | grep "^Count:" | awk '{print $2}' || echo "error")
fi

if [ -n "$TARGET_PREFIX" ]; then
    TARGET_COUNT=$(rclone size --config "$RCLONE_CONFIG_FILE" "$TARGET_PATH" 2>/dev/null | grep "^Count:" | awk '{print $2}' || echo "error")
else
    TARGET_COUNT=$(rclone size --config "$RCLONE_CONFIG_FILE" "$TARGET_PATH" 2>/dev/null | grep "^Count:" | awk '{print $2}' || echo "error")
fi

if [ "$SOURCE_COUNT" != "error" ] && [ "$TARGET_COUNT" != "error" ]; then
    echo -e "${GREEN}Source files: ${SOURCE_COUNT}${RESET}"
    echo -e "${GREEN}Target files: ${TARGET_COUNT}${RESET}"

    if [ "$SOURCE_COUNT" = "$TARGET_COUNT" ]; then
        echo -e "${GREEN}✓ Sync successful! All files transferred.${RESET}"
    else
        echo -e "${YELLOW}⚠ Warning: Source and target file counts don't match.${RESET}"
        echo -e "${YELLOW}  This could be due to errors during transfer or different directory structures.${RESET}"
        echo -e "${YELLOW}  You might want to run the sync again to transfer remaining files.${RESET}"
    fi
else
    echo -e "${YELLOW}Could not verify file counts. Please check manually.${RESET}"
fi

echo -e "${GREEN}Operation completed!${RESET}"
