export default function Container({ children }) {
  return (
    <div className="
      max-w-5xl 
      mx-auto 
      p-8 
      bg-slate-900/95 
      border 
      border-slate-700 
      shadow-2xl 
      backdrop-blur-sm
      rounded-lg
      relative
      overflow-hidden
    ">
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-800/20 to-slate-900/20 pointer-events-none" />
      
      {/* Corner accents */}
      <div className="absolute top-0 left-0 w-16 h-16 border-t-2 border-l-2 border-blue-500/30 rounded-tl-lg" />
      <div className="absolute bottom-0 right-0 w-16 h-16 border-b-2 border-r-2 border-blue-500/30 rounded-br-lg" />
      
      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}
