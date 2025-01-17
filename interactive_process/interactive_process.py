import subprocess
from select import select

class TerminatedProcessError(Exception):
    pass

class ReadWriteError(Exception):
    pass

def read_fd(readable_fds, fd_to_read):
    try:
        if fd_to_read in readable_fds:
            data = fd_to_read.peek()
            fd_to_read.read(len(data))  # move the cursor before decoding output
            return data.decode()
        return None  # just being explicit. None is returned if the fd is not readable
    except OSError as e:
        raise ReadWriteError(f"Failed to read from {fd_to_read.name} due to OSError") from e

class InteractiveProcess:
    def __init__(self):
        self.process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def send_command(self, command):
        try:
            command = f"{command}\n"
            self.process.stdin.write(command.encode())
            self.process.stdin.flush()
        except OSError as e:
            raise ReadWriteError(f"Failed to write to stdin due to OSError") from e

    def read_nonblocking(self, timeout=0.1):
        """
        Reads from stdout and std_err. Timeout is used to wait for data. But as soon as data is read,
        the function returns

        :param timeout: timeout in seconds
        :return: string output from the process stdout
        :raise TimeoutError: if no data is read before timeout
        """
        if self.process.poll() is not None:
            raise TerminatedProcessError(f"Process is terminated with return code {self.process.returncode}")
        readables, _, _ = select([self.process.stdout, self.process.stderr], [], [], timeout)

        if readables:
            std_out = read_fd(readables, self.process.stdout)
            std_err = read_fd(readables, self.process.stderr)
            return std_out, std_err

        raise TimeoutError(f"No data read before reaching timout of {timeout}s")

    def close(self):
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.stderr.close()
        self.process.wait(1)
        self.process.terminate()