from docx import Document
doc = Document('my_resume.docx')
text = "\n".join(p.text for p in doc.paragraphs)
with open("resume_text.txt", "w", encoding="utf-8") as f:
    f.write(text)
print("Done")