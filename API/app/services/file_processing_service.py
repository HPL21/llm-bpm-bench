import io
import logging
import os
import tempfile
import base64

from PIL import Image
import pymupdf4llm
from app.models.file_asset import FileAsset
from app.services.storage_service import storage_service

logger = logging.getLogger("BenchmarkWorker")

MAX_IMAGE_SIZE = (1024, 1024)


class FileProcessingService:
    """Service for processing files from MinIO (PDF, images)"""

    @staticmethod
    def get_file_content(file_asset: FileAsset) -> dict:
        """
        Pobiera plik z MinIO i przygotowuje jego zawartość na podstawie formatu.
        Dla PDF - ekstrakcja tekstu. Dla obrazów - optymalizacja, resize i konwersja do Base64.
        Funkcja synchroniczna (blokująca), powinna być wywoływana w osobnym wątku.
        """
        response = None
        try:
            response = storage_service.client.get_object(
                storage_service.bucket_name,
                file_asset.minio_path
            )
            file_bytes = response.read()
        except Exception as e:
            logger.error(f"Nie udało się pobrać pliku {file_asset.filename} z MinIO: {e}")
            return {"type": "error", "content": f"[Błąd pobierania pliku: {file_asset.filename}]"}
        finally:
            if response:
                response.close()
                response.release_conn()

        return FileProcessingService._process_file_by_extension(file_asset, file_bytes)

    @staticmethod
    def _process_file_by_extension(file_asset: FileAsset, file_bytes: bytes) -> dict:
        """Process file based on its extension"""
        ext = os.path.splitext(file_asset.filename)[1].lower()

        if ext == ".pdf":
            return FileProcessingService._process_pdf(file_bytes, file_asset.filename)
        elif ext in [".jpg", ".jpeg", ".png"]:
            return FileProcessingService._process_image(file_bytes, file_asset.filename, ext)
        else:
            logger.warning(f"Nieobsługiwany format pliku: {ext} ({file_asset.filename})")
            return {"type": "error", "content": f"[Pominięto nieobsługiwany format pliku: {file_asset.filename}]"}

    @staticmethod
    def _process_pdf(file_bytes: bytes, filename: str) -> dict:
        """Extract text from PDF file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            logger.info(f"Ekstrakcja tekstu z pliku PDF: {filename}")
            md_text = pymupdf4llm.to_markdown(tmp_path)
            return {"type": "text", "content": md_text}
        except Exception as e:
            logger.error(f"Błąd podczas parsowania pliku PDF {filename}: {e}")
            return {"type": "error", "content": f"[Błąd przetwarzania pliku PDF: {filename}]"}
        finally:
            os.remove(tmp_path)

    @staticmethod
    def _process_image(file_bytes: bytes, filename: str, ext: str) -> dict:
        """Process image - resize and convert to Base64"""
        logger.info(f"Przygotowanie i optymalizacja obrazu {filename} do wysłania.")
        try:
            img = Image.open(io.BytesIO(file_bytes))
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                alpha_mask = img.convert("RGBA").split()[3]
                background.paste(img, mask=alpha_mask)
                img = background
                ext = ".jpg"
            elif img.mode != "RGB":
                img = img.convert("RGB")
            img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            save_format = "PNG" if ext == ".png" else "JPEG"
            save_kwargs = {"format": save_format}
            if save_format == "JPEG":
                save_kwargs["quality"] = 85
                save_kwargs["optimize"] = True
            img.save(buffer, **save_kwargs)
            processed_bytes = buffer.getvalue()
            b64_img = base64.b64encode(processed_bytes).decode("utf-8")
            mime = "image/png" if ext == ".png" else "image/jpeg"
            return {"type": "image", "content": b64_img, "mime_type": mime}
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania obrazu {filename}: {e}")
            return {"type": "error", "content": f"[Błąd przetwarzania obrazu: {filename}]"}
