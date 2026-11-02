#!/bin/bash
set -eu
umask 022
/opt/netclaw-r01/rag-venv/bin/python -m pip install 'torch>=2,<3' --index-url https://download.pytorch.org/whl/cpu
/opt/netclaw-r01/rag-venv/bin/python -m pip install /opt/netclaw-r01/source/mcp-servers/rag-mcp
chgrp -R netclaw-r01 /opt/netclaw-r01/rag-venv
chmod -R g+rX /opt/netclaw-r01/rag-venv
printf 'RAG_INSTALL_COMPLETE\n'
