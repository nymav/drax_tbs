import { useRef, useState } from "react";
import Container from "./components/layout/Container";
import Header from "./components/layout/Header";
import TextbookSelector from "./components/selector/TextbookSelector";
import RoleSelector from "./components/selector/RoleSelector";
import ChatWindow from "./components/chat/ChatWindow";

function App() {
  const [pdfId, setPdfId] = useState(null);
  const [pdfName, setPdfName] = useState("");
  const [role, setRole] = useState("tutor");
  const chatRef = useRef(null);

  const handleBookSelect = ({ id, name }) => {
    setPdfId(id);
    setPdfName(name);
    setTimeout(() => chatRef.current?.scrollIntoView({ behavior: "smooth" }), 300);
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 to-slate-900 text-slate-100 p-4">
      <Container>
        <Header />

        <TextbookSelector onSelect={handleBookSelect} />

        {pdfName && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 mt-6 mb-6">
            <div className="flex items-center gap-3 text-slate-300">
              <span className="text-xl">📚</span>
              <span className="text-sm font-medium">Active Document:</span>
              <span className="text-white bg-blue-600/20 px-3 py-1 rounded-md border border-blue-600/30 text-sm font-medium">
                {pdfName}
              </span>
            </div>
          </div>
        )}

        <RoleSelector role={role} setRole={setRole} />

        {pdfId && (
          <div ref={chatRef} className="mt-8">
            <ChatWindow role={role} pdfId={pdfId} pdfName={pdfName} />
          </div>
        )}
      </Container>
    </main>
  );
}

export default App;