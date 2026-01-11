import sys
import subprocess
import os
import readline

BUILTINS = ["exit", "type", "echo", "pwd", "cd"]

# ---------- READLINE AUTOCOMPLETE ----------
def completer(text, state):
    buffer = readline.get_line_buffer()

    # If there is a space, we are completing arguments → do nothing
    if " " in buffer:
        return None

    matches = [b for b in BUILTINS if b.startswith(text)]
    if state < len(matches):
        return matches[state] + " "
    return None

readline.set_completer(completer)
readline.parse_and_bind("tab: complete")
# ------------------------------------------


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
    try:
        line = input("$ ")
    except EOFError:
        break

    if not line.strip():
        continue

    parts = parse_command(line)

    stdout_file = None
    stderr_file = None
    stdout_mode = "w"
    stderr_mode = "w"
    redirect_idx = None

    for i, token in enumerate(parts):
        if token in (">", "1>", ">>", "1>>", "2>", "2>>"):
            redirect_idx = i
            target = parts[i + 1]

            if token == "2>":
                stderr_file = target
                stderr_mode = "w"
            elif token == "2>>":
                stderr_file = target
                stderr_mode = "a"
            elif token in (">", "1>"):
                stdout_file = target
                stdout_mode = "w"
            elif token in (">>", "1>>"):
                stdout_file = target
                stdout_mode = "a"
            break

    if redirect_idx is not None:
        parts = parts[:redirect_idx]

    command = parts[0]

    # exit
    if command == "exit":
        sys.exit(0)

    # pwd
    if command == "pwd":
        print(os.getcwd())
        continue

    # cd
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
            print(f"cd: {path}: No such file or directory")
        continue

    # type
    if command == "type":
        if len(parts) < 2:
            continue
        target = parts[1]
        if target in BUILTINS:
            print(f"{target} is a shell builtin")
            continue
        for p in os.environ.get("PATH", "").split(":"):
            full = os.path.join(p, target)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                print(f"{target} is {full}")
                break
        else:
            print(f"{target}: not found")
        continue

    # external commands
    try:
        stdout_handle = open(stdout_file, stdout_mode) if stdout_file else None
        stderr_handle = open(stderr_file, stderr_mode) if stderr_file else None

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
        print(f"{command}: command not found")
