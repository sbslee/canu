from langchain_google_community import GoogleSearchAPIWrapper

retrieve_from_web_json = {
    "name": "retrieve_from_web",
    "description": """Answer a question based on the content of a web search result. Do not use this function unless the user has explicitly requested to retrieve data from the web. For example, if the prompt is "What is the capital of France?", you must not use this function. However, if the prompt is "What is the capital of France? Search the web for the answer.", you can use this function.""",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The query to search the web for.",
            }
        },
        "required": ["query"]
    }
}

def retrieve_from_web(query):
    search = GoogleSearchAPIWrapper()
    result = search.run(query)
    return result