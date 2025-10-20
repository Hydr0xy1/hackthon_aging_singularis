import fitz, re, sys

def extract_text_from_pdf(pdf_path, out_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        lines = [l for l in page.get_text("text").split("\n") if not re.match(r"^\s*\d+\s*$", l)]
        text += "\n".join(lines) + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

if __name__ == "__main__":
    pdf_path = sys.argv[1]
    out_path = pdf_path.replace(".pdf", ".txt")
    extract_text_from_pdf(pdf_path, out_path)
    print(f"Extracted text saved to {out_path}")