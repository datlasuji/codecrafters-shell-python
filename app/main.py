import sys
import subprocess
import os

BUILTINS = ["exit", "type", "echo", "pwd", "cd"]

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
    command = parts[0]

    # exit builtin
    if command == "exit":
        sys.exit(0)

    # pwd builtin
    if command == "pwd":
        sys.stdout.write(os.getcwd() + "\n")
        sys.stdout.flush()
        continue

    # cd builtin (supports ~)
    if command == "cd":
        if len(parts) < 2:
            continue

        path = parts[1]

        # expand ~
        if path == "~":
            path = os.environ.get("HOME", "")
        elif path.startswith("~/"):
            path = os.path.join(os.environ.get("HOME", ""), path[2:])

        try:
            os.chdir(path)
        except FileNotFoundError:
            sys.stdout.write(f"cd: {path}: No such file or directory\n")
            sys.stdout.flush()
        continue

    # type builtin
    if command == "type":
        if len(parts) < 2:
            continue

        target = parts[1]

        if target in BUILTINS:
            sys.stdout.write(f"{target} is a shell builtin\n")
            sys.stdout.flush()
            continue

        found_path = None
        for p in os.environ.get("PATH", "").split(":"):
            full_path = os.path.join(p, target)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                found_path = full_path
                break

        if found_path:
            sys.stdout.write(f"{target} is {found_path}\n")
        else:
            sys.stdout.write(f"{target}: not found\n")

        sys.stdout.flush()
        continue

    # external commands
    try:
        subprocess.run(parts)
    except FileNotFoundError:
        sys.stdout.write(f"{command}: command not found\n")
        sys.stdout.flush()
