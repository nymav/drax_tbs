import React from 'react';

export default function ChatMessage({ msg }) {
  const alignment = msg.user ? "justify-end" : "justify-start";
  const userStyles = msg.user ? {
    bg: "bg-blue-600",
    text: "text-white",
    border: "border-blue-600"
  } : {
    bg: "bg-slate-700",
    text: "text-slate-100",
    border: "border-slate-600"
  };

  return (
    <div className={`flex ${alignment} mb-4`}>
      <div
        className={`
          max-w-[75%]
          p-4
          ${userStyles.bg}
          ${userStyles.text}
          border
          ${userStyles.border}
          rounded-lg
          shadow-sm
          text-sm
          leading-relaxed
          ${msg.user ? 'rounded-br-sm' : 'rounded-bl-sm'}
        `}
      >
        <p className="whitespace-pre-wrap">{msg.text}</p>
      </div>
    </div>
  );
}

// Demo component to show it working
function ChatDemo() {
  const messages = [
    { user: false, text: "Hello! How can I help you today?" },
    { user: true, text: "I need help with my React component." },
    { user: false, text: "I'd be happy to help! What specific issue are you encountering?" }
  ];

  return (
    <div className="min-h-screen bg-slate-900 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-8 text-center">Chat Message Component Demo</h1>
        <div className="space-y-4 bg-slate-800 p-6 rounded-lg">
          {messages.map((msg, index) => (
            <ChatMessage key={index} msg={msg} />
          ))}
        </div>
      </div>
    </div>
  );
}

// Export the demo for testing
export { ChatDemo };