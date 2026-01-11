import sys
import subprocess

while True:
    # Print prompt
    sys.stdout.write("$ ")
    sys.stdout.flush()

    line = sys.stdin.readline()
    if not line:
        break  # EOF

    line = line.strip()
    if not line:
        continue

    parts = line.split()

    # exit builtin
    if parts[0] == "exit":
        sys.exit(0)

    try:
        subprocess.run(parts)
    except FileNotFoundError:
        sys.stdout.write(f"{parts[0]}: command not found\n")
        sys.stdout.flush()
