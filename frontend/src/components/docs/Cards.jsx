import { ArrowRight, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getIcon } from './IconPicker';

export const Columns = ({ children, cols = 2, className = '' }) => {
  const gridCols = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={`grid gap-4 my-6 relative z-10 ${gridCols[cols] || gridCols[2]} ${className}`} data-testid="columns">
      {children}
    </div>
  );
};

export const CardGroup = ({ children, cols = 2, className = '' }) => {
  const gridCols = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={`grid gap-4 my-6 relative z-10 ${gridCols[cols] || gridCols[2]} ${className}`} data-testid="card-group">
      {children}
    </div>
  );
};

export const Card = ({ title, children, href, icon, color, className = '' }) => {
  const navigate = useNavigate();
  const isExternal = href?.startsWith('http');
  const IconComponent = icon ? getIcon(icon) : null;

  const handleClick = () => {
    if (isExternal) window.open(href, '_blank', 'noopener,noreferrer');
    else if (href) navigate(href);
  };

  const content = (
    <>
      {IconComponent && (
        <div className="mb-4">
          <div className="w-10 h-10 rounded-lg bg-slate-800/50 border border-slate-700/50 flex items-center justify-center"
            style={color ? { borderColor: `${color}30` } : {}}>
            <IconComponent className="w-5 h-5" color={color || '#FFFFFF'} />
          </div>
        </div>
      )}
      <h4 className="text-base font-semibold !text-white mb-2 group-hover:text-emerald-400 transition-colors flex items-center gap-2">
        {title}
        {href && (
          <span className="opacity-0 group-hover:opacity-100 transition-opacity">
            {isExternal ? <ExternalLink className="w-3.5 h-3.5" /> : <ArrowRight className="w-3.5 h-3.5" />}
          </span>
        )}
      </h4>
      <div className="text-sm !text-slate-400 leading-relaxed [&_p]:!text-slate-400 [&_p]:!m-0">
        {children}
      </div>
    </>
  );

  if (href) {
    return (
      <button onClick={handleClick}
        className={`card group text-left w-full p-5 bg-slate-900/30 hover:bg-slate-900/60 border border-slate-800/60 hover:border-slate-700 rounded-xl transition-all duration-200 ${className}`}
        data-testid="card">
        {content}
      </button>
    );
  }

  return (
    <div className={`card group p-5 bg-slate-900/30 border border-slate-800/60 rounded-xl ${className}`} data-testid="card">
      {content}
    </div>
  );
};

Card.displayName = 'Card';
