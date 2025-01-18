# Interactive Process &middot; [![PyPI version](https://img.shields.io/pypi/v/interactive-process.svg)](https://pypi.org/project/interactive-process/)

A Python package that provides a simple interface to manage interactive shells using a pseudo-terminal. It wraps around [PtyProcessUnicode][ptyprocess-docs] to let you send commands, read outputs, handle timeouts, and gracefully terminate processes.

- **License:** [MIT](#license)
- **Author:** Yason Khaburzaniya

## Description

The `interactive-process` package allows you to spawn and interact with a shell (`/bin/bash` on Unix-like systems or `cmd.exe` on Windows) in a controlled pseudo-terminal environment. This is useful when you need to automate or script tasks that depend on interactive command-line behavior, such as sending commands and reading their outputs in real time.

Key features include:
1. **Cross-Platform Shell Access** – Automatically chooses the correct shell based on the operating system. (Nonblocking reads do not work due to select not supporting file descriptors on windows)
2. **Customizable Environment** – Control environment variables and echo behavior.
3. **Non-Blocking Reads** – Read output with a configurable timeout; raises a `TimeoutError` if no data is received in time.
4. **Exception Handling** – Raises specialized exceptions for terminated processes or I/O issues.
5. **Easy Cleanup** – Gracefully terminate processes with a single method call.

## Installation

This package is published on PyPI under the name `interactive-process`. To install:

```bash
pip install interactive-process
```

You will also need [`ptyprocess`][ptyprocess-pypi], which will be automatically installed if it’s not already present in your environment.

## Usage

Below is an example demonstrating how to create an interactive process, send commands, read outputs, and handle potential errors or timeouts.

```python
from interactive_process import InteractiveProcess, TerminatedProcessError, ReadWriteError

# Create an InteractiveProcess instance
proc = InteractiveProcess()

try:
    # Send a simple echo command
    proc.send_command("echo Hello, Interactive Shell!")

    # Attempt to read the response with a 0.1s timeout
    output = proc.read_nonblocking(timeout=0.1)
    print("Output received:\n", output)

except TerminatedProcessError as e:
    print("Process terminated unexpectedly:", e)
except ReadWriteError as e:
    print("Read/Write error:", e)
except TimeoutError as e:
    print("No data received within timeout:", e)
finally:
    # Ensure the process is terminated properly
    proc.close()
```

### Custom Environment Example

```python
custom_env = {
    "PS1": "",             # Sets a blank prompt
    "TERM": "xterm-256color",
    "MY_VAR": "CustomValue"
}

proc = InteractiveProcess(env=custom_env, echo=True)
try:
    proc.send_command("echo $MY_VAR")
    output = proc.read_nonblocking(timeout=0.5)
    print("Custom Environment Output:", output)
except TimeoutError:
    print("No output received within 0.5 seconds.")
finally:
    proc.close()
```

## API Reference

### InteractiveProcess

**Constructor**
```python
InteractiveProcess(env={"PS1": "", "TERM": "xterm"}, echo=False)
```
- **env** (dict): Environment variables for the subprocess. Default is `{"PS1": "", "TERM": "xterm"}`.
- **echo** (bool): Whether to echo commands in the console.

**send_command(command)**
- Sends a command string to the subprocess.

**read_nonblocking(timeout=0.1)**
- Reads output from the subprocess with the specified `timeout`.
- If no data is read within `timeout` seconds, a `TimeoutError` is raised.

**close()**
- Terminates the subprocess if it is still alive.

### Exceptions

- **TerminatedProcessError**
  Raised when the subprocess has terminated unexpectedly.

- **ReadWriteError**
  Raised when an error occurs during reading from or writing to the subprocess.

## Contributing

1. **Fork** this repository.
2. Create a new **feature branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. **Commit your changes**:
   ```bash
   git commit -am "Add new feature"
   ```
4. **Push to the branch**:
   ```bash
   git push origin feature/my-new-feature
   ```
5. Open a **Pull Request** on GitHub and provide a clear explanation of your changes.

## License

[MIT LICENSE](LICENSE)





[ptyprocess-docs]: https://pexpect.readthedocs.io/en/stable/api/pty_process.html
[ptyprocess-pypi]: https://pypi.org/project/ptyprocess/