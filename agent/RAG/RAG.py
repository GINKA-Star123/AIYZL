from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

loader = TextLoader("knowledge/RAG.md",encoding="utf-8")
docs =loader.load()

headers_to_split_on = [
    ("###", "Header 3"),
    ("##", "Header 2"),
    ("####", "Header 4"), 
]
# 创建 MarkdownHeaderTextSplitter 实例，指定要分割的标题级别

markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on,)
md_header_split = markdown_splitter.split_text(str(docs[0]).split("=")[1])

# 进一步使用 RecursiveCharacterTextSplitter 对分割后的文本进行更细粒度的分割

text_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", "。", "，", " ", ""],  # 分隔符优先级
    chunk_size=200,
    chunk_overlap=10,
)

chunks = text_splitter.split_documents(md_header_split)

print(chunks)