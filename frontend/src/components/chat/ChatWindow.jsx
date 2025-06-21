import { useState, forwardRef, useImperativeHandle, useRef } from "react";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import { sendChatQuery } from "../../api/chat";

const ChatWindow = forwardRef(({ role, pdfId }, ref) => {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const containerRef = useRef(null);

  const handleSend = async () => {
    if (!query.trim() || !pdfId) return;
    setMessages((prev) => [...prev, { user: true, text: query }]);
    setQuery("");

    try {
      const res = await sendChatQuery({ query, role, pdf_id: pdfId });
      setMessages((prev) => [...prev, { user: false, text: res.answer }]);
    } catch {
      setMessages((prev) => [...prev, { user: false, text: "⚠️ Error: Unable to process request." }]);
    }
  };

  useImperativeHandle(ref, () => ({
    scrollIntoView: () => {
      containerRef.current?.scrollIntoView({ behavior: "smooth" });
    },
  }));

  return (
    <div
      ref={containerRef}
      className="
        flex
        flex-col
        bg-slate-800
        border
        border-slate-600
        rounded-lg
        shadow-lg
        max-h-[60vh]
        overflow-hidden
      "
    >
      {/* Header */}
      <div className="bg-slate-700 border-b border-slate-600 p-4">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="text-slate-200 text-sm font-medium">AI Assistant</span>
        </div>
      </div>

      {/* Messages container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-850">
        {messages.length === 0 && (
          <div className="text-center text-slate-400 text-sm py-8">
            <div className="mb-2">👋 Welcome!</div>
            <div>Start a conversation by typing a message below.</div>
          </div>
        )}
        
        {messages.map((msg, i) => (
          <ChatMessage key={i} msg={msg} />
        ))}
      </div>
      
      {/* Input area */}
      <div className="p-4 border-t border-slate-600 bg-slate-750">
        <ChatInput query={query} setQuery={setQuery} onSend={handleSend} />
      </div>
    </div>
  );
});

export default ChatWindow;