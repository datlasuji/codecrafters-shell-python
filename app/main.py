import sys
import shutil
import subprocess
import os
import shlex
import re
import readline
import glob

# History storage
command_history = []
last_written_index = 0  # Track how many commands have been written to file

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

def history_handler(args):
    """Display command history."""
    global last_written_index
    
    # Check for -r flag
    if args and args[0] == "-r":
        # history -r <path> - read history from file
        if len(args) < 2:
            print("history: -r: option requires an argument", file=sys.stderr)
            return False
        
        history_file = args[1]
        try:
            with open(history_file, 'r') as f:
                for line in f:
                    line = line.rstrip('\n')
                    # Skip empty lines
                    if line:
                        command_history.append(line)
            # Update last_written_index to reflect that these commands are already in the file
            last_written_index = len(command_history)
        except FileNotFoundError:
            print(f"history: {history_file}: No such file or directory", file=sys.stderr)
        except Exception as e:
            print(f"history: {history_file}: {e}", file=sys.stderr)
        
        return False
    
    # Check for -w flag
    if args and args[0] == "-w":
        # history -w <path> - write history to file
        if len(args) < 2:
            print("history: -w: option requires an argument", file=sys.stderr)
            return False
        
        history_file = args[1]
        try:
            with open(history_file, 'w') as f:
                for cmd in command_history:
                    f.write(cmd + '\n')
            # Update last_written_index to track all commands have been written
            last_written_index = len(command_history)
        except Exception as e:
            print(f"history: {history_file}: {e}", file=sys.stderr)
        
        return False
    
    # Check for -a flag
    if args and args[0] == "-a":
        # history -a <path> - append new commands to file
        if len(args) < 2:
            print("history: -a: option requires an argument", file=sys.stderr)
            return False
        
        history_file = args[1]
        try:
            # Append only commands that haven't been written yet
            with open(history_file, 'a') as f:
                for i in range(last_written_index, len(command_history)):
                    f.write(command_history[i] + '\n')
            # Update last_written_index to track what we've written
            last_written_index = len(command_history)
        except Exception as e:
            print(f"history: {history_file}: {e}", file=sys.stderr)
        
        return False
    
    # Regular history display
    if args:
        # history <n> - show last n commands
        try:
            n = int(args[0])
            # Get the last n commands
            start_index = max(0, len(command_history) - n)
            for i in range(start_index, len(command_history)):
                print(f"    {i + 1}  {command_history[i]}")
        except ValueError:
            print(f"history: {args[0]}: numeric argument required", file=sys.stderr)
    else:
        # history - show all commands
        for i, cmd in enumerate(command_history, start=1):
            print(f"    {i}  {cmd}")
    return False

BUILTINS = {
    "exit": exit_handler,
    "pwd": pwd_handler,
    "cd": cd_handler,
    "echo": echo_handler,
    "type": type_handler,
    "history": history_handler,
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

def execute_builtin_in_pipeline(cmd, args, stdin_fd, stdout_fd, stderr_fd):
    """Execute a builtin command with specified stdin/stdout/stderr."""
    # Fork to run builtin in a separate process
    pid = os.fork()
    
    if pid == 0:
        # Child process
        try:
            # Redirect stdin
            if stdin_fd is not None:
                os.dup2(stdin_fd, sys.stdin.fileno())
                os.close(stdin_fd)
            
            # Redirect stdout
            if stdout_fd is not None:
                os.dup2(stdout_fd, sys.stdout.fileno())
                os.close(stdout_fd)
            
            # Redirect stderr
            if stderr_fd is not None:
                os.dup2(stderr_fd, sys.stderr.fileno())
                os.close(stderr_fd)
            
            # Execute the builtin
            handler = BUILTINS[cmd]
            handler(args)
            
            # Exit child process
            os._exit(0)
        except Exception as e:
            print(f"Error executing builtin: {e}", file=sys.stderr)
            os._exit(1)
    else:
        # Parent process - close file descriptors
        if stdin_fd is not None:
            os.close(stdin_fd)
        if stdout_fd is not None:
            os.close(stdout_fd)
        if stderr_fd is not None:
            os.close(stderr_fd)
        
        return pid

def execute_pipeline(commands):
    """Execute a pipeline of commands."""
    if len(commands) == 1:
        # Single command, no pipeline
        return execute_single_command(commands[0])
    
    # Create pipes and processes
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
        stdin_fd = prev_pipe_read
        
        # Determine stdout
        if is_last:
            if stdout_file:
                mode = 'a' if stdout_append else 'w'
                stdout_fd = os.open(stdout_file, os.O_WRONLY | os.O_CREAT | (os.O_APPEND if stdout_append else os.O_TRUNC), 0o644)
            else:
                stdout_fd = None
        else:
            stdout_fd = pipe_write
        
        # Determine stderr
        if stderr_file:
            mode = 'a' if stderr_append else 'w'
            stderr_fd = os.open(stderr_file, os.O_WRONLY | os.O_CREAT | (os.O_APPEND if stderr_append else os.O_TRUNC), 0o644)
        else:
            stderr_fd = None
        
        # Check if it's a builtin
        if cmd in BUILTINS:
            # Execute builtin in a forked process
            pid = execute_builtin_in_pipeline(cmd, args, stdin_fd, stdout_fd, stderr_fd)
            processes.append(pid)
        else:
            # Execute external command
            pid = os.fork()
            
            if pid == 0:
                # Child process
                try:
                    # Redirect stdin
                    if stdin_fd is not None:
                        os.dup2(stdin_fd, sys.stdin.fileno())
                        os.close(stdin_fd)
                    
                    # Redirect stdout
                    if stdout_fd is not None:
                        os.dup2(stdout_fd, sys.stdout.fileno())
                        os.close(stdout_fd)
                    
                    # Redirect stderr
                    if stderr_fd is not None:
                        os.dup2(stderr_fd, sys.stderr.fileno())
                        os.close(stderr_fd)
                    
                    # Close the read end of current pipe if exists
                    if pipe_read is not None:
                        os.close(pipe_read)
                    
                    # Execute the command
                    os.execvp(cmd, [cmd] + args)
                except FileNotFoundError:
                    print(f"{cmd}: command not found", file=sys.stderr)
                    os._exit(127)
                except Exception as e:
                    print(f"Error: {e}", file=sys.stderr)
                    os._exit(1)
            else:
                # Parent process - close file descriptors
                if stdin_fd is not None:
                    os.close(stdin_fd)
                if stdout_fd is not None:
                    os.close(stdout_fd)
                if stderr_fd is not None:
                    os.close(stderr_fd)
                
                processes.append(pid)
        
        # Update prev_pipe_read for next iteration
        prev_pipe_read = pipe_read
    
    # Wait for all processes to complete
    for pid in processes:
        os.waitpid(pid, 0)
    
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
    """Set up readline with custom completion and history."""
    # Set up tab completion
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete)
    readline.set_completer_delims(" \t\n")

def main():
    setup_readline()
    
    while True:
        try:
            command = input("$ ")
        except EOFError:
            break
        
        # Add command to history (readline handles this automatically)
        if command.strip():
            command_history.append(command)
        
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