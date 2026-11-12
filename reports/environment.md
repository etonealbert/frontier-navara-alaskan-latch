# Actual build environment

- OS: macOS-26.0.1-arm64-arm-64bit
- Architecture: arm64
- Python: 3.12.13
- Interpreter: /Users/albertlukmanov/CodeBase/3D models/armrest_latch_agent_project/.venv/bin/python
- build123d: 0.13.0 (stable PyPI release)
- OpenCascade Python package: 8.0.1.1.0
- trimesh: 5.2.0
- matplotlib: 3.11.2
- Installation: local `.venv` using Homebrew Python 3.12; no administrator privileges required.
- Host is macOS arm64; the Windows-specific setup directions were adapted to the actual host.
- Full dependency versions: `requirements-lock.txt`. Minimal pinned build requirements: `requirements.txt`.
- Official API references: https://build123d.readthedocs.io/en/latest/installation.html and https://build123d.readthedocs.io/en/latest/introductory_examples.html
- All CAD coordinates and STEP units are mm. STL does not store a unit declaration.
- Removed 8 collapsed zero-area tessellation facets; no geometry was moved and no holes were filled. See `mesh_cleanup.json`.
