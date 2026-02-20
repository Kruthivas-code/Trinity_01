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
          <IconComponent className="w-7 h-7 text-[#00A1B2]" />
        </div>
      )}
      <h4 className="text-base font-semibold !text-gray-900 dark:!text-white mb-2 group-hover:text-[#00A1B2] dark:group-hover:text-[#00A1B2] transition-colors flex items-center gap-2">
        {title}
        {href && (
          <span className="opacity-0 group-hover:opacity-100 transition-opacity">
            {isExternal ? <ExternalLink className="w-3.5 h-3.5" /> : <ArrowRight className="w-3.5 h-3.5" />}
          </span>
        )}
      </h4>
      <div className="text-sm !text-gray-500 dark:!text-[#999999] leading-relaxed [&_p]:!text-gray-500 dark:[&_p]:!text-[#999999] [&_p]:!m-0">
        {children}
      </div>
    </>
  );

  const cardClass = `card group text-left w-full p-5 bg-white dark:bg-[#0a0a0a] border border-gray-200 dark:border-white/10 hover:border-[#00A1B2] dark:hover:border-[#00A1B2] rounded-2xl transition-all duration-200 ${className}`;

  if (href) {
    return (
      <button onClick={handleClick} className={cardClass} data-testid="card">
        {content}
      </button>
    );
  }

  return (
    <div className={cardClass} data-testid="card">
      {content}
    </div>
  );
};

Card.displayName = 'Card';
