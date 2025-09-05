from backend.rag.chroma_instance import get_chroma_client
from main_app.config import Config
from backend.chatbot.process_query import process_query_with_rag
from backend.rag.vector_db_name_generation import generate_vector_db_document_name

import google.generativeai as genai

import pandas as pd
import regex as re
import time

model = genai.GenerativeModel("gemini-2.0-flash")
chroma_client = get_chroma_client(Config.CHROMA_CLIENT_DIR)

# Optional settings
change_length_checkbox = "False"
enhancer_checkbox = "True"
output_size = "short"  # DEPENDS ON THE PR
slider_value = 0.8
rag_doc_slider = "RAG"  # or "doc"

# Load Excel with Questions and Real Answers prepared by human and LLM
df = pd.read_excel(
    "https://raw.githubusercontent.com/Andrzej-Tezyk/KNF_Tool/main/src/Q_A_total.xlsx"
)  # change to main before commit
# Ensure the RAG answer column exists
if "A_tool" not in df.columns:
    df["A_tool"] = ""
df["A_tool"] = df["A_tool"].astype("string")

# Iterate through rows and get RAG answers
for idx, row in df.iterrows():
    if pd.isna(row["A_tool"]) or row["A_tool"] == "":  # skip if already filled
        prompt = row["Q"]
        recommendation_type = row.get("Recommendation", "").strip().upper()
        if recommendation_type == "A":
            pdf_name = "2025-01-17_Rekomendacja A - dotycząca zarządzania przez banki ryzykiem związanym z działalnością na instrumentach pochodnych"
        elif recommendation_type == "B":
            pdf_name = "2025-01-17_Rekomendacja B - dotycząca ograniczania ryzyka inwestycji finansowych banków"
        else:
            continue  # Skip if unknown
    collection_name = generate_vector_db_document_name(
        pdf_name, max_length=Config.CHROMADB_MAX_FILENAME_LENGTH
    )
    try:
        print(f"Processing Q{idx+1}: {prompt}")
        chunks = process_query_with_rag(
            prompt,
            pdf_name,
            model,
            change_length_checkbox,
            enhancer_checkbox,
            output_size,
            slider_value,
            chroma_client,
            collection_name,
            rag_doc_slider,
        )

        full_answer = ""
        for chunk in chunks:
            if "content" in chunk:
                full_answer += chunk["content"]
            elif "error" in chunk:
                full_answer = f"[Error]: {chunk['error']}"
                break
        print("Answer:", full_answer[:300])
        df.at[idx, "A_tool"] = full_answer
        time.sleep(15)
    except Exception as e:
        df.at[idx, "A_tool"] = f"[Exception]: {str(e)}"


def clean_markdown(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Remove bold (**text**) and italic (*text*) markdown
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # remove ** **
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # remove * *
    text = re.sub(r"__(.*?)__", r"\1", text)  # remove __ __
    text = re.sub(r"_(.*?)_", r"\1", text)  # remove _ _
    text = re.sub(r"\s+", " ", text)
    return text.strip()


df["A_tool"] = df["A_tool"].apply(clean_markdown)

df.to_excel("Q_A_total_completed.xlsx", index=False)
