# DRAX TBS - AI-Powered Tutoring System

A comprehensive Retrieval-Augmented Generation (RAG) based tutoring system that allows students to upload textbooks and engage in intelligent conversations with an AI tutor. The system processes PDF documents, creates vector embeddings, and provides contextual responses based on the uploaded content.

## Features

- **PDF Document Processing**: Upload and process textbook PDFs for intelligent tutoring
- **Vector Search**: Advanced semantic search using ChromaDB for relevant content retrieval
- **AI Chat Interface**: Interactive chatbot powered by LM Studio integration
- **Session Management**: Persistent chat sessions with history tracking
- **Role-Based Learning**: Customizable AI tutor personality and teaching style
- **Real-time Responses**: Fast, contextual responses based on uploaded textbooks
- **Modern Web Interface**: Clean, responsive React frontend with Tailwind CSS

## Architecture

### Backend (Python/FastAPI)
- **FastAPI**: Modern, fast web framework for building APIs
- **ChromaDB**: Vector database for semantic search and embeddings
- **Sentence Transformers**: For generating text embeddings
- **PyMuPDF**: PDF processing and text extraction
- **SQLite**: Chat history and session persistence

### Frontend (React/Vite)
- **React**: Modern UI library for building interactive interfaces
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework for styling
- **Axios**: HTTP client for API communication

## Prerequisites

- Python 3.9+
- Node.js 16+
- LM Studio (for local AI model hosting)

## Installation

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/nymav/drax_tbs.git
   cd drax_tbs
   ```

2. **Create and activate virtual environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the backend directory:
   ```env
   LMSTUDIO_BASE_URL=http://localhost:1234/v1
   LMSTUDIO_API_KEY=your-api-key
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   VECTOR_STORE_PATH=./data/vector_store
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd ../frontend
   ```

2. **Install Node.js dependencies**
   ```bash
   npm install
   ```

3. **Build the frontend**
   ```bash
   npm run build
   ```

### LM Studio Setup

1. **Download and install LM Studio**
   - Visit [LM Studio website](https://lmstudio.ai/) and download the application

2. **Load a model**
   - Open LM Studio
   - Browse and download a suitable model (e.g., Llama 2, Mistral)
   - Start the local server on port 1234

## Running the Application

### Start the Backend Server
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start the Frontend (Development)
```bash
cd frontend
npm run dev
```

The application will be available at:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Usage

### 1. Upload Textbooks
- Navigate to the upload section
- Select and upload PDF textbooks
- Wait for processing and embedding generation

### 2. Start Tutoring Session
- Select a processed textbook from the dropdown
- Choose your preferred tutor role/personality
- Begin asking questions about the content

### 3. Chat Interface
- Ask questions related to your uploaded textbooks
- Receive contextual answers based on the document content
- View chat history and maintain conversation context

## API Endpoints

### Core Endpoints
- `POST /api/upload` - Upload PDF textbooks
- `GET /api/textbooks` - List available textbooks
- `POST /api/chat` - Send chat messages
- `GET /api/sessions` - Manage chat sessions
- `POST /api/embed` - Generate embeddings for documents

### Health Check
- `GET /health` - Application health status

## Project Structure

```
drax_tbs/
├── backend/
│   ├── app/
│   │   ├── routes/          # API route handlers
│   │   ├── services/        # Business logic
│   │   ├── models/          # Data models
│   │   ├── utils/           # Utility functions
│   │   └── main.py          # FastAPI application
│   ├── data/
│   │   ├── pdfs/           # Uploaded PDF files
│   │   ├── vector_store/   # ChromaDB vector storage
│   │   └── textbooks.json  # Textbook metadata
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── api/           # API client functions
│   │   ├── hooks/         # Custom React hooks
│   │   └── styles/        # CSS styles
│   ├── dist/              # Built frontend files
│   └── package.json
└── README.md
```

## Configuration

### Environment Variables

**Backend (.env)**
```env
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_API_KEY=your-api-key
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_STORE_PATH=./data/vector_store
DATABASE_URL=sqlite:///./app/db/chat_history.db
MAX_FILE_SIZE=50MB
```

### LM Studio Configuration
- Ensure the local server is running on port 1234
- Configure the model parameters (temperature, max tokens, etc.)
- Set appropriate context window size for your use case

## Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Troubleshooting

### Common Issues

1. **LM Studio Connection Error**
   - Ensure LM Studio is running and accessible at `http://localhost:1234`
   - Check if the model is loaded and the server is started

2. **PDF Processing Issues**
   - Verify PDF files are not corrupted or password-protected
   - Check file size limits (default: 50MB)

3. **Vector Store Errors**
   - Clear the vector store directory if corrupted: `rm -rf backend/data/vector_store/*`
   - Restart the application to reinitialize

4. **Port Conflicts**
   - Backend: Change port in uvicorn command
   - Frontend: Modify `vite.config.js` port settings

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and commit: `git commit -m 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation at `/docs` endpoint
- Review the API documentation at `/api/docs`

## Future Enhancements

- [ ] Multi-modal support (images, videos)
- [ ] Advanced analytics and learning progress tracking
- [ ] Mobile app development
- [ ] Integration with external LLM services
- [ ] Collaborative learning features
- [ ] Advanced document parsing (tables, equations)
