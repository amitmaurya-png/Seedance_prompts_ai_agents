"""Plain-code helpers used by the nodes (no LLM calls).

    skit_pdf          read the skit PDF and split it into scenes
    breakdown_text    the breakdown as script text, speakers and locations
    verbatim          check actions and dialogue are copied word for word
    clips             clip rules: durations, fixed fields, hand-offs, speakers
    prompt_repair     fix and check a director prompt
    seedance_request  build Seedance API requests and curl commands
    json_files        write output files (with backups)
    checkpoints       reuse saved LLM results instead of calling again
"""
