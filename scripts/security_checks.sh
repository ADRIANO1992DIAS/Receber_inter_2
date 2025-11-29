#!/bin/sh
set -e

pip-audit
safety check --full-report || true
bandit -r .
