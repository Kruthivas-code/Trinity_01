import React from 'react';

/**
 * TriangleIcon - Trinity's brand icon
 * A clean, minimal triangle representing stability and direction
 */
export const TridentIcon = ({ 
  size = 24, 
  className = '',
  strokeWidth = 2,
  ...props 
}) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      {/* Simple elegant triangle pointing up */}
      <path d="M12 3L21 20H3L12 3Z" />
    </svg>
  );
};

/**
 * TridentLogo - Full brand logo with text
 */
export const TridentLogo = ({ 
  size = 'default',
  showText = true,
  className = '' 
}) => {
  const sizes = {
    sm: { icon: 18, text: 'text-base' },
    default: { icon: 20, text: 'text-lg' },
    lg: { icon: 28, text: 'text-xl' }
  };
  
  const { icon, text } = sizes[size] || sizes.default;
  
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <TridentIcon size={icon} className="text-primary" strokeWidth={2} />
      {showText && (
        <span className={`brand ${text} font-bold tracking-tight`}>
          Trinity
        </span>
      )}
    </div>
  );
};

export default TridentIcon;
