"""PyDumbInit

Simple init system that uses signal proxiying for managining children. Inspired from yelp/dumb-init
"""

import fcntl
import logging
import os
import signal
import subprocess
import sys
import termios

MAXSIG = 31
SIGMAP = dict.fromkeys(range(1, MAXSIG + 1), -1)
IGNORED_SIGMAP = dict.fromkeys(range(MAXSIG), False)

child_pid = -1
use_setsid = 1

logger = logging.getLogger()


def translate_signal(signum: int) -> int:
    if SIGMAP.get(signum, -1) > 0:
        res = SIGMAP[signum]
        logger.info(f"Translating signal {signum} to {res}")
        return res
    else:
        return signum


def forward_signal(signum: int) -> None:
    signum = translate_signal(signum)
    if signum != 0:
        os.kill(-child_pid if use_setsid else child_pid, signum)
        logger.info(f"Forwarded signal {signum} to children.")
    else:
        logger.info(f"Not forwarding signal {signum} to children (ignored).")


def handle_signal(signum: int) -> None:
    logger.info(f"Received signal {signum}")
    if IGNORED_SIGMAP[signum]:
        logger.info(f"Ignoring tty hand-off signal {signum}")
        IGNORED_SIGMAP[signum] = False
    elif signum == signal.SIGCHLD:
        killed_pid, status = os.waitpid(-1, os.WNOHANG)
        while killed_pid > 0:
            if os.WIFEXITED(status):
                exit_status = os.WEXITSTATUS(status)
                logger.info(
                    f"A child with PID {killed_pid} exited with exit status {exit_status}."
                )
            else:
                assert os.WIFSIGNALED(status)
                exit_status = 128 + os.WTERMSIG(status)
                logger.info(
                    f"A child with PID {killed_pid} was terminated by signal {exit_status - 128}."
                )

            if killed_pid == child_pid:
                forward_signal(signal.SIGTERM)
                logger.info(f"Child exited with status {exit_status}. Goodbye.")
                sys.exit(exit_status)

            killed_pid, status = os.waitpid(-1, os.WNOHANG)
    else:
        forward_signal(signum)
        if signum in {signal.SIGTSTP, signal.SIGTTOU, signal.SIGTTIN}:
            logger.info("Suspending self due to TTY signal.")
            os.kill(os.getpid(), signal.SIGSTOP)


def parse_rewrite_signum(arg: str) -> None:
    try:
        signum, replacement = arg.split(":")
        if signum < 1 or signum > MAXSIG or replacement < 0 or replacement > MAXSIG:
            raise ValueError
        SIGMAP[signum] = replacement
    except ValueError:
        logger.error("Incorrect rewrite format")


def set_rewrite_to_sigstop_if_not_defined(signum: int) -> None:
    if SIGMAP[signum] == -1:
        SIGMAP[signum] = signal.SIGSTOP


def dummy(*args):
    pass


def register_signals() -> None:
    for i in range(1, MAXSIG + 1):
        if i in {9, 19}:
            continue
        signal.signal(i, dummy)


def run(program, *args):
    register_signals()
    if fcntl.ioctl(0, termios.TIOCNOTTY) == -1:
        logger.warn("Unable to detach from controlling tty")
    else:
        if os.getsid(0) == os.getpid():
            logger.info(
                "Detached from controlling tty, ignoring the first SIGHUP and SIGCONT we receive"
            )
            IGNORED_SIGMAP[signal.SIGHUP] = 1
            IGNORED_SIGMAP[signal.SIGCONT] = 1
        else:
            logger.info("Detached from controlling tty, but was not session leader.")

    child_pid = os.fork()
    if child_pid < 0:
        logger.error("Unable to fork. Exiting.")
        return 1
    elif child_pid == 0:
        if use_setsid:
            os.setsid()

        os.execvp(program, args)
        return 2
    else:
        logger.info(f"Child spawned with PID {child_pid}.")
        while True:
            signum = signal.sigwait(set(SIGMAP.keys()))
            handle_signal(signum)


def main(args):
    cmd, *args = args
    cmd = cmd.strip("--")
    if cmd == "run":
        sys.exit(run(*args))


def test_translate_signal():
    assert translate_signal(5) == 5
    SIGMAP[14] = 3
    assert translate_signal(14) == 3
    assert translate_signal(-1) == -1


def test_rewrite_parsing():
    parse_rewrite_signum("5:6")
    assert SIGMAP[5] == 6


def test_forward_signal() -> None:
    print("NO, It works well")


if __name__ == "__main__":
    main(sys.argv[1:])
