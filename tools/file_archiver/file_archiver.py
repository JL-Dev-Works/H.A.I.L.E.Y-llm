
import hashlib

from pathlib import Path

from tools.file_manager.file_manager import FileManager
from tools.file_manager.archive_database import ArchiveDatabase


class FileArchiverTool:

    IMAGE_EXTENSIONS = {
        ".png", ".jpg", ".jpeg",
        ".gif", ".webp", ".bmp",
        ".svg", ".ico"
    }

    CODE_EXTENSIONS = {
        ".py", ".js", ".ts",
        ".html", ".css", ".sql",
        ".sh", ".java", ".cpp",
        ".c", ".h", ".hpp",
        ".rs", ".go", ".php"
    }

    DOCUMENT_EXTENSIONS = {
        ".txt", ".md", ".pdf",
        ".doc", ".docx",
        ".xls", ".xlsx",
        ".ppt", ".pptx",
        ".csv", ".json", ".xml",
        ".yaml", ".yml", ".toml",
        ".ini", ".log"
    }

    RESEARCH_KEYWORDS = {
        "research",
        "paper",
        "study",
        "thesis",
        "journal",
        "academic",
        "literature",
        "dissertation",
        "scientific"
    }


    def __init__(self):

        self.file_manager = FileManager()
        self.database = ArchiveDatabase()


    def categorize_file(self, filename):

        path = Path(filename)

        extension = path.suffix.lower()

        name_parts = {
            part.lower()
            for part in path.stem.replace("-", "_").split("_")
        }

        # Research takes priority for named research files.
        if name_parts & self.RESEARCH_KEYWORDS:
            return "research"

        if extension in self.IMAGE_EXTENSIONS:
            return "images"

        if extension in self.CODE_EXTENSIONS:
            return "code"

        if extension in self.DOCUMENT_EXTENSIONS:
            return "documents"

        return "uncategorized"


    def _get_destination_name(self, filename, sha256):

        path = Path(filename)

        # First attempt: original filename.
        return path.name


    def archive_file(self, path):

        """
        Archive one file from the configured imports directory.

        Arguments:
            path: Relative path inside the imports directory.
        """

        if not isinstance(path, str) or not path:
            return {
                "success": False,
                "error": "A valid relative file path is required."
            }

        try:

            # Validate and inspect the source file.
            information = self.file_manager.get_file_info(path)

            if not information["success"]:
                return information

            filename = information["name"]
            size_bytes = information["size_bytes"]
            extension = information["extension"]

            source = self.file_manager._resolve_safe(
                "imports",
                path
            )

            if not source.is_file():
                return {
                    "success": False,
                    "error": "Source file does not exist."
                }

            # Calculate SHA-256.
            sha256 = self.database.calculate_hash(source)

            # Check for duplicates.
            duplicate = self.database.find_by_hash(sha256)

            if duplicate:

                existing_path = (
                    self.file_manager.ROOTS["archive"]
                    / duplicate["archived_path"]
                )

                # Only report a duplicate if the file physically exists.
                if existing_path.is_file():

                    return {
                        "success": False,
                        "duplicate": True,
                        "message": "This file is already archived.",
                        "existing_file": duplicate["archived_path"],
                        "sha256": sha256
                    }

                # Metadata exists, but the archived file is missing.
                # Remove the stale metadata so archiving can continue.
                self.database.remove_by_hash(sha256)

            category = self.categorize_file(filename)

            destination_name = self._get_destination_name(
                filename,
                sha256
            )

            archive_relative = (
                Path(category) / destination_name
            ).as_posix()

            # Never overwrite existing files.
            destination = (
                self.file_manager.ROOTS["archive"]
                / archive_relative
            )

            if destination.exists():

                original = Path(filename)

                destination_name = (
                    f"{original.stem}_{sha256[:8]}"
                    f"{original.suffix}"
                )

                archive_relative = (
                    Path(category) / destination_name
                ).as_posix()

                destination = (
                    self.file_manager.ROOTS["archive"]
                    / archive_relative
                )

                if destination.exists():

                    return {
                        "success": False,
                        "error": "Archive destination already exists."
                    }

            # Move the file.
            move_result = self.file_manager.move_import_to_archive(
                source_relative=path,
                category=category,
                destination_name=destination_name
            )

            if not move_result["success"]:
                return move_result

            # Register metadata after a successful move.
            try:

                record = self.database.add_file(
                    original_name=filename,
                    archived_path=archive_relative,
                    category=category,
                    sha256=sha256,
                    size_bytes=size_bytes,
                    extension=extension
                )

            except Exception as database_error:

                # Attempt to restore the original import file.
                try:

                    self.file_manager.move_archive_to_import(
                        archive_relative=archive_relative,
                        import_relative=path
                    )

                except Exception as rollback_error:

                    return {
                        "success": False,
                        "error": "Database update and rollback both failed.",
                        "database_error": str(database_error),
                        "rollback_error": str(rollback_error),
                        "archive_path": archive_relative
                    }

                return {
                    "success": False,
                    "error": "Database update failed. Original file restored.",
                    "details": str(database_error)
                }

            return {
                "success": True,
                "message": "File successfully archived.",
                "file": record
            }

        except Exception as error:

            return {
                "success": False,
                "error": str(error),
                "error_type": type(error).__name__
            }


    def archive_all(self, max_results=100):

        """
        Archive all supported files in the imports directory.

        Files are processed individually.
        One failure does not stop the remaining files.
        """

        if not isinstance(max_results, int) or not 1 <= max_results <= 500:
            return {
                "success": False,
                "error": "max_results must be between 1 and 500."
            }

        try:

            listing = self.file_manager.list_import_files(
                recursive=True,
                max_results=max_results
            )

            results = []

            for file in listing["files"]:

                result = self.archive_file(
                    file["path"]
                )

                results.append({
                    "path": file["path"],
                    "result": result
                })

            successful = sum(
                1 for item in results
                if item["result"].get("success")
            )

            duplicates = sum(
                1 for item in results
                if item["result"].get("duplicate")
            )

            failed = len(results) - successful - duplicates

            return {
                "success": True,
                "total_processed": len(results),
                "successful": successful,
                "duplicates": duplicates,
                "failed": failed,
                "results": results
            }

        except Exception as error:

            return {
                "success": False,
                "error": str(error),
                "error_type": type(error).__name__
            }


    def list_archived_files(self):

        return {
            "success": True,
            "files": self.database.get_all_files()
        }


    def get_archive_statistics(self):

        return {
            "success": True,
            "statistics": self.database.get_statistics()
        }
