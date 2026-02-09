# wait-uptime
A lightweight utility to delay execution until a specific system uptime threshold is met.

## Installation

### From GitHub

```bash
pipx install git+https://github.com/sourceperl/wait-uptime.git
```

### From source

```bash
git clone https://github.com/sourceperl/wait-uptime.git
cd wait-uptime
pip install .
```


## Usage

### Basic Usage

```bash
# Wait for 30 seconds of uptime
wait-uptime 30

# Wait for 5 minutes
wait-uptime 5m

# Wait for 2 hours
wait-uptime 2h

# Wait for 1.5 hours
wait-uptime 1.5h
```

### Advanced Usage

```bash
# Verbose mode with progress updates
wait-uptime 10m --verbose

# Quiet mode (only errors)
wait-uptime 5m --quiet

# With timeout (give up after 10 minutes)
wait-uptime 1h --timeout 10m

# Custom polling interval (check every second)
wait-uptime 30s --interval 1.0
```

### Time Format

The script supports these time units:
- `s` - seconds
- `m` - minutes  
- `h` - hours
- `d` - days

Examples: `30`, `30s`, `5m`, `2h`, `1.5h`, `90s`

### Exit Codes

- `0` - Success (target uptime reached)
- `1` - Error (invalid arguments, uptime read failure)
- `2` - Timeout (waited too long)
- `130` - User interrupted (Ctrl+C)

## Platform Support

This script requires a Linux/Unix-like operating system that exposes uptime information via `/proc/uptime`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.