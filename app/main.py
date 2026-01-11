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

    stdout_file = None
    stderr_file = None
    redirect_idx = None

    for i, token in enumerate(parts):
        if token in (">", "1>", "2>"):
            redirect_idx = i
            if token == "2>":
                stderr_file = parts[i + 1]
            else:
                stdout_file = parts[i + 1]
            break

    if redirect_idx is not None:
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

    # external command with redirection
    try:
        stdout_handle = open(stdout_file, "w") if stdout_file else None
        stderr_handle = open(stderr_file, "w") if stderr_file else None

        subprocess.run(
            parts,
            stdout=stdout_handle,
            stderr=stderr_handle
        )

        if stdout_handle:
            stdout_handle.close()
        if stderr_handle:
            stderr_handle.close()

    except FileNotFoundError:
        sys.stdout.write(f"{command}: command not found\n")
        sys.stdout.flush()
