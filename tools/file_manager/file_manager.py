
import os
import errno
import shutil
import tempfile

from pathlib import Path

import config


class FileManager:

    CATEGORIES = {
        "documents",
        "images",
        "code",
        "research",
        "uncategorized"
    }

    ROOTS = {
        "imports": config.IMPORT_DIR,
        "archive": config.ARCHIVE_DIR,
        "exports": config.EXPORT_DIR
    }


    def __init__(self):

        self.max_size_bytes = (
            config.ARCHIVE_MAX_SIZE_MB * 1024 * 1024
        )

        self.allowed_extensions = {
            extension.lower()
            for extension in config.ARCHIVE_ALLOWED_EXTENSIONS
        }

        for root in self.ROOTS.values():
            root.mkdir(parents=True, exist_ok=True)


    def _validate_relative_path(self, relative_path):

        if not isinstance(relative_path, str):
            raise ValueError("Path must be a string.")

        if not relative_path or "\x00" in relative_path:
            raise ValueError("Invalid path.")

        normalized = relative_path.replace("\\", "/")

        parts = normalized.split("/")

        if normalized.startswith("/"):
            raise ValueError("Absolute paths are forbidden.")

        if any(part in ("..", ".", "") for part in parts):
            raise ValueError("Invalid relative path.")

        path = Path(*parts)

        if path.is_absolute():
            raise ValueError("Absolute paths are forbidden.")

        return path


    def _resolve_safe(self, root_name, relative_path):

        if root_name not in self.ROOTS:
            raise ValueError("Directory is not allowed.")

        root = self.ROOTS[root_name].resolve(strict=True)

        relative = self._validate_relative_path(
            relative_path
        )

        current = root

        for part in relative.parts:

            current = current / part

            if current.is_symlink():
                raise ValueError("Symbolic links are forbidden.")

        resolved = current.resolve(strict=False)

        if not resolved.is_relative_to(root):
            raise ValueError("Path escapes the allowed directory.")

        return resolved


    def _validate_file(self, file_path):

        if file_path.is_symlink():
            raise ValueError("Symbolic links are forbidden.")

        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("Source file does not exist.")

        extension = file_path.suffix.lower()

        if extension not in self.allowed_extensions:
            raise ValueError(
                f"Unsupported file extension: {extension or 'none'}"
            )

        size = file_path.stat().st_size

        if size > self.max_size_bytes:
            raise ValueError(
                "File exceeds the maximum allowed size."
            )

        return {
            "size_bytes": size,
            "extension": extension
        }


    def list_import_files(
        self,
        recursive=False,
        max_results=500
    ):

        if not isinstance(max_results, int) or not 1 <= max_results <= 500:
            raise ValueError("max_results must be between 1 and 500.")

        root = self.ROOTS["imports"].resolve(strict=True)

        files = []

        iterator = root.rglob("*") if recursive else root.iterdir()

        for path in iterator:

            if path.is_symlink():
                continue

            if not path.is_file():
                continue

            try:

                resolved = path.resolve(strict=True)

                if not resolved.is_relative_to(root):
                    continue

                relative = resolved.relative_to(root)

                if resolved.suffix.lower() not in self.allowed_extensions:
                    continue

                if resolved.stat().st_size > self.max_size_bytes:
                    continue

                files.append({
                    "name": resolved.name,
                    "path": relative.as_posix(),
                    "extension": resolved.suffix.lower(),
                    "size_bytes": resolved.stat().st_size
                })

            except (OSError, ValueError):
                continue

            if len(files) >= max_results:
                break

        return {
            "success": True,
            "count": len(files),
            "files": files
        }


    def _move_file(
        self,
        source_root,
        source_relative,
        destination_root,
        destination_relative
    ):

        source = self._resolve_safe(
            source_root,
            source_relative
        )

        destination = self._resolve_safe(
            destination_root,
            destination_relative
        )

        if source == destination:
            raise ValueError("Source and destination are identical.")

        if not source.is_file():
            raise FileNotFoundError("Source file does not exist.")

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Revalidate after creating the destination directory.
        destination = self._resolve_safe(
            destination_root,
            destination_relative
        )

        if destination.exists():
            raise FileExistsError(
                f"Destination already exists: {destination.name}"
            )

        self._validate_file(source)

        temporary_path = None

        try:

            # Hard linking is atomic and refuses to overwrite.
            try:

                os.link(
                    source,
                    destination,
                    follow_symlinks=False
                )

            except OSError as error:

                if error.errno != errno.EXDEV:
                    raise

                # Cross-filesystem fallback:
                # Copy to a temporary file, then create the
                # destination exclusively using a hard link.

                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=".archive_",
                    suffix=".tmp",
                    dir=destination.parent
                )

                os.close(descriptor)

                temporary_path = Path(temporary_name)

                shutil.copy2(
                    source,
                    temporary_path,
                    follow_symlinks=False
                )

                os.link(
                    temporary_path,
                    destination,
                    follow_symlinks=False
                )

                temporary_path.unlink()
                temporary_path = None

            try:

                source.unlink()

            except Exception:

                # Roll back the destination if the original
                # source cannot be removed.

                destination.unlink(missing_ok=True)
                raise

            return {
                "success": True,
                "source": str(source_relative),
                "destination": str(destination_relative)
            }

        finally:

            if temporary_path and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)


    def move_import_to_archive(
        self,
        source_relative,
        category,
        destination_name=None
    ):

        if category not in self.CATEGORIES:
            raise ValueError("Invalid archive category.")

        source = self._resolve_safe(
            "imports",
            source_relative
        )

        destination_name = (
            destination_name or source.name
        )

        if (
            not isinstance(destination_name, str)
            or not destination_name
            or destination_name in (".", "..")
            or "/" in destination_name
            or "\\" in destination_name
            or "\x00" in destination_name
        ):
            raise ValueError("Invalid destination filename.")

        if Path(destination_name).suffix.lower() not in self.allowed_extensions:
            raise ValueError("Unsupported destination file extension.")

        destination_relative = (
            Path(category) / destination_name
        ).as_posix()

        return self._move_file(
            "imports",
            source_relative,
            "archive",
            destination_relative
        )


    def move_archive_to_import(
        self,
        archive_relative,
        import_relative
    ):

        return self._move_file(
            "archive",
            archive_relative,
            "imports",
            import_relative
        )


    def get_file_info(self, relative_path):

        file_path = self._resolve_safe(
            "imports",
            relative_path
        )

        information = self._validate_file(file_path)

        return {
            "success": True,
            "name": file_path.name,
            "path": relative_path,
            "extension": information["extension"],
            "size_bytes": information["size_bytes"]
        }
