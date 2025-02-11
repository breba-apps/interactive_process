import os
import secrets
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
    @classmethod
    def with_random_prompt(cls):
        alphabet = string.ascii_letters + string.digits
        random_string = ''.join(secrets.choice(alphabet) for i in range(8))

        return cls({"PS1": f"{random_string}$ ", "TERM": "dumb"})


    # For some reason echo=True will sometimes show the command going in and then also show it with the prefixed shell prompt.
    # For example: echo Completed 4e556f02-38a1-4eec-8e0c-2d8afcd37ae7
    #              term123$ echo Completed 4e556f02-38a1-4eec-8e0c-2d8afcd37ae7
    # Only the second line is expected. If I wait long enough, the output is correct, but it appears to be a race condition
    def __init__(self, env={"PS1": "", "TERM": "dumb"}, echo=True):
        if platform.system() == 'Windows':
            shell = 'cmd.exe'
        else:
            shell = '/bin/bash'
        self.shell_prompt = env["PS1"]
        self.buffer = ""
        self.process = PtyProcessUnicode.spawn([shell, '--noprofile', '--norc'], env=env, echo=echo)

    def send_command(self, command):
        try:
            self.process.write(f"{command}" + os.linesep)
        except OSError as e:
            raise ReadWriteError(f"Failed to write to stdin due to OSError") from e

    def read_to_prompt(self, inclusive = True, timeout=0.5):
        if not self.shell_prompt:
            raise Exception("Shell prompt is not set")

        start_time = time.monotonic()
        output = ""
        before = self.buffer
        self.buffer = ""
        while True:
            try:
                output += self.read_nonblocking(0.01)
                index = output.find(self.shell_prompt)
                if index != -1:
                    if inclusive:
                        index = index + len(self.shell_prompt)
                    self.buffer = output[index:]
                    return before + output[:index]
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