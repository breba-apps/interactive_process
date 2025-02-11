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
        self.process = InteractiveProcess(env={"PS1": "term123$ ", "TERM": "dumb"})
        self.process.read_to_prompt()  # discard the returned value

        return self.process

    def test_read_nonblocking(self):
        self.process.send_command("echo Hello")
        assert self.process.buffer == ""

        time.sleep(0.1)  # wait for terminal to process command
        output = self.process.read_nonblocking(2)

        assert output == 'echo Hello\nHello\nterm123$ '

    def test_read_to_prompt(self):
        self.process.send_command("echo Hello")

        output = self.process.read_to_prompt()

        assert output == "echo Hello\nHello\nterm123$ "

    def test_read_to_prompt_exclusive(self):
        self.process.send_command("echo Hello")

        output = self.process.read_to_prompt(False)

        assert output == "echo Hello\nHello\n"

        prompt = self.process.read_nonblocking()
        assert prompt == "term123$ "

    def test_read_nonblocking_sleeping_command(self):
        self.process.send_command("sleep 0.2 && echo Hello")
        time.sleep(0.4)

        output = self.process.read_nonblocking(2)

        assert output == 'sleep 0.2 && echo Hello\nHello\nterm123$ '

    def test_read_to_prompt_sleeping_command(self):
        self.process.send_command("sleep 0.2 && echo Hello")

        output = self.process.read_to_prompt()

        assert output == "sleep 0.2 && echo Hello\nHello\nterm123$ "


    def test_read_nonblocking_sleeping_command_timeout(self):
        self.process.send_command("sleep 1 && echo Hello")
        time.sleep(0.1)

        with pytest.raises(TimeoutError):
            echo = self.process.read_nonblocking(0.1)
            assert echo == "sleep 1 && echo Hello\n"
            self.process.read_nonblocking(0.1)

    def test_read_to_prompt_sleeping_command_timeout(self):
        self.process.send_command("sleep 1 && echo Hello")

        with pytest.raises(TimeoutError):
            self.process.read_to_prompt(0.1)

        echo = self.process.read_nonblocking(0.1)
        assert echo == "sleep 1 && echo Hello\n"

    def test_read_with_process_closed(self):
        self.process.send_command("sleep 1 && echo Hello")
        time.sleep(0.1)
        echo = self.process.read_nonblocking(0.1)
        assert echo == "sleep 1 && echo Hello\n"  # process doesn't terminate until stdin is drained

        self.process.process.terminate(force=True)
        time.sleep(0.1)  # wait for process to terminate, sometimes takes a bit longer

        with pytest.raises(TerminatedProcessError, match="Process is terminated with return code 1"):
            echo = self.process.read_nonblocking(0.1)
            assert echo == ""

    def test_read_with_intput_response(self):
        self.process.send_command('read -p "Please enter your name: " user_name')
        time.sleep(0.1)
        prompt = self.process.read_nonblocking(0.1)
        assert prompt == """read -p "Please enter your name: " user_name\nPlease enter your name: """
        # Check for timeout after we read the prompt, maybe should be own test
        with pytest.raises(TimeoutError):
            self.process.read_nonblocking(0.01)

        self.process.send_command('dog')
        time.sleep(0.1)
        echo = self.process.read_nonblocking(0.1)
        assert echo == "dog\nterm123$ "

        self.process.send_command('echo $user_name')
        time.sleep(0.1)
        output_result = self.process.read_nonblocking(0.1)

        assert output_result == 'echo $user_name\ndog\nterm123$ '

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
        time.sleep(0.1)
        self.process.send_command('echo Completed 4e556f02-38a1-4eec-8e0c-2d8afcd37ae7')
        time.sleep(0.1)
        value = self.process.read_nonblocking(1)
        assert value == ('clear\n'
                         'term123$ echo Completed 4e556f02-38a1-4eec-8e0c-2d8afcd37ae7\n'
                         'Completed 4e556f02-38a1-4eec-8e0c-2d8afcd37ae7\n'
                         'term123$ ')