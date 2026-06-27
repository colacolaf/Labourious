# LEAST PRIVILEGE — IAM SCOPING & ACCESS CONTROL

## Core Rule
Never generate or suggest code that requests more permissions than the task requires.
If uncertain about required scope → request minimum, document why.

## Permission Rules

### File System
- Read only files needed for the task
- Write only to explicitly scoped paths
- Never `chmod 777`, never `chmod -R`
- Prefer specific path over glob: `./data/` not `./`

### Database
- SELECT only unless task requires mutation
- Never `DROP`, `TRUNCATE`, `DELETE` without explicit user confirmation
- No `GRANT ALL`. Scope to minimum required tables/operations.
- Migrations: always reversible (add `down` migration)

### Network
- Outbound only to specified endpoints
- No wildcard CORS (`*`) in production config
- No `verify=False` in TLS/SSL
- Explicit allowlist > implicit allow-all

### Process / Shell
- Never `sudo` or `su` in generated code
- No `subprocess.shell=True` with user input
- No `os.system()` with interpolated variables
- Prefer `subprocess.run([...])` with explicit args list

### API Keys / Secrets
- Never hardcode. Always: env var or vault.
- Never log. Never print. Never f-string into error messages.
- Minimum scope: use read-only keys when writes not needed

## Rejection Rule
If task requires root/admin/superuser → stop, explain minimum needed scope,
ask user to grant explicitly. Do not work around with elevated temp permissions.
