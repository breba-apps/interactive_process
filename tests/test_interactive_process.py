import time
from unittest.mock import MagicMock

import pytest

from interactive_process.interactive_process import InteractiveProcess, TerminatedProcessError, ReadWriteError

@pytest.fixture(params=[
        ("ls dog", "No such file or directory\n"),
        ("cd dog", "No such file or directory\n"),
        ("nocommand1", "command not found"),
    ])
def error_commands(request):
    yield request.param

class TestInteractiveProcess:
    @pytest.fixture(autouse=True)
    def process(self):
        self.process = InteractiveProcess()

    def test_stream_nonblocking(self):
        self.process.send_command("echo Hello")

        output = self.process.read_nonblocking()

        assert output[0] == "Hello\n"  # newline is part of echo command

    def test_stream_nonblocking_sleeping_command(self):
        self.process.send_command("sleep 1 && echo Hello")

        output = self.process.read_nonblocking(1.5)

        assert output[0] == "Hello\n"

    def test_stream_nonblocking_sleeping_command_timeout(self):
        self.process.send_command("sleep 1 && echo Hello")

        with pytest.raises(TimeoutError):
            self.process.read_nonblocking(0.1)

    def test_read_with_process_closed(self):
        self.process.send_command("sleep 1 && echo Hello")
        self.process.process.kill()
        # wait for process to exit
        while self.process.process.poll() is None:
            time.sleep(0.1)

        with pytest.raises(TerminatedProcessError, match="Process is terminated with return code -9"):
            self.process.read_nonblocking(0.1)

    def test_read_with_intput_response(self):
        self.process.send_command('read -p "Please enter your name: " user_name')
        self.process.send_command('dog')

        with pytest.raises(TimeoutError):
            self.process.read_nonblocking(0.1)

        self.process.send_command('echo $user_name')
        output_result = self.process.read_nonblocking(0.1)

        assert output_result[0] == 'dog\n'

    def test_read_std_err(self, error_commands):
        command, expect_output =error_commands
        self.process.send_command(command)

        output = self.process.read_nonblocking(0.2)

        assert expect_output in output[1]

    def test_read_nonblocking_write_error(self):
        self.process.process.stdin.write = MagicMock(side_effect=OSError("Mocked OSError"))

        with pytest.raises(ReadWriteError) as exc:
            self.process.send_command("echo Hello")

        exc.match("Failed to write to stdin due to OSError")

    def test_read_nonblocking_read_error(self):
        self.process.process.stdout.read = MagicMock(side_effect=OSError("Mocked OSError"))

        self.process.send_command("echo Hello")
        with pytest.raises(ReadWriteError) as exc:
            self.process.read_nonblocking()

        exc.match("Failed to read from .* due to OSError")