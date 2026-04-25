import os
from pathlib import Path
from typing import List, Dict
import chromadb

# Path to our centralized vector database
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chroma_db"

def match_hospitals(medical_data: Dict) -> List[Dict]:
    """
    Match the patient's condition to specific Specialists (Doctors) using the Centralized Doctor RAG.
    """
    if not os.path.exists(DB_PATH):
        print("⚠️ Warning: ChromaDB not found. Please run 'python pipeline/ingest_doctors.py' first.")
        return []

    # Connect to the persistent database
    client = chromadb.PersistentClient(path=str(DB_PATH))
    
    try:
        collection = client.get_collection(name="malaysia_doctors")
    except Exception:
        print("⚠️ Warning: 'malaysia_doctors' collection not found.")
        return []
        
    condition = medical_data.get("condition", "General Cardiology")
    sub_specialty = medical_data.get("sub_specialty_inference", condition)
    
    # Query the Doctor RAG
    query_text = f"Specialist for {condition} and {sub_specialty}."
    
    results = collection.query(
        query_texts=[query_text],
        n_results=3
    )
    
    matched_doctors = []
    if results and results.get("metadatas"):
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            doc_text = results["documents"][0][i]
            
            matched_doctors.append({
                "id": results["ids"][0][i],
                "name": meta.get("name"),
                "hospital": meta.get("hospital"),
                "specialty": meta.get("specialty"),
                "tier": meta.get("tier"),
                "rag_summary": doc_text
            })
            
    return matched_doctors
