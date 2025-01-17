from ptyprocess import PtyProcessUnicode
import platform
from select import select

class TerminatedProcessError(Exception):
    pass

class ReadWriteError(Exception):
    pass


class InteractiveProcess:
    def __init__(self, env={"PS1": ""}, echo=False):
        if platform.system() == 'Windows':
            shell = 'cmd.exe'
        else:
            shell = '/bin/bash'
        self.process = PtyProcessUnicode.spawn([shell], env=env, echo=echo)

    def send_command(self, command):
        try:
            self.process.write(f"{command}\n")
        except OSError as e:
            raise ReadWriteError(f"Failed to write to stdin due to OSError") from e

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
        readables, _, _ = select([self.process.fd], [], [], timeout)

        if readables:
            try:
                return self.process.read()
            except EOFError as e:
                return ""
            except OSError as e:
                raise ReadWriteError(f"Failed to read due to OSError") from e

        raise TimeoutError(f"No data read before reaching timout of {timeout}s")

    def close(self):
        if self.process.isalive():
            self.process.terminate(force=True)