from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import tempfile
from pathlib import Path
import requests
import yaml

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

app = FastAPI()

class URLRequest(BaseModel):
    urls: List[str]

@app.post("/parse")
async def parse_docs(payload: URLRequest):
    results = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        local_files = []

        for url in payload.urls:
            try:
                filename = url.split("/")[-1].split("?")[0] or "download"
                local_path = tmp_path / filename
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                local_path.write_bytes(response.content)
                local_files.append(local_path)
            except Exception as e:
                results.append({
                    "filename": url,
                    "error": str(e)
                })

        if local_files:
            doc_converter = DocumentConverter(
                allowed_formats=[
                    InputFormat.PDF,
                    InputFormat.IMAGE,
                    InputFormat.DOCX,
                    InputFormat.HTML,
                    InputFormat.PPTX,
                    InputFormat.ASCIIDOC,
                    InputFormat.CSV,
                    InputFormat.MD,
                ],
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_cls=StandardPdfPipeline,
                        backend=PyPdfiumDocumentBackend,
                    ),
                    InputFormat.DOCX: WordFormatOption(pipeline_cls=SimplePipeline),
                },
            )

            conv_results = doc_converter.convert_all(local_files)

            for res in conv_results:
                doc_dict = res.document.export_to_dict()
                results.append({
                    "filename": res.input.file.name,
                    "markdown": res.document.export_to_markdown(),
                    "json": doc_dict,
                    "yaml": yaml.safe_dump(doc_dict, allow_unicode=True),
                })

    return results