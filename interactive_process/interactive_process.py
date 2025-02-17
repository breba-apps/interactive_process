import os
import secrets
import shlex
import string
import time

from ptyprocess import PtyProcessUnicode
import platform
from select import select

class TerminatedProcessError(Exception):
    pass

class ReadWriteError(Exception):
    pass


class InteractiveProcess:
    def __init__(self, env={"PS1": "", "TERM": "dumb"}, shell_prompt = "", echo=False):
        if platform.system() == 'Windows':
            shell = 'cmd.exe'
        else:
            shell = '/bin/bash'
        self.shell_prompt = shell_prompt
        self.buffer = ""
        self.process = PtyProcessUnicode.spawn([shell, '--noprofile', '--norc'], env=env, echo=echo)

    @classmethod
    def with_random_prompt(cls) -> "InteractiveProcess":
        alphabet = string.ascii_letters + string.digits
        random_string = ''.join(secrets.choice(alphabet) for i in range(8))
        prompt = f"user-{random_string}$"

        return cls(shell_prompt=prompt)

    def flush_output(self):
        self.process.write("echo flushed" + os.linesep)
        return self.read_to_text("flushed" + os.linesep)

    def send_command(self, command, end_marker=None):
        try:
            escaped_command = shlex.quote(command)
            echo_text = f"echo {self.shell_prompt} {escaped_command}"
            self.process.write(echo_text + os.linesep)

            if end_marker:
                shell_command = f"{command} && echo {end_marker} || echo {end_marker}"
                self.process.write(f"{shell_command}" + os.linesep)
            else:
                self.process.write(f"{command}" + os.linesep)

        except OSError as e:
            raise ReadWriteError(f"Failed to write to stdin due to OSError") from e

    def send_input(self, input_text: str):
        try:
            input_text = f"{input_text}" + os.linesep
            self.buffer += input_text  # keep input in the buffer for the next read to pick it up
            self.process.write(f"{input_text}" + os.linesep)
        except OSError as e:
            raise ReadWriteError(f"Failed to write to stdin due to OSError") from e

    # TODO: need more tests for this
    def read_to_text(self, text: str, inclusive = True, timeout=0.5):
        start_time = time.monotonic()
        output = ""
        while True:
            try:
                output += self.read_nonblocking(0.01)
                index = output.find(text)
                if index != -1:
                    if inclusive:
                        index = index + len(text)
                    self.buffer = output[index:]
                    return output[:index]
            except TimeoutError as e:
                if time.monotonic() - start_time > timeout:
                    self.buffer = output  # Just save the buffer, so that you can get it by calling read_nonblocking
                    raise e
                continue

    def read_nonblocking(self, timeout=0.1):
        """
        Reads from stdout and std_err. Timeout is used to wait for data. But as soon as data is read,
        the function returns

        :param timeout: timeout in seconds
        :return: string output from the process
        :raise TimeoutError: if no data is read before timeout
        """
        if not self.process.isalive():
            raise TerminatedProcessError(f"Process is terminated with return code {self.process.status}")

        output = ""
        if self.buffer:
            output = self.buffer
            self.buffer = ""
            timeout = 0  # since we already have some output, just collect whatever else is already waiting

        readables, _, _ = select([self.process.fd], [], [], timeout)
        if readables:
            try:
                output += self.process.read().replace("\r\n", "\n")
            except EOFError as e:
                return ""
            except OSError as e:
                raise ReadWriteError(f"Failed to read due to OSError") from e

        if output:
            return output

        raise TimeoutError(f"No data read before reaching timout of {timeout}s")

    def close(self):
        if self.process.isalive():
            self.process.terminate(force=True)

def main():
    process = InteractiveProcess()

    process.send_command("clear")
    process.send_command("echo flush")
    while True:
        try:
            flushed = process.read_nonblocking(0.001)  # clear buffer
        except TimeoutError:
            continue
        else:
            if "flush" in flushed:
                print(flushed.encode())
                break

if __name__ == "__main__":
    main()