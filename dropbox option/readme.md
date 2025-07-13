<img width="1024" height="1536" alt="image" src="https://github.com/user-attachments/assets/4378ae14-184d-49dd-8913-9851deb1479f" /># overview
[1] End-User (App UI)
     |
     v
[2] Submit Permission Request Form
     |
     v
[3] App Backend Receives Request
     |
     +--> [4] Generate Multiple Editable PDFs
     |
     +--> [5] Create Dropbox Folders (one per document or user)
     |
     +--> [6] Upload PDFs to Dropbox
     |
     +--> [7] Register Dropbox Webhook Endpoint for Folder(s)
     |
     v
[8] Notify End-User (e.g., app or email with Dropbox links)
     |
     v
[9] End-User Opens Dropbox Link to Edit/Sign PDF
     |
     v
[10] End-User Signs and Saves PDF (in Dropbox)
     |
     v
[11] Dropbox Triggers Webhook on File Change
     |
     v
[12] App Backend Receives Webhook Notification
     |
     +--> [13] Report shows missing signatures

     <img width="1024" height="1536" alt="image" src="https://github.com/user-attachments/assets/91fa7c46-1803-4198-bfd9-612dc2d3fc70" />

