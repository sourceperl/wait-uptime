"""
Wait for system uptime to reach a specified threshold.

This script is useful for delaying service startup until the system has been
running for a minimum amount of time, which can help avoid race conditions
during boot.
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# some const
__version__ = '0.0.1'


class UptimeError(Exception):
    """Raised when uptime cannot be determined."""
    pass


def get_uptime() -> float:
    """
    Get the current system uptime in seconds.

    Returns:
        System uptime in seconds

    Raises:
        UptimeError: If uptime cannot be read or parsed
    """
    uptime_file = Path('/proc/uptime')

    if not uptime_file.exists():
        raise UptimeError(f'{uptime_file} not found. this script requires a linux/unix system')

    try:
        with uptime_file.open('r') as f:
            content = f.readline().strip()
            uptime_str = content.split()[0]
            uptime = float(uptime_str)

        if uptime < 0:
            raise UptimeError(f'invalid uptime value: {uptime}')

        return uptime

    except (IndexError, ValueError) as e:
        raise UptimeError(f'failed to parse uptime from {uptime_file}: {e}') from e
    except IOError as e:
        raise UptimeError(f'failed to read {uptime_file}: {e}') from e


def parse_time_string(time_str: str) -> float:
    """
    Parse time string with units into seconds.

    Supports formats like: 30, 30s, 5m, 2h, 1.5h, 90s, etc.

    Args:
        time_str: Time string to parse

    Returns:
        Time in seconds

    Raises:
        ValueError: If format is invalid
    """
    time_str = time_str.strip().lower()

    # Map of unit suffixes to multipliers
    units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
    }

    # Check if it has a unit suffix
    for unit, multiplier in units.items():
        if time_str.endswith(unit):
            try:
                value = float(time_str[:-len(unit)])
                return value * multiplier
            except ValueError:
                raise ValueError(f'invalid time value: {time_str}')

    # No unit, assume seconds
    try:
        return float(time_str)
    except ValueError:
        raise ValueError(f'invalid time format: {time_str} (use format like: 30, 30s, 5m, 2h, 1.5h)')


def format_duration(seconds: float) -> str:
    """
    Format seconds as human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2h 30m 15s")
    """
    if seconds < 60:
        return f'{seconds:.1f}s'

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f'{hours}h')
    if minutes > 0:
        parts.append(f'{minutes}m')
    if secs > 0 or not parts:
        parts.append(f'{secs}s')

    return ' '.join(parts)


def wait_uptime(min_seconds: float, poll_interval: float = 0.5, verbose: bool = False,
                timeout: Optional[float] = None) -> bool:
    """
    Wait until the system's uptime exceeds a specified minimum duration.

    Args:
        min_seconds: Minimum uptime duration in seconds
        poll_interval: How often to check uptime (in seconds)
        verbose: Enable verbose logging
        timeout: Maximum time to wait (None for unlimited)

    Returns:
        True if target uptime reached, False if timeout occurred

    Raises:
        UptimeError: If uptime cannot be determined
        ValueError: If min_seconds or poll_interval are invalid
    """
    if min_seconds < 0:
        raise ValueError(f'min_seconds must be non-negative, got {min_seconds}')

    if poll_interval <= 0:
        raise ValueError(f'poll_interval must be positive, got {poll_interval}')

    if timeout is not None and timeout < 0:
        raise ValueError(f'timeout must be non-negative, got {timeout}')

    start_time = time.time()
    initial_uptime = get_uptime()

    if initial_uptime >= min_seconds:
        logger.info(f'uptime already at {format_duration(initial_uptime)}, target was {format_duration(min_seconds)}')
        return True

    remaining = min_seconds - initial_uptime
    logger.info(
        f'waiting for uptime to reach {format_duration(min_seconds)} '
        f'(current: {format_duration(initial_uptime)}, remaining: {format_duration(remaining)})'
    )

    last_log_time = start_time
    # log progress every 10s
    log_interval = 10.0

    try:
        while True:
            current_uptime = get_uptime()

            # check if target reached
            if current_uptime >= min_seconds:
                elapsed = time.time() - start_time
                logger.info(
                    f'target uptime reached: {format_duration(current_uptime)} '
                    f'(waited {format_duration(elapsed)})'
                )
                return True

            # check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(
                        f'timeout reached after {format_duration(elapsed)}, '
                        f'current uptime: {format_duration(current_uptime)}, '
                        f'target: {format_duration(min_seconds)}'
                    )
                    return False

            # verbose progress logging
            if verbose:
                current_time = time.time()
                if current_time - last_log_time >= log_interval:
                    remaining = min_seconds - current_uptime
                    logger.info(
                        f'still waiting... current: {format_duration(current_uptime)}, '
                        f'remaining: {format_duration(remaining)}'
                    )
                    last_log_time = current_time

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        logger.info('interrupted by user')
        raise


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """
    Configure logging.

    Args:
        verbose: Enable debug logging
        quiet: Suppress all output except errors
    """
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(message)s', level=level)


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, 1 for error, 2 for timeout)
    """
    parser = argparse.ArgumentParser(
        description='wait for system uptime to reach a specified threshold',
        epilog='examples:\n'
               '  %(prog)s 30       # wait for 30 seconds uptime\n'
               '  %(prog)s 5m       # wait for 5 minutes uptime\n'
               '  %(prog)s 2h       # wait for 2 hours uptime\n'
               '  %(prog)s 90s -v   # wait for 90 seconds with verbose output\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('delay', type=str, help='minimum uptime to wait for (e.g., 30, 30s, 5m, 2h)')
    parser.add_argument('-i', '--interval', type=float, default=0.5, metavar='SECONDS',
                        help='polling interval in seconds (default: 0.5)',)
    parser.add_argument('-t', '--timeout', type=str, default=None, metavar='TIME',
                        help='maximum time to wait before giving up (e.g., 10m, 1h)',)
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='enable verbose output with progress updates',)
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='suppress all output except errors',)
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    args = parser.parse_args()

    # setup logging
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    try:
        # parse delay
        try:
            min_seconds = parse_time_string(args.delay)
        except ValueError as e:
            logger.error(f'invalid delay argument: {e}')
            return 1

        # parse timeout if provided
        timeout = None
        if args.timeout:
            try:
                timeout = parse_time_string(args.timeout)
            except ValueError as e:
                logger.error(f'invalid timeout argument: {e}')
                return 1

        # Wait for uptime
        success = wait_uptime(min_seconds=min_seconds, poll_interval=args.interval, verbose=args.verbose,
                              timeout=timeout)

        return 0 if success else 2

    except UptimeError as e:
        logger.error(f'uptime error: {e}')
        return 1
    except KeyboardInterrupt:
        logger.info('operation cancelled by user')
        # standard exit code for SIGINT
        return 130
    except Exception as e:
        logger.error(f'unexpected error: {type(e).__name__} - {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
