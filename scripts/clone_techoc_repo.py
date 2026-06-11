#!/usr/bin/env python3
"""Clone techoc/fanqie-novel-api and inspect for word_number API."""
import subprocess, os

os.chdir(r"C:\Users\59314\claudework\ai-novel-skill-lab\scripts")

# Clone the repo shallow
result = subprocess.run(
    ["git", "clone", "--depth=1", "https://github.com/techoc/fanqie-novel-api.git"],
    capture_output=True, text=True
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
