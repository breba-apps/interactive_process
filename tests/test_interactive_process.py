import time
from unittest.mock import MagicMock

import pytest

from interactive_process.interactive_process import InteractiveProcess, TerminatedProcessError, ReadWriteError

@pytest.fixture(params=[
        ("ls dog", "No such file or directory"),
        ("cd dog", "No such file or directory"),
        ("nocommand1", "command not found"),
    ])
def error_commands(request):
    yield request.param

class TestInteractiveProcess:
    @pytest.fixture(autouse=True)
    def process(self):
        self.process = InteractiveProcess(shell_prompt="testing$")
        flushed = self.process.flush_output()
        print(f"\nFlushed before reading input:\n{flushed}")
        return self.process

    def test_read_nonblocking(self):
        self.process.send_command("echo Hello")
        time.sleep(0.2)  # wait for output to show up in the terminal
        output = self.process.read_nonblocking(2)

        assert output.strip() == "testing$ echo Hello\nHello"  # newline is part of echo command

    def test_read_nonblocking_sleeping_command(self):
        self.process.send_command("sleep 0.2 && echo Hello")
        time.sleep(0.3)

        output = self.process.read_nonblocking(2)

        assert output.strip() == "testing$ sleep 0.2 && echo Hello\nHello"

    def test_read_nonblocking_sleeping_command_timeout(self):
        self.process.send_command("sleep 1 && echo Hello")
        time.sleep(0.2)
        echo = self.process.read_nonblocking(0.1)
        assert echo.strip() == "testing$ sleep 1 && echo Hello"
        time.sleep(0.3)

        with pytest.raises(TimeoutError):
            self.process.read_nonblocking(0.1)

    def test_read_with_process_closed(self):
        self.process.send_command("sleep 1 && echo Hello")
        self.process.process.terminate(force=True)

        with pytest.raises(TerminatedProcessError, match="Process is terminated with return code 1"):
            self.process.read_nonblocking(0.1)

    def test_read_with_intput_response(self):
        self.process.send_command('read -p "Please enter your name: " user_name')
        time.sleep(0.1)
        prompt = self.process.read_nonblocking(0.1)
        assert prompt.strip() == """testing$ read -p "Please enter your name: " user_name\nPlease enter your name:"""
        # Check for timeout after we read the prompt, maybe should be own test
        with pytest.raises(TimeoutError):
            self.process.read_nonblocking(0.01)
        self.process.send_input('dog')

        self.process.send_command('echo $user_name')
        time.sleep(0.1)
        output_result = self.process.read_nonblocking(0.1)

        assert output_result.strip() == 'dog\ntesting$ echo $user_name\ndog'

    def test_read_std_err(self, error_commands):
        command, expect_output =error_commands
        self.process.send_command(command)
        time.sleep(0.1)

        output = self.process.read_nonblocking(0.2)

        assert expect_output in output.strip()  # in because different OS have slightly different error messages

    def test_read_nonblocking_write_error(self):
        self.process.process.write = MagicMock(side_effect=OSError("Mocked OSError"))

        with pytest.raises(ReadWriteError) as exc:
            self.process.send_command("echo Hello")

        exc.match("Failed to write to stdin due to OSError")

    def test_read_nonblocking_read_error(self):
        self.process.process.read = MagicMock(side_effect=OSError("Mocked OSError"))

        self.process.send_command("echo Hello")
        with pytest.raises(ReadWriteError, match="Failed to read due to OSError") as exc:
            self.process.read_nonblocking()


    def test_read_nonblocking_clear_command(self):
        self.process.send_command('clear')  # with "dumb" terminal clear command FAIL silently
        self.process.send_command('echo Completed 4e556f02-38a1-4eec-8e0c-2d8afcd37ae7')
        time.sleep(0.1)
        value = self.process.read_nonblocking(1)
        assert value.strip() == ('testing$ clear\n'
                                 'testing$ echo Completed 4e556f02-38a1-4eec-8e0c-2d8afcd37ae7\n'
                                 'Completed 4e556f02-38a1-4eec-8e0c-2d8afcd37ae7')