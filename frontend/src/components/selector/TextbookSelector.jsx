import { useState } from "react";
import useTextbooks from "../../hooks/useTextbooks";
import UploadForm from "../upload/UploadForm";

export default function TextbookSelector({ onSelect }) {
  const { books, loading, error } = useTextbooks();
  const [mode, setMode] = useState("select");
  const [selectedId, setSelectedId] = useState("");

  if (loading) return (
    <div className="text-slate-400 text-sm flex items-center gap-2">
      <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      Loading textbooks...
    </div>
  );
  
  if (error) return (
    <div className="text-red-400 text-sm bg-red-900/20 border border-red-500/50 p-3 rounded-lg">
      Error: {error.message}
    </div>
  );

  const handleSelectChange = (e) => {
    const selectedId = e.target.value;
    setSelectedId(selectedId);
    
    const book = books.find((b) => b.id === selectedId);
    if (book) {
      const name = book.title || book.name || book.original_name || book.filename;
      onSelect({ 
        id: book.id,
        name: name,
        title: book.title,
        author: book.author,
        pages: book.pages,
        filename: book.filename
      });
    }
  };

  return (
    <div className="space-y-6 mb-8">
      {/* Section header */}
      <div className="text-slate-300 text-sm font-medium flex items-center gap-2">
        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
        Select Textbook
      </div>

      {/* Mode selector */}
      <div className="flex gap-1 bg-slate-800 p-1 rounded-lg">
        <button
          onClick={() => setMode("select")}
          className={`
            flex-1 px-4 py-2 text-sm font-medium rounded-md
            transition-all duration-200
            ${mode === "select"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-300 hover:bg-slate-700"
            }
          `}
        >
          Select Existing
        </button>
        
        <button
          onClick={() => setMode("upload")}
          className={`
            flex-1 px-4 py-2 text-sm font-medium rounded-md
            transition-all duration-200
            ${mode === "upload"
              ? "bg-blue-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-300 hover:bg-slate-700"
            }
          `}
        >
          Upload New
        </button>
      </div>

      {/* Content area */}
      {mode === "select" ? (
        <div className="relative">
          <select
            value={selectedId}
            onChange={handleSelectChange}
            className="
              w-full bg-slate-800 border border-slate-600 text-slate-100
              px-4 py-3 text-sm rounded-lg
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              hover:border-slate-500
              transition-colors duration-200
            "
          >
            <option value="" disabled>
              Choose a textbook...
            </option>
            {books.map((book) => (
              <option key={book.id} value={book.id} className="bg-slate-800 text-slate-100">
                {book.title || book.name || book.original_name} 
                {book.pages && ` (${book.pages} pages)`}
                {book.author && ` - ${book.author}`}
              </option>
            ))}
          </select>
        </div>
      ) : (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <UploadForm onUpload={onSelect} />
        </div>
      )}
    </div>
  );
}
