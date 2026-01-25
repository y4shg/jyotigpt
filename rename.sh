#!/bin/bash

# Script to rename all variations of jyotigpt to JyotiGPT
# Preserves git-related items (.git/, .gitignore, etc.)

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting JyotiGPT to JyotiGPT renaming process...${NC}\n"

# Function to check if path is git-related
is_git_related() {
    local path="$1"
    if [[ "$path" =~ \.git || "$path" =~ \.github ]]; then
        return 0
    fi
    return 1
}

# Function to perform replacement with proper case handling
do_replacement() {
    local input="$1"
    echo "$input" | perl -pe '
        s/open([-_ ]*)web([-_ ]*)ui/
            my $sep1 = $1;
            my $sep2 = $2;
            my $orig = "open${sep1}web${sep2}ui";
            if ($orig eq uc($orig)) {
                "JYOTIGPT"
            } elsif ($orig =~ m![A-Z]!) {
                "JyotiGPT"
            } else {
                "jyotigpt"
            }
        /egi
    '
}

# Backup important files first
echo -e "${YELLOW}Creating backup...${NC}"
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Find all files except git-related ones and create manifest
find . -type f ! -path '*/.git/*' ! -path '*/.github/*' ! -name '.git*' > "$BACKUP_DIR/files_manifest.txt"
echo -e "${GREEN}Backup manifest created at $BACKUP_DIR/files_manifest.txt${NC}\n"

# Step 1: Replace content within files
echo -e "${YELLOW}Step 1: Replacing content within files...${NC}"
file_count=0

while IFS= read -r file; do
    if is_git_related "$file"; then
        continue
    fi
    
    # Skip binary files
    if file "$file" | grep -q "text\|JSON\|XML\|HTML\|script\|empty"; then
        # Create temporary file
        temp_file=$(mktemp)
        
        # Process file directly with Perl
        perl -pe '
            s/open([-_ ]*)web([-_ ]*)ui/
                my $sep1 = $1;
                my $sep2 = $2;
                my $orig = "open${sep1}web${sep2}ui";
                if ($orig eq uc($orig)) {
                    "JYOTIGPT"
                } elsif ($orig =~ m![A-Z]!) {
                    "JyotiGPT"
                } else {
                    "jyotigpt"
                }
            /egi
        ' "$file" > "$temp_file"
        
        # Only replace if changes were made
        if ! cmp -s "$file" "$temp_file"; then
            mv "$temp_file" "$file"
            ((file_count++))
            echo "  Updated: $file"
        else
            rm "$temp_file"
        fi
    fi
done < "$BACKUP_DIR/files_manifest.txt"

echo -e "${GREEN}Updated content in $file_count files${NC}\n"

# Step 2: Rename files
echo -e "${YELLOW}Step 2: Renaming files...${NC}"
rename_count=0

# Create a list of files to rename (to avoid issues with changing paths)
files_to_rename=()
while IFS= read -r file; do
    if is_git_related "$file"; then
        continue
    fi
    
    dir=$(dirname "$file")
    base=$(basename "$file")
    
    # Check if filename contains any variation (case-insensitive)
    if echo "$base" | grep -qiE "open[-_ ]*web[-_ ]*ui"; then
        new_base=$(do_replacement "$base")
        
        if [ "$base" != "$new_base" ]; then
            echo -e "  ${CYAN}Found: $base -> $new_base${NC}"
            files_to_rename+=("$file|$dir/$new_base")
        fi
    fi
done < "$BACKUP_DIR/files_manifest.txt"

# Perform the renames
for entry in "${files_to_rename[@]}"; do
    old_path="${entry%|*}"
    new_path="${entry#*|}"
    
    if [ -e "$old_path" ]; then
        mv "$old_path" "$new_path"
        echo "  Renamed: $old_path -> $new_path"
        ((rename_count++))
    fi
done

echo -e "${GREEN}Renamed $rename_count files${NC}\n"

# Step 3: Rename directories (bottom-up to avoid path issues)
echo -e "${YELLOW}Step 3: Renaming directories...${NC}"
dir_count=0

# Get directories sorted by depth (deepest first)
dirs_to_rename=()
while IFS= read -r dir; do
    if is_git_related "$dir"; then
        continue
    fi
    
    if [ "$dir" = "." ]; then
        continue
    fi
    
    parent=$(dirname "$dir")
    base=$(basename "$dir")
    
    # Check if directory name contains any variation (case-insensitive)
    if echo "$base" | grep -qiE "open[-_ ]*web[-_ ]*ui"; then
        new_base=$(do_replacement "$base")
        
        if [ "$base" != "$new_base" ] && [ ! -d "$parent/$new_base" ]; then
            echo -e "  ${CYAN}Found dir: $base -> $new_base${NC}"
            # Store with depth for sorting
            depth=$(echo "$dir" | tr -cd '/' | wc -c)
            dirs_to_rename+=("$depth|$dir|$parent/$new_base")
        fi
    fi
done < <(find . -type d ! -path '*/.git/*' ! -path '*/.github/*' ! -name '.git*')

# Sort by depth (deepest first) and rename
for entry in $(printf '%s\n' "${dirs_to_rename[@]}" | sort -rn); do
    old_path="${entry#*|}"
    old_path="${old_path%|*}"
    new_path="${entry##*|}"
    
    if [ -d "$old_path" ]; then
        mv "$old_path" "$new_path"
        echo "  Renamed: $old_path -> $new_path"
        ((dir_count++))
    fi
done

echo -e "${GREEN}Renamed $dir_count directories${NC}\n"

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Renaming complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Files content updated: ${YELLOW}$file_count${NC}"
echo -e "Files renamed: ${YELLOW}$rename_count${NC}"
echo -e "Directories renamed: ${YELLOW}$dir_count${NC}"
echo -e "Backup location: ${YELLOW}$BACKUP_DIR${NC}"
echo -e "\n${YELLOW}Note: Git-related files and directories were preserved.${NC}"
echo -e "${YELLOW}Review changes before committing to git.${NC}\n"