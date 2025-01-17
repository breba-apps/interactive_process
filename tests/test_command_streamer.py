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

class TestCommandStreamer:
    @pytest.fixture(autouse=True)
    def streamer(self):
        self.streamer = InteractiveProcess()

    def test_stream_nonblocking(self):
        self.streamer.send_command("echo Hello")

        output = self.streamer.read_nonblocking()

        assert output[0] == "Hello\n"  # newline is part of echo command

    def test_stream_nonblocking_sleeping_command(self):
        self.streamer.send_command("sleep 1 && echo Hello")

        output = self.streamer.read_nonblocking(1.5)

        assert output[0] == "Hello\n"

    def test_stream_nonblocking_sleeping_command_timeout(self):
        self.streamer.send_command("sleep 1 && echo Hello")

        with pytest.raises(TimeoutError):
            self.streamer.read_nonblocking(0.1)

    def test_read_with_process_closed(self):
        self.streamer.send_command("sleep 1 && echo Hello")
        self.streamer.process.kill()
        # wait for process to exit
        while self.streamer.process.poll() is None:
            time.sleep(0.1)

        with pytest.raises(TerminatedProcessError, match="Process is terminated with return code -9"):
            self.streamer.read_nonblocking(0.1)

    def test_read_with_intput_response(self):
        self.streamer.send_command('read -p "Please enter your name: " user_name')
        self.streamer.send_command('dog')

        with pytest.raises(TimeoutError):
            self.streamer.read_nonblocking(0.1)

        self.streamer.send_command('echo $user_name')
        output_result = self.streamer.read_nonblocking(0.1)

        assert output_result[0] == 'dog\n'

    def test_read_std_err(self, error_commands):
        command, expect_output =error_commands
        self.streamer.send_command(command)

        output = self.streamer.read_nonblocking(0.2)

        assert expect_output in output[1]

    def test_read_nonblocking_write_error(self):
        self.streamer.process.stdin.write = MagicMock(side_effect=OSError("Mocked OSError"))

        with pytest.raises(ReadWriteError) as exc:
            self.streamer.send_command("echo Hello")

        exc.match("Failed to write to stdin due to OSError")

    def test_read_nonblocking_read_error(self):
        self.streamer.process.stdout.read = MagicMock(side_effect=OSError("Mocked OSError"))

        self.streamer.send_command("echo Hello")
        with pytest.raises(ReadWriteError) as exc:
            self.streamer.read_nonblocking()

        exc.match("Failed to read from .* due to OSError")