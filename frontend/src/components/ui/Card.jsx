export function Card({ children, className = '', hover = false, ...props }) {
  return (
    <div
      className={`bg-slate-900/80 backdrop-blur-md border border-slate-800/90 rounded-2xl shadow-xl shadow-slate-950/50 p-6 ${
        hover ? 'transition-all duration-200 hover:border-slate-700/80 hover:shadow-2xl hover:shadow-indigo-950/20' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '' }) {
  return <div className={`flex flex-col gap-1.5 pb-4 mb-4 border-b border-slate-800/60 ${className}`}>{children}</div>;
}

export function CardTitle({ children, className = '' }) {
  return <h3 className={`text-lg font-bold text-white tracking-tight ${className}`}>{children}</h3>;
}

export function CardDescription({ children, className = '' }) {
  return <p className={`text-sm text-slate-400 leading-relaxed ${className}`}>{children}</p>;
}

export function CardContent({ children, className = '' }) {
  return <div className={`space-y-4 ${className}`}>{children}</div>;
}

export function CardFooter({ children, className = '' }) {
  return (
    <div className={`mt-6 pt-4 border-t border-slate-800/60 flex items-center justify-between gap-3 ${className}`}>
      {children}
    </div>
  );
}

export default Card;
