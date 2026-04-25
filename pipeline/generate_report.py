import chromadb
import os
import webbrowser

def generate_html_dashboard():
    print("Generating Visual Dashboard for Judges...")
    
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    
    # Connect to the new Doctors collection
    collection = client.get_collection(name="malaysia_doctors")
    results = collection.get()
    
    if not results or not results['metadatas']:
        print("No data found in the database!")
        return

    html_content = """
    <html>
    <head>
        <title>Medical AI - Doctor Database</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; padding: 20px; }
            h1 { color: #2c3e50; text-align: center; }
            .subtitle { text-align: center; color: #7f8c8d; margin-bottom: 30px; }
            table { width: 100%; border-collapse: collapse; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
            th, td { padding: 15px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #8e44ad; color: white; }
            tr:hover { background-color: #f5f5f5; }
            .hosp-badge { background-color: #2980b9; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
            .tier-badge { background-color: #16a085; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        </style>
    </head>
    <body>
        <h1>🩺 Live Doctor Vector Database (ChromaDB)</h1>
        <div class="subtitle">Granular Specialist Matching Engine</div>
        <table>
            <tr>
                <th>Doctor Name</th>
                <th>Sub-Specialty</th>
                <th>Hospital Affiliation</th>
                <th>Foreigner Tier</th>
                <th>Raw RAG Vector (AI Knowledge)</th>
            </tr>
    """

    for i in range(len(results['metadatas'])):
        meta = results['metadatas'][i]
        doc = results['documents'][i]
        
        doc_html = doc.replace('\n', '<br>')
        
        html_content += f"""
            <tr>
                <td><strong>{meta.get('name', 'N/A')}</strong></td>
                <td>{meta.get('specialty', 'N/A')}</td>
                <td><span class="hosp-badge">{meta.get('hospital', 'N/A')}</span></td>
                <td><span class="tier-badge">{meta.get('tier', 'N/A')}</span></td>
                <td style="font-size: 13px; color: #555;">{doc_html}</td>
            </tr>
        """

    html_content += """
        </table>
    </body>
    </html>
    """

    output_file = os.path.join(os.path.dirname(__file__), "..", "reports", "db_dashboard.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Dashboard generated at: {os.path.abspath(output_file)}")
    
    try:
        webbrowser.open('file://' + os.path.abspath(output_file))
        print("Opening in your web browser...")
    except Exception as e:
        print("Could not open browser automatically. Please open the file manually.")

if __name__ == "__main__":
    generate_html_dashboard()
