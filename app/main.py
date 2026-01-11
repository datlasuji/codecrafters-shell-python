import sys
import subprocess

# Print prompt
sys.stdout.write("$ ")
sys.stdout.flush()

# Read command
line = sys.stdin.readline().strip()

if line:
    parts = line.split()
    try:
        subprocess.run(parts)
    except FileNotFoundError:
        sys.stdout.write(f"{parts[0]}: command not found\n")
        sys.stdout.flush()
