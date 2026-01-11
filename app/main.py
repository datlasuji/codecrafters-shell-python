import sys
import subprocess
import os

BUILTINS = ["exit", "type", "echo"]


while True:
    # Print prompt
    sys.stdout.write("$ ")
    sys.stdout.flush()

    line = sys.stdin.readline()
    if not line:
        break

    line = line.strip()
    if not line:
        continue

    parts = line.split()
    command = parts[0]

    # exit builtin
    if command == "exit":
        sys.exit(0)

    # type builtin
    if command == "type":
        if len(parts) < 2:
            continue

        target = parts[1]

        if target in BUILTINS:
            sys.stdout.write(f"{target} is a shell builtin\n")
            sys.stdout.flush()
            continue

        found = False
        for path in os.environ.get("PATH", "").split(":"):
            full_path = os.path.join(path, target)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                sys.stdout.write(f"{target} is {full_path}\n")
                sys.stdout.flush()
                found = True
                break

        if not found:
            sys.stdout.write(f"{target}: not found\n")
            sys.stdout.flush()

        continue

    # external commands
    try:
        subprocess.run(parts)
    except FileNotFoundError:
        sys.stdout.write(f"{command}: command not found\n")
        sys.stdout.flush()
