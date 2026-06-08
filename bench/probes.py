"""Retention probes: real factual questions about earlier features.

Each probe's `accept` list holds substrings, ANY of which appearing in an
answer counts as correct (case-insensitive). The facts are genuine details of
the cc-gradient-statusline build, so the Full baseline establishes an honest
ceiling. `feature` is which feature the fact comes from (lower = older = harder
to retain after compaction).
"""

PROBES = [
    dict(id="oauth_endpoint", feature=1,
         q="What exact HTTP endpoint does the status line fetch account usage from?",
         accept=["api/oauth/usage", "oauth/usage"]),
    dict(id="stdin_rejected", feature=1,
         q="Why was the per-session stdin rate_limits snapshot rejected in favor "
           "of a shared cache for the 5h/7d numbers?",
         accept=["snapshot", "last api", "frozen", "disagree", "stale", "per-session"]),
    dict(id="ps_a_slow", feature=2,
         q="Which specific command for listing processes was found to be very "
           "slow (seconds) and had to be avoided?",
         accept=["ps -a", "ps -ao", "whole table", "all processes", "process table"]),
    dict(id="shed_order", feature=2,
         q="In the responsive layout, in what priority order is detail dropped "
           "as the pane narrows?",
         accept=["model name", "ctx", "countdown", "bars", "label"]),
    dict(id="width_ancestor", feature=2,
         q="Why must the status-line process read an ANCESTOR process's tty to "
           "get the terminal width?",
         accept=["owns no tty", "no tty", "pipes", "stdin/stdout", "no controlling"]),
    dict(id="visible_len", feature=2,
         q="What is the name of the function that measures on-screen width while "
           "ignoring ANSI color codes?",
         accept=["visible_len"]),
    dict(id="time_hooks", feature=3,
         q="Which two hook events are used to give Claude real-time date/time, "
           "and which script runs on each?",
         accept=["userpromptsubmit", "posttooluse"]),
    dict(id="throttle_default", feature=3,
         q="What is the default throttle interval for the time-injection hook, "
           "and which env var overrides it?",
         accept=["cc_time_interval", "60"]),
    dict(id="pill_bg", feature=0,
         q="What RGB color is the dark 'pill' background behind the gradient "
           "status bar?",
         accept=["22, 23, 30", "22,23,30", "(22, 23, 30)", "#16171e"]),
    dict(id="theme_default", feature=0,
         q="What is the default theme name for the status line, and what does it do?",
         accept=["pill"]),
    dict(id="gradient_high", feature=0,
         q="At high utilization (near the limit), what color does the gradient "
           "bar reach?",
         accept=["red", "255, 60, 60", "255,60,60"]),
    dict(id="cache_consistency", feature=1,
         q="What property does sourcing usage from one shared cache file give "
           "across multiple Claude sessions?",
         accept=["consisten", "same", "identical", "agree"]),
    dict(id="refresh_interval", feature=1,
         q="What status-line setting makes Claude Code re-run the command every "
           "second, and what are its units?",
         accept=["refreshinterval", "second"]),
    dict(id="bg_rearm", feature=0,
         q="How does the pill keep its background color across ANSI resets within "
           "the line?",
         accept=["re-arm", "rearm", "after every reset", "48;2", "bgcode"]),
]
