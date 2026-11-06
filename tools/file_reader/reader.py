
from pathlib import Path
import io
import os


class FileReaderError(Exception):
    """Fout tijdens het veilig lezen van bestanden."""


class FileReaderTool:

    ALLOWED_EXTENSIONS = {
        ".txt",
        ".md",
        ".py",
        ".json",
        ".yaml",
        ".yml",
        ".csv",
        ".log",
        ".ini",
        ".toml",
        ".xml",
        ".pdf",
    }

    def __init__(
        self,
        allowed_directory,
        max_file_size_mb=10,
        max_output_chars=30000,
    ):
        self.root = Path(allowed_directory).expanduser().resolve()

        if not self.root.exists():
            raise FileReaderError(
                f"De ingestelde leesmap bestaat niet: {self.root}"
            )

        if not self.root.is_dir():
            raise FileReaderError(
                "De ingestelde leeslocatie is geen map."
            )

        self.max_file_size_bytes = int(
            max_file_size_mb * 1024 * 1024
        )

        self.max_output_chars = int(max_output_chars)

        if self.max_file_size_bytes <= 0:
            raise ValueError("max_file_size_mb moet groter dan nul zijn.")

        if self.max_output_chars <= 0:
            raise ValueError("max_output_chars moet groter dan nul zijn.")



    def _resolve_path(self, path):
        if not isinstance(path, str) or not path.strip():
            raise FileReaderError("Geef een geldig bestandspad op.")

        supplied_path = Path(path.strip())

        if supplied_path.is_absolute():
            raise FileReaderError(
                "Gebruik een relatief pad binnen de toegestane leesmap."
            )

        if ".." in supplied_path.parts:
            raise FileReaderError(
                "Het gebruik van '..' in bestandspaden is niet toegestaan."
            )

        resolved = (self.root / supplied_path).resolve(strict=True)

        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise FileReaderError(
                "Toegang geweigerd: het pad valt buiten de toegestane map."
            )

        return resolved

    def _validate_file(self, path):
        if not path.is_file():
            raise FileReaderError("Het opgegeven pad is geen bestand.")

        extension = path.suffix.lower()

        if extension not in self.ALLOWED_EXTENSIONS:
            raise FileReaderError(
                f"Bestandstype '{extension}' wordt niet ondersteund."
            )

        size = path.stat().st_size

        if size > self.max_file_size_bytes:
            raise FileReaderError(
                "Het bestand is groter dan de toegestane bestandsgrootte."
            )

        return size



    def read_file(self, path, max_chars=None):

        file_path = self._resolve_path(path)
        size = self._validate_file(file_path)

        # Lees de bytes en controleer de grootte opnieuw.
        raw_data = file_path.read_bytes()

        if len(raw_data) > self.max_file_size_bytes:
            raise FileReaderError(
                "Het bestand is tijdens het lezen groter geworden "
                "dan toegestaan."
            )

        extension = file_path.suffix.lower()

        if extension == ".pdf":
            content, page_count = self._read_pdf(raw_data)
        else:
            content = self._decode_text(raw_data)
            page_count = None

        limit = self.max_output_chars

        if max_chars is not None:
            if isinstance(max_chars, bool) or not isinstance(max_chars, int):
                raise FileReaderError(
                    "max_chars moet een geheel getal zijn."
                )

            if max_chars <= 0:
                raise FileReaderError(
                    "max_chars moet groter dan nul zijn."
                )

            limit = min(max_chars, self.max_output_chars)

        truncated = len(content) > limit

        if truncated:
            content = content[:limit]

        result = {
            "success": True,
            "path": file_path.relative_to(self.root).as_posix(),
            "extension": extension,
            "size_bytes": size,
            "content": content,
            "truncated": truncated,
        }

        if truncated:
            result["notice"] = (
                "De inhoud is afgekapt vanwege de maximale uitvoerlengte."
            )

        if page_count is not None:
            result["page_count"] = page_count

        return result



    @staticmethod
    def _decode_text(raw_data):

        try:
            return raw_data.decode("utf-8-sig")

        except UnicodeDecodeError:
            try:
                return raw_data.decode("cp1252")

            except UnicodeDecodeError:
                raise FileReaderError(
                    "Het bestand kon niet als ondersteunde tekst "
                    "worden gelezen."
                )


    @staticmethod
    def _read_pdf(raw_data):

        try:
            from pypdf import PdfReader

        except ImportError:
            raise FileReaderError(
                "PDF-ondersteuning ontbreekt. "
                "Installeer pypdf met: pip install pypdf"
            )

        try:
            pdf = PdfReader(io.BytesIO(raw_data))

            if pdf.is_encrypted:
                raise FileReaderError(
                    "Beveiligde PDF-bestanden worden niet ondersteund."
                )

            pages = []

            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""

                pages.append(
                    f"--- Pagina {index} ---\n{text}"
                )

            return "\n\n".join(pages), len(pdf.pages)

        except FileReaderError:
            raise

        except Exception:
            raise FileReaderError(
                "De PDF kon niet worden gelezen."
            )



    def list_files(
        self,
        directory=".",
        recursive=False,
        max_results=100,
    ):

        if isinstance(recursive, str):
            if recursive.lower() in ("true", "1", "yes"):
                recursive = True
            elif recursive.lower() in ("false", "0", "no"):
                recursive = False
            else:
                raise FileReaderError(
                    "recursive moet true of false zijn."
                )

        if not isinstance(recursive, bool):
            raise FileReaderError(
                "recursive moet true of false zijn."
            )

        if isinstance(max_results, bool) or not isinstance(max_results, int):
            raise FileReaderError(
                "max_results moet een geheel getal zijn."
            )

        if not 1 <= max_results <= 500:
            raise FileReaderError(
                "max_results moet tussen 1 en 500 liggen."
            )

        target = self._resolve_directory(directory)

        results = []

        if recursive:
            for current_root, dirs, files in os.walk(
                target,
                followlinks=False,
            ):
                current_path = Path(current_root)

                # Sla symbolische links naar mappen over.
                dirs[:] = [
                    name
                    for name in dirs
                    if not (current_path / name).is_symlink()
                ]

                for filename in sorted(files):
                    file_path = current_path / filename

                    if file_path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
                        continue

                    try:
                        resolved = file_path.resolve(strict=True)
                        resolved.relative_to(self.root)

                        if not resolved.is_file():
                            continue

                        results.append(self._file_metadata(resolved))

                    except (OSError, ValueError, FileReaderError):
                        continue

                    if len(results) >= max_results:
                        return {
                            "success": True,
                            "directory": target.relative_to(
                                self.root
                            ).as_posix(),
                            "files": results,
                            "truncated": True,
                        }

        else:
            for file_path in sorted(target.iterdir()):
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
                    continue

                try:
                    resolved = file_path.resolve(strict=True)
                    resolved.relative_to(self.root)

                    results.append(self._file_metadata(resolved))

                except (OSError, ValueError, FileReaderError):
                    continue

                if len(results) >= max_results:
                    break

        return {
            "success": True,
            "directory": target.relative_to(self.root).as_posix(),
            "files": results,
            "truncated": len(results) >= max_results,
        }



    def _resolve_directory(self, directory):

        if not isinstance(directory, str) or not directory.strip():
            raise FileReaderError(
                "Geef een geldige map op."
            )

        supplied = Path(directory.strip())

        if supplied.is_absolute() or ".." in supplied.parts:
            raise FileReaderError(
                "Gebruik alleen relatieve mappaden binnen de leesmap."
            )

        resolved = (self.root / supplied).resolve(strict=True)

        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise FileReaderError(
                "Toegang geweigerd: de map valt buiten de toegestane leesmap."
            )

        if not resolved.is_dir():
            raise FileReaderError(
                "Het opgegeven pad is geen map."
            )

        return resolved



    def get_file_info(self, path):

        file_path = self._resolve_path(path)
        size = self._validate_file(file_path)

        stat = file_path.stat()

        return {
            "success": True,
            "path": file_path.relative_to(self.root).as_posix(),
            "name": file_path.name,
            "extension": file_path.suffix.lower(),
            "size_bytes": size,
            "size_kb": round(size / 1024, 2),
            "modified_timestamp": stat.st_mtime,
            "readable": True,
        }



    def _file_metadata(self, file_path):

        size = file_path.stat().st_size

        return {
            "name": file_path.name,
            "path": file_path.relative_to(self.root).as_posix(),
            "extension": file_path.suffix.lower(),
            "size_bytes": size,
        }
