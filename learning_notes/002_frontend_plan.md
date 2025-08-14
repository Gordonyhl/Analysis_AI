
# Plan: Transitioning from CLI to a Web-Based Chat Interface

This document outlines the steps to evolve the existing CLI chat application into a full-stack application with a FastAPI backend and a simple HTML/JavaScript front-end.

### Guiding Principle
The goal is to achieve a functional web interface with minimal complexity, reusing as much of the existing backend logic as possible. We will prioritize a clean separation of concerns between the front-end and the back-end.

---

### Phase 1: Create the Backend API for Chat

The first step is to expose the chat functionality through a dedicated API endpoint. This decouples the core AI logic from the command-line interface.

-   **Action:** Create a new file named `api.py`.
    -   **Purpose:** This file will house all chat-related API endpoints, keeping them separate from the file-upload logic in `app.py`.
-   **Action:** Design a new chat endpoint.
    -   **Endpoint:** `POST /api/chat/stream`
    -   **Request Body:** The endpoint will accept a JSON object with the user's `message` and an optional `thread_title`.
    -   **Response:** It will use **Server-Sent Events (SSE)** (`StreamingResponse`) to stream the AI's response back to the client in real-time. This is highly efficient for chat applications.
-   **Action:** Refactor the core logic.
    -   The chat logic currently in `llm.py`'s `main` loop will be moved into an async generator function (`stream_chat_response`) that can be called by the new endpoint. This function will handle loading history, running the agent, and persisting the conversation.

### Phase 2: Integrate APIs and Serve the Front-End

Next, we'll update the main application to incorporate the new API, simplify the existing upload endpoint, and prepare it to serve a web page.

-   **Action:** Modify `app.py`.
    -   **Integrate Chat Router:** Import the router from `api.py` and include it in the main FastAPI application.
    -   **Simplify Upload Endpoint:** Modify the existing `/upload` endpoint. Remove the complex CSV/pandas validation. The new goal is to simply accept a file and save it to a designated `uploads/` directory. It should return a simple success message.
    -   **Serve Static Files:** Configure FastAPI to serve static files from a new `/static` directory.
    -   **Create Root Endpoint:** Add a root endpoint (`GET /`) that serves the main `index.html` file.

### Phase 3: Build the Front-End Interface

With the backend ready, the next step is to create the user interface.

-   **Action:** Create a `static/` directory.
-   **Action:** Create a new file: `static/index.html`.
    -   **Structure (HTML):**
        -   A main container for the chat history.
        -   An input field for the user to type their message and a "Send" button.
        -   An optional input field for specifying a conversation `thread_title`.
    -   **Styling (CSS):**
        -   Use simple, modern CSS to create a clean and readable chat interface.
    -   **Logic (JavaScript):**
        -   Add an event listener to handle sending chat messages via `fetch` to the `/api/chat/stream` endpoint.
        -   Process the streaming SSE response to display the AI's message in real-time.

### Phase 4: Integrate File Uploading into the Chat

Finally, we'll connect the simplified upload functionality to the chat interface.

-   **Action:** Modify `static/index.html`.
    -   **Add Upload UI:** Add an `<input type="file">` element and an "Upload" button to the HTML structure.
    -   **Add Upload Logic (JavaScript):**
        -   Create a new JavaScript function to handle the file upload.
        -   When the user clicks "Upload", use `FormData` and `fetch` to send the selected file to the simplified `/upload` endpoint.
        -   Upon receiving a successful response from the server, display a confirmation message directly in the chat window (e.g., "System: You have uploaded `document.pdf`. You can now ask questions about it.").

### Milestone
Once these four phases are complete, you will be able to:
1.  Run `uvicorn app:app --reload`.
2.  Open a web browser to `http://127.0.0.1:8000`.
3.  Interact with the AI through a web interface.
4.  Upload a document through the same interface and receive a confirmation that it's ready for discussion.

