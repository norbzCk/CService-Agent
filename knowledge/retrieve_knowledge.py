from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent

def retrieve_knowledge(query: str) -> str:
    """Retrieve relevant information from the Soko-link knowledge base based on the query.
    
    Args:
        query (str): The user's query for which knowledge is to be retrieved.
    
        Returns:
        str: The relevant information from the knowledge base 
    """

    knowledge = {}

    for file in KNOWLEDGE_DIR.glob("*.md"):
        with open(file, "r", encoding="utf-8") as f:
            knowledge[file.stem] = f.read()

    return knowledge.get(
        query,"I'm sorry, I don't have that information in my knowledge base."    
    )

if __name__ == "__main__":
    result = retrieve_knowledge("company_information")
    print(result)