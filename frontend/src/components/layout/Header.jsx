export default function Header() {
  return (
    <div className="mb-12 relative">
      <h1 className="text-5xl font-bold text-white mb-4 flex items-center gap-4">
        <span className="text-6xl">📚</span> 
        <div className="flex flex-col">
          <span className="text-3xl text-slate-400 font-medium tracking-wide">
            PDF Assistant
          </span>
        </div>
      </h1>
      
     
      
      {/* Decorative line */}
      <div className="absolute -bottom-6 left-0 right-0 h-px bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
    </div>
  );
}
