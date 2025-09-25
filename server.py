from fastmcp import FastMCP
import pymongo
import json

mcp = FastMCP("poc-tools")

@mcp.tool()
def find_document_in_mongo(query: str) -> str:
    try:
        client = pymongo.MongoClient("<mongodb+srv://...")
        db = client['test_db']
        collection = db["movies"]
        query_dict = json.loads(query) if isinstance(query,str) else query
        results = list(collection.find(query_dict).limit(10))
        if not results:
            return "no document found matching the query"
        for doc in results:
            doc["_id"] = str(doc["_id"])
        return json.dumps(results)
    except Exception as e:
        error_msg = f"Error Querying DB : {str(e)}"
        print(error_msg)
        return error_msg

if __name__ == "__main__":
    mcp.run()