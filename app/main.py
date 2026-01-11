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

    i = 0
    while i < len(line):
        ch = line[i]

        if escape:
            current += ch
            escape = False
            i += 1
            continue

        if ch == "\\":
            if not in_single and not in_double:
                escape = True
                i += 1
                continue
            if in_double and i + 1 < len(line) and line[i + 1] in ['\\', '"']:
                current += line[i + 1]
                i += 2
                continue
            current += "\\"
            i += 1
            continue

        if ch == "'" and not in_double:
            in_single = not in_single
            i += 1
            continue

        if ch == '"' and not in_single:
            in_double = not in_double
            i += 1
            continue

        if ch == " " and not in_single and not in_double:
            if current:
                args.append(current)
                current = ""
        else:
            current += ch

        i += 1

    if current:
        args.append(current)

    return args


while True:
    sys.stdout.write("$ ")
    sys.stdout.flush()

    line = sys.stdin.readline()
    if not line:
        break

    line = line.rstrip("\n")
    if not line.strip():
        continue

    parts = parse_command(line)

    # 🔴 FIX: handle > and 1>
    output_file = None
    redirect_idx = None

    for i, token in enumerate(parts):
        if token == ">" or token == "1>":
            redirect_idx = i
            break

    if redirect_idx is not None:
        output_file = parts[redirect_idx + 1]
        parts = parts[:redirect_idx]

    command = parts[0]

    # exit builtin
    if command == "exit":
        sys.exit(0)

    # pwd builtin
    if command == "pwd":
        sys.stdout.write(os.getcwd() + "\n")
        sys.stdout.flush()
        continue

    # cd builtin
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

    # external command (with stdout redirection)
    try:
        if output_file:
            with open(output_file, "w") as f:
                subprocess.run(parts, stdout=f)
        else:
            subprocess.run(parts)
    except FileNotFoundError:
        sys.stdout.write(f"{command}: command not found\n")
        sys.stdout.flush()
