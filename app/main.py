import sys
import subprocess

while True:
    # Print prompt
    sys.stdout.write("$ ")
    sys.stdout.flush()

    # Read input
    line = sys.stdin.readline()
    if not line:
        break  # EOF

    line = line.strip()
    if not line:
        continue

    parts = line.split()

    try:
        subprocess.run(parts)
    except FileNotFoundError:
        sys.stdout.write(f"{parts[0]}: command not found\n")
        sys.stdout.flush()
