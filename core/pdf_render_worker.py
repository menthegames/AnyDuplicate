"""
Отдельный процесс для рендеринга PDF.
Запускается через subprocess, чтобы segfault в pypdfium2 не убил основное приложение.
Сохраняет результат как PNG во временный файл.
"""
import sys
import os
import tempfile
import traceback


def main():
    if len(sys.argv) < 2:
        print("ERROR: No PDF path provided", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    
    if not os.path.isfile(pdf_path):
        print(f"ERROR: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    try:
        import pypdfium2 as pdfium
        
        pdf = pdfium.PdfDocument(pdf_path)
        if len(pdf) == 0:
            pdf.close()
            print("ERROR: PDF has no pages", file=sys.stderr)
            sys.exit(1)
        
        page = pdf[0]
        width, height = page.get_size()
        
        # Масштабируем, чтобы вписаться в 800x800
        scale = min(800.0 / width, 800.0 / height, 2.0) if width > 0 and height > 0 else 1.0
        
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        
        # Сохраняем во временный PNG файл
        fd, tmp_path = tempfile.mkstemp(suffix=".png", prefix="anydup_pdf_")
        os.close(fd)
        
        pil_image.save(tmp_path, format="PNG")
        
        # Выводим путь к файлу в stdout
        print(tmp_path)
        
        pdf.close()
        sys.exit(0)
        
    except ImportError:
        print("ERROR: pypdfium2 not installed", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
