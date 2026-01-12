import sys
import shutil
import subprocess
import os
import shlex
import re
import readline
import glob

def exit_handler(args):
    return True

def pwd_handler(args):
    print(os.getcwd())
    return False

def cd_handler(args):
    if not args:
        return False
    target = args[0]
    path = os.path.expanduser(target)
    try:
        os.chdir(path)
    except OSError as e:
        print(f"cd: {target}: {e.strerror}")
    return False

def echo_handler(args):
    print(" ".join(args))
    return False

def type_handler(args):
    if not args:
        return False
    target = args[0]
    if target in BUILTINS:
        print(f"{target} is a shell builtin")
    else:
        path = shutil.which(target)
        if path:
            print(f"{target} is {path}")
        else:
            print(f"{target}: not found")
    return False

BUILTINS = {
    "exit": exit_handler,
    "pwd": pwd_handler,
    "cd": cd_handler,
    "echo": echo_handler,
    "type": type_handler,
}

def parse_redirection(command_parts):
    """Parse redirection operators and return command parts and output files if any."""
    stdout_file = None
    stderr_file = None
    stdout_append = False
    stderr_append = False
    i = 0
    
    while i < len(command_parts):
        if command_parts[i] in [">", "1>"]:
            if i + 1 < len(command_parts):
                stdout_file = command_parts[i + 1]
                stdout_append = False
                command_parts = command_parts[:i] + command_parts[i+2:]
                continue
        elif command_parts[i] in [">>", "1>>"]:
            if i + 1 < len(command_parts):
                stdout_file = command_parts[i + 1]
                stdout_append = True
                command_parts = command_parts[:i] + command_parts[i+2:]
                continue
        elif command_parts[i] == "2>":
            if i + 1 < len(command_parts):
                stderr_file = command_parts[i + 1]
                stderr_append = False
                command_parts = command_parts[:i] + command_parts[i+2:]
                continue
        elif command_parts[i] == "2>>":
            if i + 1 < len(command_parts):
                stderr_file = command_parts[i + 1]
                stderr_append = True
                command_parts = command_parts[:i] + command_parts[i+2:]
                continue
        i += 1
        
    return command_parts, stdout_file, stderr_file, stdout_append, stderr_append

def split_pipeline(parts):
    """Split command parts by pipe operator."""
    commands = []
    current = []
    
    for part in parts:
        if part == "|":
            if current:
                commands.append(current)
                current = []
        else:
            current.append(part)
    
    if current:
        commands.append(current)
    
    return commands

def execute_pipeline(commands):
    """Execute a pipeline of commands."""
    if len(commands) == 1:
        # Single command, no pipeline
        return execute_single_command(commands[0])
    
    # Create pipes for communication between processes
    processes = []
    prev_pipe_read = None
    
    for i, cmd_parts in enumerate(commands):
        is_last = (i == len(commands) - 1)
        
        # Parse redirection for this command
        cmd_parts, stdout_file, stderr_file, stdout_append, stderr_append = parse_redirection(cmd_parts)
        
        if not cmd_parts:
            continue
        
        cmd, *args = cmd_parts
        
        # Create pipe for this command's output (unless it's the last command)
        if not is_last:
            pipe_read, pipe_write = os.pipe()
        else:
            pipe_read, pipe_write = None, None
        
        # Determine stdin
        if prev_pipe_read is not None:
            stdin = prev_pipe_read
        else:
            stdin = None
        
        # Determine stdout
        if is_last:
            if stdout_file:
                mode = 'a' if stdout_append else 'w'
                stdout = open(stdout_file, mode)
            else:
                stdout = None
        else:
            stdout = pipe_write
        
        # Determine stderr
        if stderr_file:
            mode = 'a' if stderr_append else 'w'
            stderr = open(stderr_file, mode)
        else:
            stderr = None
        
        # Start the process
        try:
            proc = subprocess.Popen(
                [cmd] + args,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr
            )
            processes.append(proc)
        except FileNotFoundError:
            print(f"{cmd}: command not found", file=sys.stderr)
            # Clean up any open file descriptors
            if prev_pipe_read is not None:
                os.close(prev_pipe_read)
            if pipe_write is not None:
                os.close(pipe_write)
            if pipe_read is not None:
                os.close(pipe_read)
            return False
        
        # Close file descriptors in parent process
        if prev_pipe_read is not None:
            os.close(prev_pipe_read)
        
        if not is_last:
            os.close(pipe_write)
            prev_pipe_read = pipe_read
        
        # Close file handles if we opened them
        if stdout and stdout_file:
            stdout.close()
        if stderr and stderr_file:
            stderr.close()
    
    # Wait for all processes to complete
    for proc in processes:
        proc.wait()
    
    return False

def execute_single_command(parts):
    """Execute a single command (no pipeline)."""
    parts, stdout_file, stderr_file, stdout_append, stderr_append = parse_redirection(parts)
    
    if not parts:
        return False
    
    cmd, *args = parts
    
    # Check if it's a builtin
    handler = BUILTINS.get(cmd)
    if handler:
        # Setup file redirection for builtins
        stdout_backup = None
        stderr_backup = None
        stdout_fd = None
        stderr_fd = None
        
        try:
            if stdout_file:
                mode = 'a' if stdout_append else 'w'
                stdout_fd = open(stdout_file, mode)
                stdout_backup = os.dup(sys.stdout.fileno())
                os.dup2(stdout_fd.fileno(), sys.stdout.fileno())
            
            if stderr_file:
                mode = 'a' if stderr_append else 'w'
                stderr_fd = open(stderr_file, mode)
                stderr_backup = os.dup(sys.stderr.fileno())
                os.dup2(stderr_fd.fileno(), sys.stderr.fileno())
            
            exit_shell = handler(args)
            return exit_shell
        finally:
            if stdout_backup is not None:
                os.dup2(stdout_backup, sys.stdout.fileno())
                os.close(stdout_backup)
                if stdout_fd:
                    stdout_fd.close()
            
            if stderr_backup is not None:
                os.dup2(stderr_backup, sys.stderr.fileno())
                os.close(stderr_backup)
                if stderr_fd:
                    stderr_fd.close()
    else:
        # External command
        stdout_handle = None
        stderr_handle = None
        
        if stdout_file:
            mode = 'a' if stdout_append else 'w'
            stdout_handle = open(stdout_file, mode)
        
        if stderr_file:
            mode = 'a' if stderr_append else 'w'
            stderr_handle = open(stderr_file, mode)
        
        try:
            subprocess.run(
                [cmd] + args,
                stdout=stdout_handle,
                stderr=stderr_handle
            )
        except FileNotFoundError:
            print(f"{cmd}: command not found", file=sys.stderr)
        finally:
            if stdout_handle:
                stdout_handle.close()
            if stderr_handle:
                stderr_handle.close()
        
        return False

# Variables to track completion state
last_tab_text = ""
last_tab_matches = []
last_tab_count = 0

def get_executable_matches(text):
    """Find all executables in PATH that match the given prefix."""
    matches = []
    
    # First, check builtins
    for cmd in BUILTINS.keys():
        if cmd.startswith(text):
            matches.append(cmd)
    
    # Then check executables in PATH
    path_dirs = os.environ.get("PATH", "").split(":")
    for dir_path in path_dirs:
        if not dir_path:
            continue
        
        try:
            for file_path in glob.glob(os.path.join(dir_path, "*")):
                if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                    cmd_name = os.path.basename(file_path)
                    if cmd_name.startswith(text) and cmd_name not in matches:
                        matches.append(cmd_name)
        except Exception:
            pass
    
    return sorted(matches)

def get_longest_common_prefix(strings):
    """Get the longest common prefix of a list of strings."""
    if not strings:
        return ""
    if len(strings) == 1:
        return strings[0]
        
    prefix = strings[0]
    for string in strings[1:]:
        length = 0
        for i in range(min(len(prefix), len(string))):
            if prefix[i] != string[i]:
                break
            length = i + 1
        
        prefix = prefix[:length]
        if not prefix:
            break
            
    return prefix

def complete(text, state):
    """Custom tab completion function for readline."""
    global last_tab_text, last_tab_matches, last_tab_count
    
    line = readline.get_line_buffer()
    
    if not line.strip() or " " not in line.lstrip():
        if text != last_tab_text:
            last_tab_text = text
            last_tab_matches = get_executable_matches(text)
            last_tab_count = 0
        
        if not last_tab_matches:
            return None
            
        if len(last_tab_matches) == 1:
            if state == 0:
                return last_tab_matches[0] + " "
            return None
            
        if state == 0:
            longest_prefix = get_longest_common_prefix(last_tab_matches)
            
            if len(longest_prefix) > len(text):
                return longest_prefix
            
            if last_tab_count == 0:
                last_tab_count += 1
                sys.stdout.write('\a')
                sys.stdout.flush()
                return text
            else:
                print()
                print("  ".join(last_tab_matches))
                sys.stdout.write(f"$ {text}")
                sys.stdout.flush()
                last_tab_count = 0
                return text
        
        return None
    
    if state == 0:
        return text
    return None

def setup_readline():
    """Set up readline with custom completion."""
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete)
    readline.set_completer_delims(" \t\n")

def main():
    setup_readline()
    
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        try:
            command = input()
        except EOFError:
            break
        
        try:
            parts = shlex.split(command)
        except ValueError as e:
            print(f"Error parsing command: {e}")
            continue
        
        if not parts:
            continue
        
        # Check for pipeline
        commands = split_pipeline(parts)
        
        if len(commands) > 1:
            # Execute pipeline
            exit_shell = execute_pipeline(commands)
        else:
            # Execute single command
            exit_shell = execute_single_command(parts)
        
        if exit_shell:
            break

if __name__ == "__main__":
    main()