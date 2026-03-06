#!/usr/bin/env python3
"""
Fix alpaca_options_provider.py import order
"""
import re

with open("wrdata/providers/alpaca_options_provider.py", "r") as f:
    content = f.read()

# Move the import before logger = logging.getLogger(__name__)
pattern = r'(import requests\nfrom typing import Optional, List, Dict, Any\nfrom datetime import datetime, date, timezone\nfrom decimal import Decimal\nimport re\nimport logging\n\nfrom wrdata\.providers\.base import BaseProvider\n\nlogger = logging\.getLogger\(__name__\)\n)(from wrdata\.models\.schemas import \(\n    DataResponse,\n    OptionsChainRequest,\n    OptionsChainResponse,\n    OptionsChainData,\n    OptionsGreeks,\n    OptionsTimeseriesRequest,\n    OptionsTimeseriesResponse,\n\))'

def fix_import(match):
    before = match.group(1)
    import_block = match.group(2)
    
    # Move import before logger
    new_before = before.replace("logger = logging.getLogger(__name__)\n", "")
    new_content = new_before + import_block + "\n\nlogger = logging.getLogger(__name__)\n"
    
    return new_content

new_content = re.sub(pattern, fix_import, content, count=1, flags=re.DOTALL)

if new_content != content:
    with open("wrdata/providers/alpaca_options_provider.py", "w") as f:
        f.write(new_content)
    print("Fixed import order in alpaca_options_provider.py")
else:
    print("Pattern not found, checking alternative...")
    # Try simpler fix
    lines = content.split('\n')
    new_lines = []
    import_block = []
    after_imports = []
    
    in_import_block = False
    for line in lines:
        if line.startswith("from wrdata.models.schemas import"):
            in_import_block = True
            import_block.append(line)
        elif in_import_block:
            import_block.append(line)
            if line.strip() == ")":
                in_import_block = False
        else:
            after_imports.append(line)
    
    # Reconstruct with imports before logger
    for line in after_imports:
        if line.strip() == "logger = logging.getLogger(__name__)":
            # Insert imports before logger
            new_lines.extend(import_block)
            new_lines.append("")
        new_lines.append(line)
    
    with open("wrdata/providers/alpaca_options_provider.py", "w") as f:
        f.write('\n'.join(new_lines))
    print("Fixed import order (alternative method)")
