import { useState, useRef, useEffect } from "react";

export default function RoleSelector({ role, setRole }) {
  const roles = ["tutor", "explainer", "summarizer", "quizzer", "reviewer"];
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const label = role.charAt(0).toUpperCase() + role.slice(1);

  return (
    <div className="mb-8">
      <div className="text-slate-300 text-sm font-medium mb-3 flex items-center gap-2">
        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
        AI Assistant Mode
      </div>
      
      <div ref={ref} className="relative inline-block w-64 text-left z-50">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="
            w-full flex items-center justify-between
            bg-slate-800 border border-slate-600 text-slate-100
            px-4 py-3 text-sm font-medium rounded-lg
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            hover:bg-slate-700 hover:border-slate-500
            transition-all duration-200
            shadow-lg
          "
        >
          <span>{label}</span>
          <svg
            className="ml-2 h-4 w-4 transform transition-transform duration-200"
            style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              d="M6 9l6 6 6-6"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        {open && (
          <ul className="
            absolute left-0 right-0 z-50 mt-2
            bg-slate-800 border border-slate-600 text-slate-100
            shadow-xl rounded-lg
            max-h-48 overflow-y-auto
            text-sm
          ">
            {roles.map((r) => {
              const cap = r.charAt(0).toUpperCase() + r.slice(1);
              const isSelected = r === role;
              return (
                <li
                  key={r}
                  onClick={() => {
                    setRole(r);
                    setOpen(false);
                  }}
                  className={`
                    px-4 py-3 cursor-pointer
                    transition-colors duration-150
                    ${isSelected 
                      ? 'bg-blue-600 text-white' 
                      : 'hover:bg-slate-700 hover:text-white'
                    }
                    first:rounded-t-lg last:rounded-b-lg
                  `}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${isSelected ? 'bg-blue-200' : 'bg-slate-500'}`}></div>
                    {cap}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
