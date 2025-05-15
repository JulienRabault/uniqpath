# uniqpath

Generate unique file or directory paths by appending customizable suffixes.

## Description

`uniqpath` is a lightweight Python utility to generate unique file or directory paths by adding formatted suffixes.  
It helps avoid overwriting existing files by incrementing numeric suffixes or adding randomized strings, UUIDs, or
timestamps.

## Features

- Incremental numeric suffix `{num}` starting at 1
- Timestamp suffix `{timestamp}` (UNIX epoch seconds)
- Random alphanumeric suffix `{rand[:n]}` with customizable length (default 6)
- UUID suffix `{uuid[:n]}` truncated to customizable length (default 32)
- Option to add suffix only if original path exists
- Returns either `Path` or `str` for integration flexibility
- Simple and dependency-free (only standard library)
- Designed for files and directories

## Installation

```bash
pip install uniqpath
````

## Usage

```python
from uniqpath import unique_path

# Basic usage with incremental number suffix
p1 = unique_path("output.txt")  # -> output_1.txt if output.txt exists

# Custom suffix with random string of length 8
p2 = unique_path("log.txt", suffix_format="_{rand:8}")

# Use UUID suffix truncated to 6 characters
p3 = unique_path("data", suffix_format="_{uuid:6}")

# Add suffix only if the path exists, otherwise return original path
p4 = unique_path("report.txt", if_exists_only=True)

# Get result as string instead of Path
p5 = unique_path("file.txt", return_str=True)
```

## Parameters

* **path** (`str` or `Path`): The base file or directory path.
* **suffix\_format** (`str`, default `_{num}`): Suffix pattern with placeholders:

    * `{num}`: incrementing number starting from 1
    * `{timestamp}`: UNIX timestamp in seconds
    * `{rand[:n]}`: random alphanumeric string, length `n` (default 6)
    * `{uuid[:n]}`: UUID4 hex string truncated to `n` chars (default 32)
* **verbose** (`bool`, default `False`): Enable logging of attempts and results.
* **if\_exists\_only** (`bool`, default `True`): Only add suffix if base path exists.
* **return\_str** (`bool`, default `False`): Return a string path instead of a `Path` object.

## Notes

* The function does **not** handle concurrency and is not thread-safe.
* Date/time placeholders use current datetime but do not support full strftime syntax.
* The function works for both files and directories.
* Make sure to handle potential race conditions externally if used in parallel environments.

## License

MIT License

## Author

Julien Rabault — [julienrabault@icloud.com](mailto:julienrabault@icloud.com)