"""Genera los manuales DOCX desde Markdown usando solo la biblioteca estandar."""
from pathlib import Path
import re
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def run(text, props=""):
    return f'<w:r><w:rPr>{props}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def inline(text, links):
    tokens = re.split(r"(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))", text)
    output = []
    for token in tokens:
        if token.startswith("`"):
            output.append(run(token[1:-1], '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>'))
        elif token.startswith("**"):
            output.append(run(token[2:-2], "<w:b/>"))
        elif match := re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", token):
            label, url = match.groups()
            if url.startswith("https://"):
                links.append(url)
                output.append(f'<w:hyperlink r:id="link{len(links)}">' +
                              run(label, '<w:color w:val="0563C1"/><w:u w:val="single"/>') + '</w:hyperlink>')
            else:
                output.append(run(f"{label} ({url})"))
        else:
            output.append(run(token))
    return "".join(output)


def paragraph(text, links, style="Normal"):
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>{inline(text, links)}</w:p>'


def table(rows, links):
    result = ['<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>' +
               ''.join(f'<w:{side} w:val="single" w:sz="4" w:color="DCE3EB"/>'
                       for side in ("top", "left", "bottom", "right", "insideH", "insideV")) +
               '</w:tblBorders></w:tblPr>']
    for index, row in enumerate(rows):
        result.append('<w:tr>' + ('<w:trPr><w:tblHeader/></w:trPr>' if index == 0 else ''))
        for cell in row:
            shade = '<w:shd w:fill="E8EFF7"/>' if index == 0 else ''
            result.append(f'<w:tc><w:tcPr>{shade}</w:tcPr>' + paragraph(cell, links, "TableText") + '</w:tc>')
        result.append('</w:tr>')
    return ''.join(result) + '</w:tbl>'


def render(markdown):
    lines = markdown.splitlines()
    body, links = [], []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            code = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(run(lines[index]))
                index += 1
            body.append('<w:p><w:pPr><w:pStyle w:val="Code"/></w:pPr>' +
                        '<w:r><w:br/></w:r>'.join(code) + '</w:p>')
        elif line == "<!-- pagebreak -->":
            body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        elif line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                cells = [c.strip() for c in lines[index].strip('|').split('|')]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                index += 1
            body.append(table(rows, links))
            continue
        elif line.startswith("# "):
            body.append(paragraph(line[2:], links, "Title"))
        elif line.startswith("## "):
            body.append(paragraph(line[3:], links, "Heading1"))
        elif line.startswith("- "):
            body.append(paragraph("• " + line[2:], links))
        elif line.strip():
            body.append(paragraph(line, links))
        index += 1
    return ''.join(body), links


STYLES = f'''<w:styles xmlns:w="{W}">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="21"/><w:lang w:val="es-AR"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="95" w:line="245" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:keepNext/></w:pPr><w:rPr><w:b/><w:color w:val="17365D"/><w:sz w:val="36"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:keepNext/><w:spacing w:before="140" w:after="90"/></w:pPr><w:rPr><w:b/><w:color w:val="17365D"/><w:sz w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:pPr><w:keepLines/><w:spacing w:before="50" w:after="95" w:line="215" w:lineRule="auto"/><w:shd w:fill="F0F3F6"/><w:ind w:left="100" w:right="100"/></w:pPr><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="17"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="TableText"/><w:pPr><w:spacing w:after="60"/></w:pPr><w:rPr><w:sz w:val="18"/></w:rPr></w:style>
</w:styles>'''


def build(source, target):
    body, links = render(source.read_text(encoding="utf-8-sig"))
    document = f'''<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>{body}
<w:sectPr><w:footerReference w:type="default" r:id="footer"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="800" w:right="900" w:bottom="850" w:left="900" w:footer="350"/></w:sectPr>
</w:body></w:document>'''
    relations = [f'<Relationship Id="styles" Type="{R}/styles" Target="styles.xml"/>',
                 f'<Relationship Id="footer" Type="{R}/footer" Target="footer.xml"/>']
    for index, url in enumerate(links, 1):
        relations.append(f'<Relationship Id="link{index}" Type="{R}/hyperlink" Target="{escape(url, {chr(34): "&quot;"})}" TargetMode="External"/>')
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    files = {
        "[Content_Types].xml": '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/footer.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>''',
        "_rels/.rels": f'<Relationships xmlns="{rel_ns}"><Relationship Id="document" Type="{R}/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": document,
        "word/styles.xml": STYLES,
        "word/_rels/document.xml.rels": f'<Relationships xmlns="{rel_ns}">{"".join(relations)}</Relationships>',
        "word/footer.xml": f'<w:ftr xmlns:w="{W}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>{run("Grupo 5 · REST y GraphQL · ")}<w:fldSimple w:instr="PAGE"/></w:p></w:ftr>',
    }
    temporary = target.with_suffix(".docx.tmp")
    try:
        with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + content)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Generado: {target.name}")


def main():
    build(ROOT / "docs/TUTORIAL.md", ROOT / "docs/Tutorial-presentacion-demo.docx")
    build(ROOT / "docs/CONCEPTOS.md", ROOT / "docs/Conceptos-REST-GraphQL.docx")


if __name__ == "__main__":
    main()
