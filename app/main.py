import sys
import subprocess
import os

BUILTINS = ["exit", "type", "echo", "pwd", "cd"]

def parse_command(line):
    args = []
    current = ""
    in_single = False
    in_double = False
    escape = False

    for ch in line:
        if escape:
            current += ch
            escape = False
            continue

        # backslash works only outside quotes
        if ch == "\\" and not in_single and not in_double:
            escape = True
            continue

        if ch == "'" and not in_double:
            in_single = not in_single
            continue

        if ch == '"' and not in_single:
            in_double = not in_double
            continue

        if ch == " " and not in_single and not in_double:
            if current:
                args.append(current)
                current = ""
        else:
            current += ch

    if current:
        args.append(current)

    return args


while True:
    # print prompt
    sys.stdout.write("$ ")
    sys.stdout.flush()

    line = sys.stdin.readline()
    if not line:
        break

    line = line.rstrip("\n")
    if not line.strip():
        continue

    parts = parse_command(line)
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

        found = None
        for p in os.environ.get("PATH", "").split(":"):
            full = os.path.join(p, target)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                found = full
                break

        if found:
            sys.stdout.write(f"{target} is {found}\n")
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
