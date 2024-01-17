## Getting Started with Chat Utilities

### Uploading Documents
To upload documents for embedding:
- Click on the **Upload** button.
- Select the document(s) you wish to upload. Accepted file types are `.txt`, `.pdf`, and `.docx`.
- Once selected, the file name(s) will be displayed, and you can proceed to fill out optional metadata for each document, such as the title and author's name.
    - The metadata is used within Knowledge Retrieval Queries in the Chat utility. Providing accurate info helps the AI better cite/source provided information.
    - Similarly for metadata, the embeddings utility also detect page numbers on the original document for each embedded chunk. This is intrinsically most accurate with PDFs and Docx files, yet it still estimates txt files based on word count.
- If you have multiple documents, use the pagination controls to navigate between them and provide details for each one.
- Click the **Submit Docs** button to upload the documents to the server.
- You may need to refresh the page to see the uploaded files in the history.

### Managing Uploaded Documents
After uploading, each document will be listed with options to edit or delete:
- To **edit** a document's metadata, click the pencil icon, make your changes to the author or title columns, and then click the disk icon to save.
- To **delete** a document, click the trash can icon and confirm your intention in the popup dialog.


### Additional Features and Settings
- **Model Context Size & Embedded Chunk Size** This section displays the context token limits for different models. This is not necessarily the "max tokens" parameter as this equates to the amount of tokens they can properly "remember" back into a conversation. 
  - They are listed as a relevant frame of reference when deciding on the appropriate chunk size given your docs and usage purpose.
