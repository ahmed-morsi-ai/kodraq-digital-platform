# Submission storage and history

Submission uploads use `StorageService` (`upload_file`, `open_file`, `delete_file`).
The default `LocalStorageService` persists bytes beneath `backend/uploads/private`.
This directory is ignored by Git and must not be mounted as public static content.
Downloads use the authenticated submission file endpoint, with the same owner /
assigned-instructor / admin permissions as submission details.

Configuration:

| Environment variable | Default |
| --- | --- |
| `STORAGE_LOCAL_ROOT` | Absolute path to `backend/uploads/private` |
| `SUBMISSION_MAX_FILE_BYTES` | `10485760` (10 MiB per file) |
| `SUBMISSION_MAX_FILES` | `10` per submission |

Uploads are streamed in bounded chunks. A failed batch rolls back its metadata
and deletes the newly stored objects. Deletion commits the metadata removal
before deleting bytes; a storage failure is logged and leaves a private orphan
for operational cleanup instead of breaking a still-existing database record.

Local storage needs a writable, persistent directory shared by API instances.
Vercel's temporary filesystem is not persistent storage. The local default is
for development; deploying this feature on Vercel requires an R2 implementation
of `StorageService` and overriding `get_storage_service`. R2 is not connected by
this change. An adapter must enforce the configured upload limit, remove partial
uploads on failure, return binary read streams, and provide idempotent deletion.
Files recorded by the previous metadata-only mock have no recoverable stored
bytes; those attachments must be uploaded again.

Run `alembic upgrade head` before serving the new submission detail response.
Migration `e7b252600001` adds submission attempts, retaining every future submit /
resubmit alongside existing review history. Backfill preserves the latest known
`submitted_at`; older overwritten attempt timestamps cannot be reconstructed.
Review feedback and grades are retained across rework. Files represent current
attachments, not immutable versions of each past attempt.

GitHub inputs accept HTTPS repository URLs of the form
`https://github.com/owner/repository`, with optional `.git` or trailing slash.
Credentials, ports, query strings, fragments, profile links and repository
subpaths are rejected. Validation checks URL format, not repository existence
or accessibility. Existing stored URLs remain readable in API responses.
