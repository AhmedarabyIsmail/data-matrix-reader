## Learned User Preferences

## Learned Workspace Facts

- On Windows, PowerShell in this environment may reject `&&` as a command separator; use `;`, separate lines, or `Set-Location` before the command when automating backend and frontend startup.
- The Python backend targets 3.9-friendly typing (for example `typing.Optional` rather than PEP 604 `X | None` unions).
