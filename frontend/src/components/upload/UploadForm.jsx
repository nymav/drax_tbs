import { useState } from "react";
import { uploadPdf } from "../../api/upload";
import { embedPdf } from "../../api/embed";

export default function UploadForm({ onUpload }) {
  const [file, setFile] = useState(null);
  const [isUploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return alert("Please choose a PDF file first.");
    setUploading(true);
    try {
      const res = await uploadPdf(file);
      const id = res.pdf_id || res.filename;
      const name = res.title || file.name;
      await embedPdf(id);
      onUpload({ id, name });
      setFile(null);
    } catch (err) {
      console.error(err);
      alert("Upload or embed failed. See console.");
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === "application/pdf") {
        setFile(droppedFile);
      } else {
        alert("Please drop a PDF file only.");
      }
    }
  };

  return (
    <form onSubmit={handleUpload} className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
        <div className="text-slate-300 text-sm font-medium">
          Upload Document
        </div>
        <div className="flex-1 h-px bg-slate-700"></div>
      </div>
      
      {/* Drag and drop area */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-8 transition-all duration-300
          ${dragActive 
            ? "border-blue-500 bg-blue-500/10" 
            : "border-slate-600 bg-slate-800/30 hover:border-slate-500 hover:bg-slate-800/50"
          }
          ${isUploading ? "opacity-50 pointer-events-none" : ""}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".pdf"
          disabled={isUploading}
          onChange={(e) => setFile(e.target.files[0])}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        
        <div className="text-center space-y-4">
          <div className="text-4xl text-slate-500">
            {isUploading ? "⏳" : "📄"}
          </div>
          
          <div className="space-y-2">
            <p className="text-slate-300 text-sm font-medium">
              {isUploading ? "Processing..." : "Drop PDF file here"}
            </p>
            <p className="text-slate-500 text-xs">
              or click to select file
            </p>
          </div>
          
          {file && (
            <div className="mt-4 p-3 bg-slate-700/50 border border-slate-600 rounded-lg">
              <p className="text-slate-300 text-sm">
                Selected: <span className="text-white font-medium">{file.name}</span>
              </p>
              <p className="text-slate-500 text-xs mt-1">
                Size: {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          )}
        </div>
      </div>
      
      {/* File format info */}
      <div className="text-xs text-slate-500 flex items-center gap-2">
        <div className="w-1 h-1 bg-slate-600 rounded-full"></div>
        Supported format: PDF • Maximum size: 50MB
      </div>

      {/* Upload button */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={!file || isUploading}
          className={`
            px-6 py-2.5 text-sm font-medium rounded-lg
            transition-all duration-200
            ${!file || isUploading
              ? "bg-slate-700 text-slate-500 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900"
            }
          `}
        >
          {isUploading ? (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              Uploading...
            </div>
          ) : (
            "Upload File"
          )}
        </button>
      </div>

      {/* Status */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${isUploading ? 'bg-blue-500' : 'bg-emerald-500'}`}></div>
          <span>
            Status: {isUploading ? 'Processing' : 'Ready'}
          </span>
        </div>
        <div>
          AI Processing v2.1
        </div>
      </div>
    </form>
  );
}