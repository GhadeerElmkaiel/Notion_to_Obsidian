import requests
from pathlib import Path
from datetime import datetime

token = ''

databaseId = ''

headers = {
    "Authorization": "Bearer " +token,
    "Notion-Version": "2022-06-28"
}

# a function to read a database
def readDatabase(page_id, headers):
    readUrl = f"https://api.notion.com/v1/databases/{page_id}"
    res = requests.request("GET", readUrl, headers=headers)
    return res

# A function to return pages ids in the database
def readDatabaseQuery(page_id, headers):
    readUrl = f"https://api.notion.com/v1/databases/{page_id}/query/"

    res = requests.request("POST", readUrl, headers=headers)
    query_data = res.json()
    return query_data

# a function to read a page info    
def readPage(page_id, headers, update_page=True):
    readUrl = f"https://api.notion.com/v1/pages/{page_id}"
    res = requests.request("GET", readUrl, headers=headers)
    page_data = res.json()
    if update_page:
        # data = {"properties": {"Moved To Obsidian":{"checkbox": True}}}
        data = '{"properties": {"Moved To Obsidian":{"checkbox": true}}}'
        res = updatePage(page_id, headers, data)
    return page_data
    
# a function to read a page property detales
def readPageProperty(page_id, property_id, headers):
    readUrl = f"https://api.notion.com/v1/pages/{page_id}/properties/{property_id}"

    res = requests.request("GET", readUrl, headers=headers)
    data = res.json()

    return data

# a function to delete a page (or a block)
def deleteBlock(block_id, headers):
    readUrl = f"https://api.notion.com/v1/blocks/{block_id}"
    res = requests.request("DELETE", readUrl, headers=headers)
    return res

# a function to read a list of a blocks children (in this case the blocks of content of a page)
def readBlockChildren(block_id, headers):
    readUrl = f"https://api.notion.com/v1/blocks/{block_id}/children"
    res = requests.request("GET", readUrl, headers=headers)
    blocks_children = res.json()
    return blocks_children

# a function to read a block (used to read a block of a page content)
def readBlockInfo(block_id, headers):
    readUrl = f"https://api.notion.com/v1/blocks/{block_id}"
    res = requests.request("GET", readUrl, headers=headers)
    block_info = res.json()
    return block_info

# a function to update a page
def updatePage(page_id, headers, data):
    readUrl = f"https://api.notion.com/v1/pages/{page_id}"

    res = requests.request("PATCH", readUrl, headers=headers, data=data)
    return res


# a function to create an MD file for Obsidian valut
#----------------------------------------------
# This is the function that creates the .md file
# You can edit this function to change the configuration of the resulted .md file
# Configure this function only to change the structure of the resutled note to match your style
#----------------------------------------------
def createMdFile(data, path):
    title = data["title"]
    date = datetime.today().strftime('%Y-%m-%d')
    with open(f"{path}/{title}.md","w") as f:
        # The file header
        f.writelines("---\n")
        f.write("Status: check\n")     # this Status makes it easier to find the notes that you still need to check after moving to Obsidian, The idea is to change this field after reviewing the 
        f.write(f"Date: {date}\n")
        f.write(f"Created_Date: {date}\n")
        f.write("---\n")
        
        # The File Name
        title = data["title"]
        f.writelines(f"# {title}\n___\n")

        source = data["source"]
        f.write(f"Source:: {source}")
        f.write("\n")
        f.write("Tags:: #copied-from-notion")
        for tag in data["tags"]:
            f.write(f", #{tag}")
        f.writelines("\n___\n")
        # The content
        content = data["content"]
        f.write(f"## Details\n{content}\n")
        paragraphs = data["paragraphs"]
        for paragraph in paragraphs:
            f.write(f"{paragraph}\n")

        f.write("\n___\n")
        # The related notes
        linked_pages = data["linked_page"]
        f.write(f"## Related Notes\n")
        for link in linked_pages:
            f.writelines(f"[[{link}]]\n")

        in_links = """
___
## In-links
```dataview
LIST
WHERE
	contains(this.file.inlinks, file.link)
	AND 
	!contains(this.file.outlinks, file.link)
```
"""
        f.write(in_links)


path = Path(__file__).parent.absolute()


query_data = readDatabaseQuery(databaseId, headers)

# a list of properties that I am interested in
property_id = {"Name":"", "Tags":"", "Comment":"", "Linked Pages":"", "Source":""}

# Getting the id's for the properties
for page_object in query_data["results"]:
    pageId = page_object["id"]
    page_data = readPage(pageId, headers)
    for prop in property_id:
        property_id[prop] = page_data["properties"][prop]["id"]
    break

for page_object in query_data["results"]:
    page_id = page_object["id"]
    # check_box_res = readPageProperty(page_id, property_id["Moved To Obsidian"], headers)
    # if check_box_res["checkbox"]==True:
    #     continue
    
    # Get the title of the page (The title of the note)
    data_in_file = {}
    prop_res = readPageProperty(page_id, property_id["Name"], headers)
    title = prop_res["results"][0]["title"]["plain_text"]
    data_in_file["title"]=title
    tags = []
    prop_res = readPageProperty(page_id, property_id["Tags"], headers)
    for tag_object in prop_res["multi_select"]:
        tags.append(tag_object["name"])
    data_in_file["tags"]=tags
    
    # The names of the linked pages
    linked_pages = []
    prop_res = readPageProperty(page_id, property_id["Linked Pages"], headers)
    for link_object in prop_res["multi_select"]:
        linked_pages.append(link_object["name"])
    data_in_file["linked_page"]=linked_pages

    # Here is the text inside the comment field (for fast notes)
    prop_res = readPageProperty(page_id, property_id["Comment"], headers)
    if len(prop_res["results"])>0:
        content = prop_res["results"][0]["rich_text"]["plain_text"]
    else:
        content = ""
    data_in_file["content"]=content

    # Here is the Source of the note (Would be Notion if nothing else was mentioned)
    prop_res = readPageProperty(page_id, property_id["Source"], headers)
    if len(prop_res["results"])>0:
        content = prop_res["results"][0]["rich_text"]["plain_text"]
    else:
        content = "Notion"
    data_in_file["source"]=content

    # Get the content inside the page itself (Each part separated by a title will be treated as a block)
    data_in_file["pageId"]=page_id
    paragraphs = []
    blocks_children = readBlockChildren(page_id, headers)
    for block_id in blocks_children["results"]:
        block_info = readBlockInfo(block_id['id'],headers)
        if block_info["type"]=="paragraph":
            # For the case of empty lines
            if len(block_info["paragraph"]["rich_text"])>0:
                paragraphs.append(block_info["paragraph"]["rich_text"][0]["plain_text"])
    data_in_file["paragraphs"]=paragraphs

    createMdFile(data_in_file, path)
    
    res_del = deleteBlock(page_id, headers)