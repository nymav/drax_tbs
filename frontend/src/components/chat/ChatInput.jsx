import { useRef, useEffect } from "react";

export default function ChatInput({ query, setQuery, onSend, disabled = false }) {
  const inputRef = useRef(null);

  // Auto-focus input when component mounts or becomes enabled
  useEffect(() => {
    if (!disabled && inputRef.current) {
      inputRef.current.focus();
    }
  }, [disabled]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (query.trim() && !disabled) {
      onSend();
      // Focus back to input after sending
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 100);
    }
  };

  const handleInputChange = (e) => {
    setQuery(e.target.value);
  };

  return (
    <div className="flex gap-3 items-center">
      {/* Input field with professional styling */}
      <div className="flex-grow relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          disabled={disabled}
          placeholder={disabled ? "Processing..." : "Type your message here..."}
          className={`
            w-full
            bg-slate-800
            border
            px-4
            py-3
            rounded-lg
            focus:outline-none
            text-sm
            transition-all
            duration-200
            ${disabled 
              ? "border-slate-600 placeholder-slate-500 text-slate-400 cursor-not-allowed bg-slate-900" 
              : "border-slate-600 placeholder-slate-400 text-slate-100 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 hover:border-slate-500"
            }
          `}
        />
        
        {/* Status indicator */}
        <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
          <div className={`w-2 h-2 rounded-full ${disabled ? 'bg-slate-500' : 'bg-blue-500'}`}></div>
        </div>
      </div>
             
      {/* Send button with professional styling */}
      <button
        onClick={handleSend}
        disabled={disabled || !query.trim()}
        className={`
          px-6
          py-3
          font-medium
          text-sm
          rounded-lg
          transition-all
          duration-200
          border
          ${disabled || !query.trim()
            ? "bg-slate-700 text-slate-400 border-slate-600 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700 text-white border-blue-600 hover:border-blue-700 shadow-md hover:shadow-lg"
          }
        `}
      >
        {disabled ? "Processing" : "Send"}
      </button>
    </div>
  );
}