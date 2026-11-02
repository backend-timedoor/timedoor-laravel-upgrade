---
max_turns: 25
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Edit, Write, "Bash(git:*)", "Bash(php -v)", "Bash(php artisan:*)", "Bash(composer:*)", "Bash(vendor/bin/*)"]
model: sonnet
runs: 3
---
/laravel-upgrade
