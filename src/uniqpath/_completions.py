"""Shell completion scripts, printed by ``uniqpath --completion SHELL``.

Hand-written rather than generated, so that uniqpath keeps zero runtime
dependencies.
"""

from __future__ import annotations

__all__ = ["SHELLS", "completion_script"]

SHELLS = ("bash", "zsh", "fish")

# Offered as suffix_format suggestions. Keep in sync with the README table.
_FORMATS = (
    "_{num}",
    "_{num:03d}",
    "_{date:%Y-%m-%d}_{num}",
    "_{date:%Y%m%d_%H%M%S}",
    "_{rand:6}",
    "_{uuid:8}",
    "_{timestamp}",
    "_{pid}_{num}",
)

_OPTIONS = (
    "-f",
    "--format",
    "-r",
    "--reserve",
    "-x",
    "--exec",
    "--always-suffix",
    "--max-num",
    "--dir",
    "--file",
    "-v",
    "--verbose",
    "--completion",
    "--version",
    "-h",
    "--help",
)

_BASH = """\
# uniqpath completion for bash
# Install with:  eval "$(uniqpath --completion bash)"
_uniqpath_completion() {{
    local cur prev
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"

    case "$prev" in
        -f|--format)
            COMPREPLY=($(compgen -W '{formats}' -- "$cur"))
            return 0
            ;;
        --completion)
            COMPREPLY=($(compgen -W '{shells}' -- "$cur"))
            return 0
            ;;
        --max-num)
            return 0
            ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W '{options}' -- "$cur"))
    else
        COMPREPLY=($(compgen -f -- "$cur"))
    fi
    return 0
}}
complete -o filenames -F _uniqpath_completion uniqpath
"""

_ZSH = """\
#compdef uniqpath
# uniqpath completion for zsh
# Install with:  uniqpath --completion zsh > "${{fpath[1]}}/_uniqpath"
# or, quick and dirty:  eval "$(uniqpath --completion zsh)"

_uniqpath() {{
    _arguments -s \\
        '(-f --format)'{{-f,--format}}'[suffix pattern]:format:({formats})' \\
        '(-r --reserve)'{{-r,--reserve}}'[atomically create the path]' \\
        '(-x --exec)'{{-x,--exec}}'[run a command with the reserved path]' \\
        '--always-suffix[add a suffix even when the base path is free]' \\
        '--max-num[give up after N attempts]:attempts:' \\
        '(--file)--dir[treat the target as a directory]' \\
        '(--dir)--file[treat the target as a file]' \\
        '(-v --verbose)'{{-v,--verbose}}'[log each attempt on stderr]' \\
        '--completion[print a shell completion script]:shell:({shells})' \\
        '--version[show the version and exit]' \\
        '(-h --help)'{{-h,--help}}'[show help and exit]' \\
        '1:path:_files'
}}

compdef _uniqpath uniqpath
"""

_FISH = """\
# uniqpath completion for fish
# Install with:  uniqpath --completion fish > ~/.config/fish/completions/uniqpath.fish

complete -c uniqpath -f -a "(__fish_complete_path)"
{format_lines}
complete -c uniqpath -s r -l reserve   -d "Atomically create the path"
complete -c uniqpath -s x -l exec      -d "Run a command with the reserved path"
complete -c uniqpath      -l always-suffix -d "Suffix even when the path is free"
complete -c uniqpath      -l max-num -r -d "Give up after N attempts"
complete -c uniqpath      -l dir       -d "Treat the target as a directory"
complete -c uniqpath      -l file      -d "Treat the target as a file"
complete -c uniqpath -s v -l verbose   -d "Log each attempt on stderr"
complete -c uniqpath      -l completion -x -a "{shells}" -d "Print a completion script"
complete -c uniqpath      -l version   -d "Show the version and exit"
complete -c uniqpath -s h -l help      -d "Show help and exit"
"""


def completion_script(shell: str) -> str:
    """Return the completion script for ``shell``.

    Raises:
        ValueError: the shell is not one of :data:`SHELLS`.
    """
    shells = " ".join(SHELLS)
    if shell == "bash":
        return _BASH.format(
            formats=" ".join(_FORMATS),
            shells=shells,
            options=" ".join(_OPTIONS),
        )
    if shell == "zsh":
        return _ZSH.format(
            formats=" ".join(fmt.replace(":", "\\:") for fmt in _FORMATS),
            shells=shells,
        )
    if shell == "fish":
        format_lines = "\n".join(
            f'complete -c uniqpath -s f -l format -x -a "{fmt}"' for fmt in _FORMATS
        )
        return _FISH.format(format_lines=format_lines, shells=shells)
    raise ValueError(
        f"unsupported shell {shell!r}; expected one of {', '.join(SHELLS)}"
    )
