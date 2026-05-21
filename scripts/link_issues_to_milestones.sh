#!/bin/bash
while IFS=$'\t' read -r number labels; do
    milestone=""
    
    # Milestone 1 logic
    if echo "$labels" | grep -qE "extraction|processing|infrastructure"; then
        milestone="Phase 1: Data Infrastructure & Integration"
    # Milestone 2 logic
    elif echo "$labels" | grep -qE "derivation"; then
        milestone="Phase 2: Parameter Derivation & Mining"
    # Milestone 3 logic
    elif echo "$labels" | grep -qE "validation|foundation|documentation|paper|collaboration|integration|workshop"; then
        milestone="Phase 3: Validation & Paper Submission"
    fi
    
    if [ -n "$milestone" ]; then
        echo "Linking issue #$number to milestone: $milestone"
        gh issue edit "$number" --milestone "$milestone"
    fi
done < issues_labels.tsv
